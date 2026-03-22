#!/usr/bin/env python3
"""
The "Universal" Dockerfile Generator.
"""

import sys
import re
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from tools.api.main import chat  # noqa: E402

# --- Configuration ---
TARGET_FILES = [
    "README.md", "Dockerfile", "docker-compose.yml", "Makefile", "Justfile",
    "pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "poetry.lock",
    "package.json", 
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "CMakeLists.txt", "configure", "configure.ac",
    "go.mod", "Cargo.toml"
]

TARGET_GLOBS = [
    "src/main.*", "src/index.*", "app/main.*", "main.*", "index.*",
    "*/package.json", "*/pom.xml", "*/build.gradle", "*/CMakeLists.txt"
]

# --- Helper Functions ---

def scan_dependency_manifest(repo_root: Path) -> str:
    manifest = ["--- TRUTH MANIFEST: DETECTED CONFIG FILES ---"]
    manifest.append("You MUST rely on this list. If a file is not listed here, IT DOES NOT EXIST.")
    
    checks = [
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "requirements.txt", "pyproject.toml", "poetry.lock", "Pipfile",
        "pom.xml", "build.gradle", "gradlew",
        "Makefile", "CMakeLists.txt", "go.mod"
    ]
    
    found_files = []
    for pattern in checks:
        for path in repo_root.rglob(pattern):
            if any(x in path.parts for x in ["node_modules", ".venv", ".git", "target", "build"]): continue
            rel_path = path.relative_to(repo_root)
            found_files.append(str(rel_path))
            
    if found_files:
        for f in sorted(found_files): manifest.append(f"[EXISTING] {f}")
    else:
        manifest.append("CRITICAL: No standard build configuration found. Rely on README.md.")
    manifest.append("------------------------------------------------")
    return "\n".join(manifest)

def get_directory_tree(startpath: Path, max_depth: int = 3) -> str:
    tree_str = []
    startpath = startpath.resolve()
    for path in sorted(startpath.rglob('*')):
        if any(x in path.parts for x in ['.git', '__pycache__', 'node_modules', '.venv', 'target', 'build', 'dist']): continue
        depth = len(path.relative_to(startpath).parts)
        if depth > max_depth: continue
        indent = '    ' * (depth - 1)
        tree_str.append(f"{indent}|-- {path.name}{'/' if path.is_dir() else ''}")
    return "\n".join(tree_str)

def read_files(repo_root: Path, files: List[Path]) -> List[Dict[str, str]]:
    results = []
    for file in files:
        if not file.exists(): continue
        rel_path = file.relative_to(repo_root)
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            if ("lock" in file.name or "gradlew" in file.name) and len(content) > 1000:
                content = "(Content Truncated: File Exists)"
            results.append({"path": str(rel_path), "content": content})
        except: pass
    return results

def find_target_files(repo_root: Path) -> List[Path]:
    found = set()
    for name in TARGET_FILES:
        p = repo_root / name
        if p.exists(): found.add(p)
    for pattern in TARGET_GLOBS:
        for p in repo_root.glob(pattern): found.add(p)
    return list(found)

# --- Updated Prompt Logic ---

def build_prompt(file_entries: List[Dict[str, str]], tree: str, manifest: str) -> str:
    has_poetry = any("pyproject.toml" in item['path'] for item in file_entries)
    has_requirements = any("requirements.txt" in item['path'] for item in file_entries)

    parts = [
        "You are a DevOps expert. Generate a `env.dockerfile` for this repository.",
        "",
        manifest, 
        "",
        "--- DIRECTORY TREE ---",
        tree,
        "",
        "--- FILE CONTENTS ---",
    ]
    
    repro_script = None
    for item in file_entries:
        fname = Path(item['path']).name
        if fname.startswith("test") and fname.endswith(".py"):
            repro_script = item['path']
            break
        if fname.startswith("reproduce") and fname.endswith(".py"):
            repro_script = item['path']
            break

    if has_poetry:
        phase_2_instructions = """**PHASE 2: PYTHON (POETRY STRATEGY)**
1. **Install Poetry via Pip:** `RUN pip install poetry`.
2. **Disable Virtualenvs:** `RUN poetry config virtualenvs.create false`.
3. **Stability:** `RUN poetry config installer.max-workers 1` (Fixes IncompleteRead).
4. **Install:** `RUN poetry install --no-root --with dev`.
"""
    elif has_requirements:
        phase_2_instructions = """**PHASE 2: PYTHON (PIP STRATEGY)**
1. **Mirror:** Ensure `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/` is set via ENV.
2. **Install:** `COPY requirements.txt .` -> `RUN pip install --no-cache-dir -r requirements.txt`.
"""
    else:
        phase_2_instructions = "**PHASE 2: PYTHON**\nNo standard dependency file found. Rely on manual `pip install` commands if seen in README."

    parts.append(f"""
--- INSTRUCTIONS ---
**GOAL:** Create a stable, flat Dockerfile for reproduction.

**PHASE 1: NETWORK STABILITY (ALIYUN MIRROR)**
**Base:** `python:3.12-slim`.
Use this exact block to fix Debian network timeouts:
```dockerfile
RUN sed -i 's/deb.debian.org/[mirrors.aliyun.com/g](https://mirrors.aliyun.com/g)' /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 --fix-missing curl git build-essential && rm -rf /var/lib/apt/lists/*

{phase_2_instructions}
                 
**PHASE 3: SETUP & ENTRYPOINT**
1. Python Path: ENV PYTHONPATH=/app
2. Copying: - COPY dependency files first.
COPY the main source folder (e.g., src or [repository name]).
COPY the reproduction script: {f'{repro_script}' if repro_script else 'Detect from file list'}.
3. CMD: If a reproduction script like {repro_script or 'test13.py'} exists, the CMD MUST be: CMD ["python3", "{repro_script or 'test13.py'}"]
Do NOT use poetry run in CMD. Just python3.

**PHASE 4: NODE.JS (If Applicable)**
1. If package.json exists: RUN npm config set registry https://registry.npmmirror.com (Aliyun Mirror).

**PHASE 5: OTHER LANGUAGES**
1. **Java:** Use `openjdk` + `./gradlew` (if exists).
2. **C++:** Check `README.md` for build steps.

**PHASE 6: TEST STAGE**
- Attempt to run tests (`poetry run pytest`, `npm test`, etc.).
- Allow failure: `... || echo "Tests failed"` (Do not break build).

**OUTPUT:**
- Raw Dockerfile text only.
""")
    return "\n".join(parts)

def ask_ai(prompt: str, model: str = "openkey/gpt-4o") -> str:
    messages = [
        {"role": "system", "content": "You are a code generator. Output raw Dockerfile only."},
        {"role": "user", "content": prompt},
    ]
    response = chat(messages=messages, model=model)
    return re.sub(r"```.*", "", response, flags=re.MULTILINE).strip()

def main():
    repo_root = Path.cwd()
    print(f"Scanning {repo_root}...")
    manifest = scan_dependency_manifest(repo_root)
    tree = get_directory_tree(repo_root)
    files = find_target_files(repo_root)
    file_contents = read_files(repo_root, files)
    
    prompt = build_prompt(file_contents, tree, manifest)
    print("Generating Dockerfile...")
    dockerfile_content = ask_ai(prompt)
    
    out_path = repo_root / "env.dockerfile"
    out_path.write_text(dockerfile_content, encoding="utf-8")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()