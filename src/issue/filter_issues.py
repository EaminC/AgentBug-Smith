#!/usr/bin/env python3
"""
Filter issues with only one PR and save each as a separate JSON file
"""

import json
import os
import sys
from pathlib import Path


def filter_and_save_issues(input_json_path: str, output_dir: str):
    """
    Read JSON file, filter issues with only one linked_pr, and save to output directory
    
    Args:
        input_json_path: Input JSON file path
        output_dir: Output directory path (issue-filtered folder)
    """
    # Read input JSON file
    print(f"Reading file: {input_json_path}")
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get issues list
    issues = data.get('issues', [])
    print(f"Found {len(issues)} issues in total")
    
    # Filter issues with only one linked_pr
    filtered_issues = []
    for issue in issues:
        linked_prs = issue.get('linked_prs', [])
        if len(linked_prs) == 1:
            filtered_issues.append(issue)
    
    print(f"Filtered {len(filtered_issues)} issues with only one PR")
    
    # Create output directory (if it doesn't exist)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_path}")
    
    # Save each issue as a separate JSON file
    saved_count = 0
    for issue in filtered_issues:
        issue_number = issue.get('number')
        if issue_number is None:
            print(f"Warning: Skipping issue without number")
            continue
        
        # Filename format: issue_{number}.json
        filename = f"issue_{issue_number}.json"
        filepath = output_path / filename
        
        # Save single issue to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(issue, f, indent=2, ensure_ascii=False)
        
        saved_count += 1
        if saved_count % 10 == 0:
            print(f"Saved {saved_count} files...")
    
    print(f"\nDone! Saved {saved_count} issue files to {output_path}")
    return saved_count


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python filter_issues.py <input_json_file> [output_dir]")
        print("Example: python filter_issues.py ../data/hooked_issue/openai-codex-20251013/issue.json ../data/issue-filtered")
        sys.exit(1)
    
    input_json_path = sys.argv[1]
    
    # If output directory is not specified, default to data/issue-filtered
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        # Default output directory
        script_dir = Path(__file__).parent
        workspace_root = script_dir.parent.parent
        output_dir = workspace_root / "data" / "issue-filtered"
    
    # Check if input file exists
    if not os.path.exists(input_json_path):
        print(f"Error: Input file does not exist: {input_json_path}")
        sys.exit(1)
    
    # Execute filtering and saving
    try:
        filter_and_save_issues(input_json_path, str(output_dir))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
