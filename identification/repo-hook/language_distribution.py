import json
import os
from collections import Counter

# Path to the JSON file
json_path = 'data/hooked_repo/agent_repo.json'

def get_language_from_extension(ext):
    """
    Maps file extensions to their proper programming language names.
    """
    mapping = {
        # High Priority (Actual Code)
        '.py': 'Python',
        '.pyc': 'Python',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript',
        '.js': 'JavaScript',
        '.mjs': 'JavaScript',
        '.cjs': 'JavaScript',
        '.rs': 'Rust',
        '.go': 'Go',
        '.dart': 'Dart',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.swift': 'Swift',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.cs': 'C#',
        
        # Domain Specific / Niche
        '.jac': 'Jac',
        '.baml': 'BAML',
        '.pddl': 'PDDL',
        
        # Shell / Scripts (Medium Priority)
        '.sh': 'Shell',
        '.bash': 'Shell',
    }
    return mapping.get(ext)

def infer_primary_language(repo_data):
    """
    Infers language by prioritizing code over config.
    """
    # 1. Use explicit tag if available and valid
    if 'language' in repo_data and repo_data['language'] != 'Unknown':
        return repo_data['language']

    paths = repo_data.get('test_paths', [])
    if not paths:
        return 'Unknown'

    # 2. Extract all extensions
    all_extensions = [os.path.splitext(p)[1].lower() for p in paths]
    
    # 3. Separate into "Code" vs "Noise"
    code_langs = []
    
    for ext in all_extensions:
        lang = get_language_from_extension(ext)
        if lang:
            code_langs.append(lang)

    # 4. Decision Logic
    if code_langs:
        # If we found ANY code files, return the most common one.
        return Counter(code_langs).most_common(1)[0][0]
    
    # 5. Fallback for edge cases (e.g. only .yaml or .json files found)
    # If a repo ONLY has .yaml, it might be a prompt-pack or dataset.
    # We check the raw extensions again to see what's there.
    raw_counts = Counter(all_extensions).most_common(1)
    if not raw_counts:
        return 'Unknown'
        
    top_ext = raw_counts[0][0]
    
    # Map known non-code types
    if top_ext in ['.yaml', '.yml', '.json', '.jsonl', '.toml', '.md', '.txt', '.png', '.snap']:
        return 'Configuration/Data' 
        
    return f"Other ({top_ext})"

# --- MAIN EXECUTION ---

# Load Data
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

repo_list = data.get('repositories', [])

agents = []
languages = []

for agent in repo_list:
    name = agent.get('name', 'Unknown')
    lang = infer_primary_language(agent)
    
    agents.append((name, lang))
    languages.append(lang)

# Display Table
print(f"{'Agent Name':<50} | Programming Language")
print("-" * 80)
for name, lang in agents:
    # Truncate very long names for display
    display_name = (name[:47] + '..') if len(name) > 47 else name
    print(f"{display_name:<50} | {lang}")

# Display Summary
print("\n" + "="*30)
print("FINAL SUMMARY BY LANGUAGE")
print("="*30)
lang_counts = Counter(languages)

# Sort by count (descending)
for lang, count in lang_counts.most_common():
    print(f"{lang:<20}: {count}")