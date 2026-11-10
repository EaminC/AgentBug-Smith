import os
import sys
import subprocess
import tempfile
import textwrap

import pytest


@pytest.fixture
def temp_crew_project():
    """
    Create a temporary directory with a valid crew.py file that defines at least one valid Crew instance.
    This is to simulate the environment where `utils.get_crews` will find crew.py and load Crew instances.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Write a valid crew.py that defines a Crew instance with required fields
        # We import Crew and Agent from crewai to create a valid crew instance
        crew_content = textwrap.dedent(
            """
            from crewai.crew import Crew
            from crewai.agent import Agent

            # Create a valid Agent instance
            agent = Agent(role="test_role", goal="test_goal", backstory="test_backstory")

            # Create a valid Crew instance with agents and tasks
            valid_crew = Crew(agents=[agent], tasks=[])
            """
        )

        with open("crew.py", "w") as f:
            f.write(crew_content)

        # Also create a src directory with crew.py to test that search includes src/
        os.makedirs("src", exist_ok=True)
        with open(os.path.join("src", "crew.py"), "w") as f:
            f.write(crew_content)

        # Create a src/templates directory with crew.py that should be ignored
        os.makedirs(os.path.join("src", "templates"), exist_ok=True)
        with open(os.path.join("src", "templates", "crew.py"), "w") as f:
            f.write("# This crew.py should be ignored by get_crews")

        yield temp_dir

        os.chdir(old_cwd)


def test_get_crews_returns_crews_and_no_errors(temp_crew_project):
    """
    This test verifies that the get_crews function:
    - Finds Crew instances from crew.py in current and src directories
    - Ignores crew.py files in templates directories
    - Does not raise errors about undefined names (JsonValue, TaskOutput, Task)
    - Does not print "No crew found" error when crew.py exists
    """

    # Compose a small python script to run inside the temp_crew_project directory
    # It imports utils.get_crews and calls it with require=True to trigger error if no crew found.
    # It prints the number of crews found.
    script = textwrap.dedent(
        """
        import sys
        from crewai.cli import utils

        try:
            crews = utils.get_crews(crew_path="crew.py", require=True)
            # Print number of crews found for verification
            print(f"Found {len(crews)} crew(s)")
        except SystemExit as e:
            print(f"SystemExit with code: {e.code}")
            sys.exit(e.code if e.code is not None else 1)
        except Exception as e:
            print(f"Unexpected exception: {e}")
            sys.exit(1)
        """
    )

    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=temp_crew_project,
        capture_output=True,
        text=True,
        timeout=10,
    )

    stdout = proc.stdout
    stderr = proc.stderr

    # The buggy code will fail with SystemExit or print errors about undefined names or "No crew found"
    # The fixed code will succeed and print "Found N crew(s)" with N > 0

    assert proc.returncode == 0, f"Process failed with code {proc.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    assert "Found" in stdout, f"Expected 'Found' in stdout but got:\n{stdout}"
    # Also assert that at least one crew was found
    found_count = 0
    for line in stdout.splitlines():
        if line.startswith("Found "):
            try:
                found_count = int(line.split()[1])
            except Exception:
                pass
    assert found_count > 0, f"Expected at least one crew found but got {found_count}"
