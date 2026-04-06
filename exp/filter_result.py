import shutil
import re
from pathlib import Path

# Assuming this script is located in the exp/ folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_ROOT / "result_agent"

def categorize_results():
    if not BASE_DIR.exists():
        print(f"Error: The directory '{BASE_DIR}' does not exist.")
        return

    # Define target directories INSIDE result_agentframework
    targets = {
        "f2p": BASE_DIR / "f2p",
        "f2f": BASE_DIR / "f2f",
        "p2p": BASE_DIR / "p2p",
        "error": BASE_DIR / "error"
    }
    
    # Create target directories if they do not exist
    for target_dir in targets.values():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Iterate over all issue_* directories
    for issue_dir in BASE_DIR.glob("issue_*"):
        if not issue_dir.is_dir():
            continue
            
        f2p_file = issue_dir / "f2p.txt"
        target_category = "error"  # Default fallback
        
        if f2p_file.exists():
            try:
                # Read lines and search backwards for the last outcome
                with open(f2p_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line in reversed(lines):
                    # This regex captures the outcome AND optionally the (rc1=X, rc2=Y) string
                    match = re.search(r"outcome=(f2p|f2f|p2p|error)(?:\s*\((.*?)\))?", line.lower())
                    
                    if match:
                        base_outcome = match.group(1)
                        rc_info = match.group(2) # E.g., "rc1=126, rc2=126"
                        
                        # If the outcome is F2F, inspect the Pytest exit codes
                        if base_outcome == "f2f" and rc_info:
                            rc_match = re.search(r"rc1=(\d+),\s*rc2=(\d+)", rc_info)
                            if rc_match:
                                rc1 = int(rc_match.group(1))
                                rc2 = int(rc_match.group(2))
                                
                                # Exit code 1 means a standard test assertion failure (True F2F).
                                # Any other exit code (2, 5, 126, etc.) means the pipeline crashed.
                                if rc1 != 1 or rc2 != 1:
                                    target_category = "error"
                                    break # Stop looking, it's an error
                        
                        # If it passes the check above, assign the parsed outcome
                        target_category = base_outcome
                        break
                        
            except Exception as e:
                print(f"Error reading {f2p_file.name} in {issue_dir.name}: {e}")
        else:
            print(f"Warning: No f2p.txt found in {issue_dir.name}. Defaulting to 'error'.")
        
        dest_dir = targets.get(target_category, targets["error"])
        dest_path = dest_dir / issue_dir.name
        
        # Prevent overwriting if a folder with the same name was already moved
        if dest_path.exists():
            print(f"Warning: Destination {dest_path} already exists. Skipping {issue_dir.name}.")
            continue
            
        print(f"Moving {issue_dir.name} -> {target_category}/")
        shutil.move(str(issue_dir), str(dest_path))

if __name__ == "__main__":
    categorize_results()