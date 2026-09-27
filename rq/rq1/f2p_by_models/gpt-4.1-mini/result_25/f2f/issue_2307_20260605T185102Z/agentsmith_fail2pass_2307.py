import os
import subprocess
import tempfile
import shutil


def test_reset_memories_command_behavior():
    """
    This test verifies the behavior of the `crewai reset-memories` CLI command
    when run inside a crew project directory.

    Expected behavior after fix:
    - Running `crewai reset-memories --knowledge` or `crewai reset-memories -a`
      should NOT fail with "No crew found."
    - Instead, it should output an error indicating the memory system is not initialized.

    This test creates a temporary directory simulating a crew project environment,
    runs the CLI commands, and asserts on the output and exit codes.
    """

    # Create a temporary directory to simulate a crew project
    temp_dir = tempfile.mkdtemp(prefix="crew_test_")
    try:
        # Create a minimal crew.py file that defines a crew function returning a dummy crew instance
        # This simulates the presence of a crew project to avoid "No crew found."
        crew_py_path = os.path.join(temp_dir, "crew.py")
        with open(crew_py_path, "w") as f:
            f.write(
                "class DummyCrew:\n"
                "    def _reset_specific_memory(self, memory_type):\n"
                "        raise RuntimeError(f'Failed to reset {memory_type} memory: knowledge memory system is not initialized')\n"
                "def crew():\n"
                "    return DummyCrew()\n"
            )

        # Change working directory to the temp crew project directory
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Define commands to test
        commands = [
            ["crewai", "reset-memories", "--knowledge"],
            ["crewai", "reset-memories", "-a"],
        ]

        for cmd in commands:
            # Run the command and capture output
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ,  # preserve environment variables
            )

            combined_output = result.stdout + result.stderr

            # The command should NOT fail with "No crew found."
            assert "No crew found" not in combined_output, (
                f"Command {cmd} unexpectedly failed with 'No crew found'. Output:\n{combined_output}"
            )

            # The command should fail with a RuntimeError message about knowledge memory system not initialized
            assert "Failed to reset knowledge memory: knowledge memory system is not initialized" in combined_output, (
                f"Command {cmd} did not output expected memory system error. Output:\n{combined_output}"
            )

            # The command exit code should be non-zero (failure)
            assert result.returncode != 0, (
                f"Command {cmd} unexpectedly succeeded with exit code 0."
            )

    finally:
        # Restore original working directory and clean up temp directory
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir)