import sys
import re
from pathlib import Path
from forge.api import LLMClient

def cofix_agent(
    repo_path: Path,
    dockerfile: str = "env.dockerfile",
    test_relpath: str = None,
    feedback: str = "",
    model: str = "gpt-4.1-mini",
    project_root: Path = None,
    verbose: bool = False
) -> tuple[bool, str]:
    """
    Refines Dockerfile and Test file using a specialized cofix prompt.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    # 1. Load the specialized cofix prompt
    prompt_path = project_root / "prompt" / "testgen" / "cofix.txt"
    if not prompt_path.exists():
        return False, f"Cofix prompt missing at {prompt_path}"
    
    template = prompt_path.read_text()

    # 2. Gather current file contents for context
    df_path = repo_path / dockerfile
    tf_path = repo_path / test_relpath if test_relpath else None
    
    current_docker = df_path.read_text() if df_path.exists() else "# Not found"
    current_test = tf_path.read_text() if (tf_path and tf_path.exists()) else "# Not found"

    # 3. Format prompt and call LLM
    prompt = template.format(
        dockerfile_content=current_docker,
        test_file_content=current_test,
        feedback=feedback
    )

    client = LLMClient()
    system_msg = (
        "You are a senior DevOps and QA engineer. Analyze the provided feedback "
        "and return corrected versions of the Dockerfile and Python test file."
    )

    if verbose:
        print(f"[cofix] Sending request to {model}...")

    try:
        response = client.simple_chat(
            prompt,
            system_prompt=system_msg,
            temperature=0.2
        )
        
        # 4. Parse response and overwrite files
        success = _apply_repairs(repo_path, dockerfile, test_relpath, response, verbose)
        return success, response

    except Exception as e:
        return False, f"LLM Error: {str(e)}"

def _apply_repairs(repo_path: Path, docker_rel: str, test_rel: str, response: str, verbose: bool) -> bool:
    """
    Extracts code blocks from the LLM response and saves them to the repo.
    """
    applied = False
    
    # Extract Dockerfile (looks for ```dockerfile ... ```)
    docker_match = re.search(r"```dockerfile\n(.*?)\n```", response, re.DOTALL)
    if docker_match:
        (repo_path / docker_rel).write_text(docker_match.group(1).strip())
        applied = True
        if verbose: print(f"[cofix] Overwrote {docker_rel}")

    # Extract Python Test (looks for ```python ... ```)
    test_match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
    if test_match and test_rel:
        (repo_path / test_rel).write_text(test_match.group(1).strip())
        applied = True
        if verbose: print(f"[cofix] Overwrote {test_rel}")

    return applied