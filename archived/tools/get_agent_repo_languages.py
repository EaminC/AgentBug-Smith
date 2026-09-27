"""
get_agent_repo_languages.py

This script scans all issue_*.json files in a specified issues folder, extracts the agent_name/repo from the 'url' field, and determines the programming language used in each repo. If test_paths_in_patch is present, it infers the language from file extensions. If not, it parses the patch to infer the language from changed file paths.

Usage:
    python tools/get_agent_repo_languages.py

Output:
    Prints agent_name/repo and its detected programming language(s).
"""

import os
import json
from pathlib import Path
import re
from urllib.parse import urlparse

# Path to the issues folder
ISSUES_DIR = "data/issues_50"

def get_agent_repo_from_url(url):
    try:
        parts = urlparse(url)
        path_parts = parts.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
    except Exception:
        pass
    return "unknown/unknown"

def infer_language_from_extension(paths):
    ext_lang_map = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.java': 'Java', '.go': 'Go', '.rs': 'Rust',
        '.cpp': 'C++', '.c': 'C', '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#', '.kt': 'Kotlin', '.swift': 'Swift',
        '.m': 'Objective-C', '.scala': 'Scala', '.sh': 'Shell', '.pl': 'Perl', '.r': 'R', '.jl': 'Julia',
        '.dart': 'Dart', '.lua': 'Lua', '.groovy': 'Groovy', '.sql': 'SQL',
    }
    langs = set()
    for path in paths:
        ext = Path(path).suffix.lower()
        if ext in ext_lang_map:
            langs.add(ext_lang_map[ext])
    return langs

def main():
    print("issue_id, agent_name/repo, language(s)")
    lang_issue_count = {}
    for fname in os.listdir(ISSUES_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(ISSUES_DIR, fname)
        try:
            issue_id = fname.replace('issue_', '').replace('.json', '')
            with open(fpath, 'r') as f:
                data = json.load(f)
            url = data.get('url', '')
            agent_repo = get_agent_repo_from_url(url)
            if agent_repo == "unknown/unknown":
                print(f"{issue_id}, {agent_repo}, UNKNOWN")
                continue
            test_paths = []
            if 'linked_prs' in data and data['linked_prs']:
                test_paths = data['linked_prs'][0].get('test_paths_in_patch', [])
            if not test_paths:
                test_paths = data.get('test_paths_in_patch', [])
            langs = set()
            if test_paths:
                langs = infer_language_from_extension(test_paths)
                if langs:
                    print(f"{issue_id}, {agent_repo}, {', '.join(sorted(langs))}")
                else:
                    print(f"{issue_id}, {agent_repo}, UNKNOWN (test paths present but no known extension)")
            else:
                # No patch test, try to infer from patch
                patch = None
                if 'linked_prs' in data and data['linked_prs'] and 'patch' in data['linked_prs'][0]:
                    patch = data['linked_prs'][0]['patch']
                if patch:
                    file_paths = [m.group(1) for m in re.finditer(r'diff --git a/(\S+)', patch)]
                    langs = infer_language_from_extension(file_paths)
                    if langs:
                        print(f"{issue_id}, {agent_repo}, {', '.join(sorted(langs))}")
                    else:
                        print(f"{issue_id}, {agent_repo}, UNKNOWN (patch present but no known extension)")
                else:
                    print(f"{issue_id}, {agent_repo}, UNKNOWN (no patch test or patch)")
            # Count for summary
            for lang in langs:
                lang_issue_count[lang] = lang_issue_count.get(lang, 0) + 1
        except Exception as e:
            print(f"Error processing {fname}: {e}")

    # Print summary
    print("\nSummary by programming language:")
    for lang, count in sorted(lang_issue_count.items(), key=lambda x: (-x[1], x[0])):
        print(f"{lang}: {count}")

if __name__ == "__main__":
    main()
