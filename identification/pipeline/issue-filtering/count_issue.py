import os
import glob

# Try both possible relative paths for issue-filtered
possible_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/issue-filtered")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/issue-filtered")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "data/issue-filtered")),
    os.path.join(os.path.dirname(__file__), "../../data/issue-filtered"),
    os.path.join(os.path.dirname(__file__), "../../../data/issue-filtered"),
    os.path.join(os.path.dirname(__file__), "data/issue-filtered"),
]

found_dir = None
for d in possible_dirs:
    if os.path.isdir(d):
        found_dir = d
        break

if not found_dir:
    print("Could not find issue-filtered directory. Tried:")
    for d in possible_dirs:
        print("  ", d)
    exit(1)

print("Resolved issue-filtered directory:", found_dir)
print("Files in directory:", os.listdir(found_dir))

issue_files = glob.glob(os.path.join(found_dir, "issue_*.json"))
print("Matched files:", issue_files)
print("Number of issue_*.json files in issue-filtered:", len(issue_files))