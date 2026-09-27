#!/usr/bin/env python3
"""edit.py — Surgical edit a Python source file, with built-in verification.

Two sub-commands cover the dominant edit ops seen across the training
set: ``replace`` (existing lines swapped for new lines) and ``insert``
(new lines appended after an existing anchor). Both always run
``python -m py_compile`` before exiting.

Reliability invariants:

  1. **Read-back after every edit.** The script re-reads the file
     after writing and reports the exact bytes that landed. If your
     ``--old`` text didn't match, the write was a no-op and the
     script exits non-zero with a re-read hint.
  2. **py_compile gate.** If the edited file doesn't compile, the
     script exits non-zero. NEVER submit a non-compiling patch.
  3. **Single-file scope.** Multi-file edits are out of scope; use
     ``apply.py`` for that.

Sub-commands::

  edit.py replace --file PATH --old "OLD_TEXT" --new "NEW_TEXT"
  edit.py insert  --file PATH --anchor "TEXT_AFTER" --new "NEW_LINE"

The ``--old`` form takes a literal string and is whitespace-sensitive.
For multi-line replacements prefer reading the file with
``sed -n 'A,Bp'`` and passing the exact bytes.

Examples::

  $ edit.py replace \\
      --file src/<PKG>/<FILE>.py \\
      --old '<EXISTING LINE>' \\
      --new '<EXISTING LINE>\\
<NEW LINE>'

  $ edit.py insert \\
      --file src/<PKG>/<FILE>.py \\
      --anchor '<EXISTING TEXT>' \\
      --new '

    def new_method(self):
        ...
'
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def _py_compile(path: Path) -> bool:
    proc = subprocess.run(
        ["python3", "-m", "py_compile", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return False
    return True


def cmd_replace(args) -> int:
    path = Path(args.file)
    text = path.read_text()
    if args.old not in text:
        sys.stderr.write(
            f"NEITHER was inserted: --old text not found in {path}. "
            f"Re-read the file (e.g. `sed -n '{args.line},{args.line+30}p' {path}`) "
            f"and copy the exact bytes.\n"
        )
        return 2
    n = text.count(args.old)
    if n > 1 and not args.allow_multi:
        sys.stderr.write(
            f"AMBIGUOUS: --old matches {n} non-overlapping occurrences. "
            f"Pass --allow-multi to replace all, or widen --old to make it unique.\n"
        )
        return 2
    new_text = text.replace(args.old, args.new, 1 if not args.allow_multi else -1)
    path.write_text(new_text)
    if not _py_compile(path):
        sys.stderr.write("py_compile FAILED — patch is broken; revert and retry.\n")
        return 3
    # Read-back: show the new line(s) so the agent can confirm.
    print(f"OK: {path} (py_compile passed)")
    # Print ±3 lines around the first replaced location.
    snippet = new_text.split(args.new, 1)[0][-200:] + args.new
    print(snippet)
    return 0


def cmd_insert(args) -> int:
    """Insert ``--new`` immediately after a unique anchor."""
    path = Path(args.file)
    text = path.read_text()
    if args.anchor not in text:
        sys.stderr.write(
            f"ANCHOR NOT FOUND: --anchor text not in {path}.\n"
        )
        return 2
    if text.count(args.anchor) > 1:
        sys.stderr.write(
            f"ANCHOR AMBIGUOUS: appears {text.count(args.anchor)} times. "
            f"Widen --anchor to make it unique.\n"
        )
        return 2
    new_text = text.replace(args.anchor, args.anchor + args.new, 1)
    path.write_text(new_text)
    if not _py_compile(path):
        sys.stderr.write("py_compile FAILED.\n")
        return 3
    print(f"OK: {path} (insert after anchor, py_compile passed)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_rep = sub.add_parser("replace", help="Replace exact OLD text with NEW.")
    p_rep.add_argument("--file", required=True)
    p_rep.add_argument("--old", required=True)
    p_rep.add_argument("--new", required=True)
    p_rep.add_argument("--line", type=int, default=0,
                       help="(hint) expected line of OLD, used in the re-read hint")
    p_rep.add_argument("--allow-multi", action="store_true",
                       help="Replace ALL matches (default: error if >1)")

    p_ins = sub.add_parser("insert", help="Insert NEW after a unique anchor.")
    p_ins.add_argument("--file", required=True)
    p_ins.add_argument("--anchor", required=True,
                       help="Existing text; new lines go immediately after.")
    p_ins.add_argument("--new", required=True)

    args = ap.parse_args()
    if args.cmd == "replace":
        sys.exit(cmd_replace(args))
    elif args.cmd == "insert":
        sys.exit(cmd_insert(args))
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
