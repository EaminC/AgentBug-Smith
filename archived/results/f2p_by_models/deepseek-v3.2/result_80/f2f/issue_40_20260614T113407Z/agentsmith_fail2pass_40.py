import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.utils.system import run_command


def test_run_command_iterates_all_commands():
    """
    Direct test of run_command to ensure it iterates over all commands.
    This test should pass after the fix where run_command processes all commands.
    """
    # Test commands
    commands = ['echo first', 'echo second', 'echo third']
    
    # Mock subprocess.Popen to capture calls
    with patch('subprocess.Popen') as mock_popen:
        # Create a mock process that simulates successful command execution
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [b'output\n', b'']
        mock_process.poll.side_effect = [None, 0]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Call run_command with the list of commands
        results = run_command(commands)
        
        # After the fix, run_command should process all commands
        # Check that Popen was called the correct number of times
        assert mock_popen.call_count == len(commands), \
            f"Expected {len(commands)} Popen calls, got {mock_popen.call_count}. " \
            "Bug: run_command doesn't iterate over all commands."
        
        # Check that results contain output for all commands
        assert isinstance(results, list), \
            f"run_command should return a list of tuples, got {type(results)}"
        assert len(results) == len(commands), \
            f"Expected {len(commands)} results, got {len(results)}"


def test_run_command_with_single_command():
    """
    Test that run_command still works correctly with a single command string.
    """
    single_command = 'echo hello world'
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [b'hello world\n', b'']
        mock_process.poll.side_effect = [None, 0]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        results = run_command(single_command)
        
        # With a single command, run_command should still work
        assert mock_popen.call_count == 1, \
            f"Expected 1 Popen call for single command, got {mock_popen.call_count}"
        
        # The result should be appropriate for a single command
        # (could be a tuple or a list with one element depending on implementation)
        if isinstance(results, list):
            assert len(results) == 1, \
                f"Expected list with 1 element for single command, got {len(results)}"
        else:
            # Might be a tuple for backward compatibility
            assert isinstance(results, tuple), \
                f"Expected tuple for single command result, got {type(results)}"


def test_run_command_handles_command_failure():
    """
    Test that run_command handles command failures appropriately.
    """
    commands = ['echo success', 'false', 'echo after_failure']
    
    with patch('subprocess.Popen') as mock_popen:
        # Create different mock processes for different commands
        def create_mock_process(exit_code=0):
            process = MagicMock()
            process.stdout.readline.side_effect = [b'output\n', b'']
            process.poll.side_effect = [None, exit_code]
            process.wait.return_value = exit_code
            return process
        
        # First command succeeds
        mock_popen.side_effect = [
            create_mock_process(0),  # echo success
            create_mock_process(1),  # false (fails)
            create_mock_process(0)   # echo after_failure
        ]
        
        results = run_command(commands)
        
        # Should still process all commands despite failures
        assert mock_popen.call_count == len(commands), \
            f"Expected {len(commands)} Popen calls even with failures, got {mock_popen.call_count}"
        
        # Should return results for all commands
        assert isinstance(results, list), \
            f"run_command should return a list of tuples even with failures, got {type(results)}"
        assert len(results) == len(commands), \
            f"Expected {len(commands)} results even with failures, got {len(results)}"