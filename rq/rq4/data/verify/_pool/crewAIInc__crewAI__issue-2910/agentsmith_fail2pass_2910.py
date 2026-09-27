import re
import pytest
from pathlib import Path
from packaging import version as pkg_version
import crewai

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python 3.10


def test_crewai_litellm_dependency_support():
    """
    Issue #2910: CrewAI requires litellm >= 1.72.0 to support OpenAI 1.78.0+ multi-image features.
    Verifies that CrewAI's active project manifest defines the upgraded dependency.
    """
    # Assert CrewAI core modules are imported and functional
    assert hasattr(crewai, "Agent"), "crewai.Agent missing"
    assert hasattr(crewai, "Crew"), "crewai.Crew missing"
    assert hasattr(crewai, "Task"), "crewai.Task missing"

    # Dynamically locate the active crewai project root from the imported module
    # crewai.__file__ is /app/src/crewai/__init__.py -> root is /app
    crewai_root = Path(crewai.__file__).resolve().parents[2]
    pyproject_path = crewai_root / "pyproject.toml"

    # Fallback to current working directory if pyproject.toml is not at parents[2]
    if not pyproject_path.exists():
        pyproject_path = Path("pyproject.toml")

    assert pyproject_path.exists(), f"Could not find pyproject.toml at {pyproject_path}"

    # Parse dependencies declared by CrewAI
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = config.get("project", {}).get("dependencies", [])
    litellm_spec = None
    for dep in dependencies:
        if dep.strip().startswith("litellm"):
            litellm_spec = dep
            break

    assert litellm_spec is not None, "litellm dependency not declared in CrewAI's pyproject.toml"

    # Extract version from specifier (e.g., 'litellm==1.72.0' -> '1.72.0')
    match = re.search(r"(\d+\.\d+(\.\d+)?)", litellm_spec)
    assert match is not None, f"Could not parse version from CrewAI specifier: {litellm_spec}"

    declared_version = match.group(1)

    # Assert compatibility:
    # Buggy state has "1.68.0" -> FAILS (Exit code: 1)
    # Patched state has "1.72.0" -> PASSES (Exit code: 0)
    assert pkg_version.parse(declared_version) >= pkg_version.parse("1.72.0"), (
        f"CrewAI declared requirement '{litellm_spec}' is incompatible with openai >= 1.78.0. "
        f"Expected litellm >= 1.72.0."
    )