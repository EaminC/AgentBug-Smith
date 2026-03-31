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
    verbose: bool = False,
    language: str = "Python"
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
    
    template = prompt_path.read_text(encoding='utf-8')

    # 2. Gather current file contents for context
    df_path = repo_path / dockerfile
    tf_path = repo_path / test_relpath if test_relpath else None
    
    current_docker = df_path.read_text(encoding='utf-8') if df_path.exists() else "# Not found"
    current_test = tf_path.read_text(encoding='utf-8') if (tf_path and tf_path.exists()) else "# Not found"

    safe_feedback = feedback if feedback is not None else "No feedback provided from the previous run."

    # 3. Format prompt safely (DO NOT USE .format() because code contains {})
    prompt = template.replace("{language}", language)
    prompt = prompt.replace("{dockerfile_content}", current_docker)
    prompt = prompt.replace("{test_file_content}", current_test)
    prompt = prompt.replace("{feedback}", safe_feedback)

    client = LLMClient()
    system_msg = (
        f"You are a senior {language} DevOps and QA engineer. Analyze the provided feedback "
        "and return corrected versions of the Dockerfile and test file."
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

def _apply_repairs(
    repo_path: Path,
    docker_rel: str,
    test_rel: str,
    response: str,
    verbose: bool
) -> bool:
    """
    Extracts code blocks from the LLM response and saves them to the repo.

    Features:
    - Case-insensitive detection of Dockerfile blocks
    - Supports multiple languages for test files
    - Handles multiple code blocks (uses the last occurrence)
    - Writes files using UTF-8 encoding
    """
    applied = False

    # Extract Dockerfile blocks
    docker_pattern = r"```(?:dockerfile)\n(.*?)\n```" 
    docker_matches = re.findall(docker_pattern, response, re.DOTALL | re.IGNORECASE)

    if docker_matches:
        docker_content = docker_matches[-1].strip()
        (repo_path / docker_rel).write_text(docker_content, encoding="utf-8")
        applied = True
        if verbose:
            print(f"[cofix] Overwrote {docker_rel}")

    # Extract Test file blocks (multiple languages)
    test_pattern = r"```(?:python|py|javascript|js|typescript|ts|rust|rs)\n(.*?)\n```" 
    test_matches = re.findall(test_pattern, response, re.DOTALL | re.IGNORECASE)

    if test_matches and test_rel:
        test_content = test_matches[-1].strip()
        (repo_path / test_rel).write_text(test_content, encoding="utf-8")
        applied = True
        if verbose:
            print(f"[cofix] Overwrote {test_rel}")

    return applied