"""
Batch **classifier** for pre-recorded test logs (not the live Docker runner).

Expects each subdirectory to contain ``test_output_prev_apply.txt`` and
``test_output_after_apply.txt`` with a line ``echo OMNIGRIL_EXIT_CODE=<n>`` inside.
For live fail2pass (build → test → ``git apply`` → test), use ``testrun.verify.run_f2p_verify``.
"""
import os
import re
import json
import argparse
import multiprocessing
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

PREV_FILE_NAME  = "test_output_prev_apply.txt"
AFTER_FILE_NAME = "test_output_after_apply.txt"
EXIT_CODE_RE    = re.compile(r"echo OMNIGRIL_EXIT_CODE=(\d+)")


def extract_exit_code(content: str) -> int | None:
    """Extracts the exit code from the content; returns None if not found."""
    m = EXIT_CODE_RE.search(content)
    return int(m.group(1)) if m else None


def process_subdirectory(subdir):
    prev_path  = os.path.join(subdir, PREV_FILE_NAME)
    after_path = os.path.join(subdir, AFTER_FILE_NAME)

    # missing outputs or unparsable -> error
    if not (os.path.isfile(prev_path) and os.path.isfile(after_path)):
        return "error"

    prev_content  = open(prev_path,  encoding="utf-8", errors="ignore").read()
    after_content = open(after_path, encoding="utf-8", errors="ignore").read()
    prev_exit  = extract_exit_code(prev_content)
    after_exit = extract_exit_code(after_content)

    if prev_exit is None or after_exit is None:
        return "error"

    prev_fail = (prev_exit != 0)
    after_pass = (after_exit == 0)

    if prev_fail and after_pass:
        return "fail2pass"
    elif prev_fail and not after_pass:
        return "fail2fail"
    elif not prev_fail and after_pass:
        return "pass2pass"
    elif not prev_fail and not after_pass:
        return "pass2fail"
    else:
        return "error"


def classify_and_write_json(src_folder: str, output_json: str, processes: int):
    # Collect subdirectories
    subs = [os.path.join(src_folder, d)
            for d in os.listdir(src_folder)
            if os.path.isdir(os.path.join(src_folder, d))]

    # Parallel processing
    with multiprocessing.Pool(processes) as pool:
        statuses = list(tqdm(
            pool.imap(process_subdirectory, subs),
            total=len(subs), desc="Classifying"
        ))

    # Build category mapping
    cats = {"fail2pass": [], "fail2fail": [], "pass2pass": [], "pass2fail": [], "error": []}
    for subdir, status in zip(subs, statuses):
        inst_id = os.path.basename(subdir)
        cats.setdefault(status, []).append(inst_id)

    # Print summary
    print("Classification summary:")
    for cat, ids in cats.items():
        print(f"  {cat}: {len(ids)}")

    # Write structured JSON
    summary = {"total": len(subs), "categories": cats}
    with open(output_json, 'w', encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary JSON written to '{output_json}'")


def main():
    parser = argparse.ArgumentParser(
        description="Classify subdirectories by test exit codes and output summary JSON.")
    parser.add_argument("target_folder", help="Folder containing subdirs to classify.")
    parser.add_argument("output_json", help="Path for summary JSON output.")
    parser.add_argument("--processes", type=int, default=20, help="Number of worker processes.")
    args = parser.parse_args()

    if not os.path.isdir(args.target_folder):
        parser.error(f"Folder not found: {args.target_folder}")
    if args.processes < 1:
        parser.error("--processes must be >= 1")

    classify_and_write_json(args.target_folder, args.output_json, args.processes)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()