import os
import shutil
import tempfile
import unittest
from unittest import mock

import yaml

from mle.utils import system


class TestCheckConfig(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to act as ~/.mle
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = self.temp_dir.name
        self.config_path = os.path.join(self.config_dir, "config.yaml")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_yaml_config(self, path, content):
        with open(path, "w") as f:
            yaml.dump(content, f)

    @mock.patch("os.path.expanduser")
    def test_check_config_with_empty_file(self, mock_expanduser):
        # Write an empty file (loads as None)
        with open(self.config_path, "w") as f:
            f.write("")

        mock_expanduser.return_value = self.config_dir
        console = mock.Mock()

        result = system.check_config(console)
        self.assertFalse(result)
        console.log.assert_called()
        # The message should mention could not be loaded or similar
        self.assertTrue(
            any("could not be loaded" in str(call.args[0]) for call in console.log.call_args_list)
        )

    @mock.patch("os.path.expanduser")
    def test_check_config_with_valid_file_no_search_key(self, mock_expanduser):
        self.write_yaml_config(self.config_path, {"some_key": "some_value"})
        mock_expanduser.return_value = self.config_dir
        console = mock.Mock()

        result = system.check_config(console)
        self.assertTrue(result)

    @mock.patch("os.path.expanduser")
    def test_check_config_with_valid_file_with_search_key(self, mock_expanduser):
        self.write_yaml_config(self.config_path, {"search_key": "dummy_key"})
        mock_expanduser.return_value = self.config_dir
        console = mock.Mock()

        # Remove SEARCH_API_KEY if set previously
        os.environ.pop("SEARCH_API_KEY", None)

        result = system.check_config(console)
        self.assertTrue(result)
        self.assertEqual(os.environ.get("SEARCH_API_KEY"), "dummy_key")

    @mock.patch("os.path.expanduser")
    @mock.patch("os.path.exists")
    def test_check_config_moves_old_config(self, mock_exists, mock_expanduser):
        # Simulate old config at ~/.mle_config.yaml
        old_config_path = os.path.abspath(os.path.join(self.config_dir, "..", ".mle_config.yaml"))
        new_config_path = self.config_path

        # Create old config file
        os.makedirs(os.path.dirname(old_config_path), exist_ok=True)
        with open(old_config_path, "w") as f:
            yaml.dump({"search_key": "old_dummy"}, f)

        # Setup mocks
        def fake_expanduser(path):
            if path == "~/.mle":
                return self.config_dir
            return os.path.expanduser(path)

        # Save original os.path.exists to avoid recursion
        original_exists = os.path.exists.__wrapped__ if hasattr(os.path.exists, "__wrapped__") else os.path.exists

        def side_effect_exists(path):
            if path == old_config_path:
                return True
            if path == new_config_path:
                return False
            # Use original os.path.exists without recursion
            return original_exists(path)

        mock_expanduser.side_effect = fake_expanduser
        mock_exists.side_effect = side_effect_exists

        console = mock.Mock()

        # Remove SEARCH_API_KEY if set previously
        os.environ.pop("SEARCH_API_KEY", None)

        # The old config file exists, new config does not, so it should move the old config
        result = system.check_config(console)
        self.assertTrue(result)
        # After move, old config should not exist, new config should exist
        self.assertFalse(os.path.exists(old_config_path))
        self.assertTrue(os.path.exists(new_config_path))
        # SEARCH_API_KEY should be set from moved config
        self.assertEqual(os.environ.get("SEARCH_API_KEY"), "old_dummy")


if __name__ == "__main__":
    unittest.main()