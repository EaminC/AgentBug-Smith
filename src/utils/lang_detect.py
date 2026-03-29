# src/utils/lang_detect.py
from pathlib import Path
from typing import Dict

def detect_project_language(repo_root: Path) -> Dict[str, str]:
    """
    Detects the programming language based on repository configuration files.
    Returns a dictionary with the language name, file extension, and test runner.
    """
    repo_root = Path(repo_root).resolve()

    if (repo_root / "package.json").exists():
        if (repo_root / "tsconfig.json").exists():
            return {"name": "TypeScript", "ext": ".ts", "runner": "npx ts-node"}
        return {"name": "JavaScript", "ext": ".js", "runner": "node"}
        
    elif (repo_root / "Cargo.toml").exists():
        return {"name": "Rust", "ext": ".rs", "runner": "cargo test --test"}
        
    elif (repo_root / "pom.xml").exists() or (repo_root / "build.gradle").exists():
        return {"name": "Java", "ext": ".java", "runner": "mvn test -Dtest="}
        
    elif (repo_root / "go.mod").exists():
        return {"name": "Go", "ext": ".go", "runner": "go test"}
        
    # Default to Python if pyproject.toml, requirements.txt, or nothing is found
    return {"name": "Python", "ext": ".py", "runner": "python -m pytest -q"}