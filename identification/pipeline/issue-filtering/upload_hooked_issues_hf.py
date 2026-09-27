import os
import shutil
import json
from huggingface_hub import upload_file
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "alfin06/swegent-hooked-issues"
REPO_TYPE = "dataset"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "data", "hooked_issue2"))
dst_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "data", "hooked_issue_success"))
fail_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "data", "hooked_issue_fail"))

if not os.path.isdir(src_dir):
    print(f"[X] Directory not found: {src_dir}")
    exit(1)

if not os.path.exists(dst_dir):
    os.makedirs(dst_dir)
if not os.path.exists(fail_dir):
    os.makedirs(fail_dir)

folders = [f for f in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, f))]
batch_size = 128

batch = folders[:batch_size]
for folder in batch:
    folder_path = os.path.join(src_dir, folder)
    issue_file = os.path.join(folder_path, "issue.json")
    if os.path.isfile(issue_file):
        # Check if issues exist and are not empty
        with open(issue_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data.get("issues"):
            print(f"[SKIP] No issues in {folder}/issue.json, skipping upload.")
            shutil.move(folder_path, os.path.join(fail_dir, folder))
            continue
        # Check linked_prs count for each issue
        # skip_due_to_linked_prs = False
        # for issue in data.get("issues", []):
        #     linked_prs = issue.get("linked_prs", [])
        #     if isinstance(linked_prs, list) and len(linked_prs) > 1:
        #         skip_due_to_linked_prs = True
        #         break
        # if skip_due_to_linked_prs:
        #     print(f"[SKIP] {folder}/issue.json has linked_prs with more than 1 record, moving to fail folder.")
        #     shutil.move(folder_path, os.path.join(fail_dir, folder))
        #     continue
        # print(f"Uploading {issue_file} to Hugging Face...")
        try:
            upload_file(
                path_or_fileobj=issue_file,
                path_in_repo=f"{folder}/issue.json",
                repo_id=REPO_ID,
                repo_type=REPO_TYPE,
                token=HF_TOKEN
            )
            print(f"[OK] Uploaded {folder}/issue.json")
            
            # Move folder after successful upload
            shutil.move(folder_path, os.path.join(dst_dir, folder))
            print(f"Moved {folder} to hooked_issue4.")
        except Exception as e:
            print(f"[X] Failed to upload {folder}/issue.json: {e}")
print(f"Batch complete. Run this script again in one hour for the next batch if needed.")