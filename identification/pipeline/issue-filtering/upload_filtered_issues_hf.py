import os
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import upload_file

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "alfin06/swegent-issues-filtered"
REPO_TYPE = "dataset"

# Define keys that should be lists if they are empty/null
# Based on your example, 'labels' and 'linked_prs' are lists.
LIST_FIELDS = {"labels", "linked_prs"}

def sanitize_data(data):
    """
    Recursively cleans data to ensure consistency:
    - None -> "" (for strings)
    - None -> [] (for known list fields)
    """
    cleaned = {}
    
    for key, value in data.items():
        # 1. Handle Lists (labels, linked_prs)
        if key in LIST_FIELDS:
            if value is None:
                cleaned[key] = []
            elif isinstance(value, list):
                # Recursively clean items inside the list
                cleaned[key] = [sanitize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = []
                
        # 2. Handle Nested Dictionaries (ai_judgment)
        elif isinstance(value, dict):
            cleaned[key] = sanitize_data(value)
            
        # 3. Handle Nulls (The main cause of your error)
        elif value is None:
            cleaned[key] = "" 
            
        # 4. Keep everything else as is
        else:
            cleaned[key] = value
            
    return cleaned

def main():
    base_dir = Path(__file__).parent.parent.parent.parent / "data"
    filtered_dir = base_dir / "issue-filtered"
    output_file = base_dir / "data.jsonl"

    if not filtered_dir.is_dir():
        print(f"[X] Directory not found: {filtered_dir}")
        return

    issue_files = list(filtered_dir.glob("issue_*.json"))
    print(f"Found {len(issue_files)} files. processing...")

    # --- STEP 1: CONVERT TO JSONL ---
    successful_count = 0
    
    with open(output_file, "w", encoding="utf-8") as outfile:
        for issue_file in issue_files:
            try:
                with open(issue_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                
                # Sanitize to prevent "Type String to Null" errors
                clean_entry = sanitize_data(raw_data)
                
                # Write to JSONL (dump json + newline)
                outfile.write(json.dumps(clean_entry) + "\n")
                successful_count += 1
                
            except Exception as e:
                print(f"[X] Error reading {issue_file.name}: {e}")

    print(f"Successfully compiled {successful_count} issues into {output_file.name}")

    # --- STEP 2: UPLOAD ---
    if successful_count > 0:
        print(f"Uploading {output_file.name} to Hugging Face...")
        try:
            upload_file(
                path_or_fileobj=str(output_file),
                path_in_repo="data.jsonl",
                repo_id=REPO_ID,
                repo_type=REPO_TYPE,
                token=HF_TOKEN
            )
            print("[OK] Upload Complete!")
            print(f"Check your dataset at: https://huggingface.co/datasets/{REPO_ID}")
        except Exception as e:
            print(f"[X] Upload failed: {e}")

if __name__ == "__main__":
    main()