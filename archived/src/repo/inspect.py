import os
from pathlib import Path

def get_file_tree(root_dir: str | Path, n: int = 3, prefix: str = "") -> str:
    """
    Generates a visual tree structure of the directory up to depth n.
    Equivalent to 'tree -L n'.
    """
    root = Path(root_dir)
    if n < 0: return ""
    
    output = []
    if prefix == "":
        output.append(f"{root.name}/")
        
    # Get sorted items, skipping common ignored directories
    items = sorted([item for item in root.iterdir() if item.name not in {'.git', '__pycache__', 'venv'}])
    
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        output.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
        
        if item.is_dir() and n > 1:
            extension = "    " if is_last else "│   "
            output.append(get_file_tree(item, n - 1, prefix + extension))
            
    return "\n".join(filter(None, output))