import os
import shutil
import tempfile
import unittest
from pathlib import Path

from aider.coders import editblock_coder as eb


class TestFileCreationRegression(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to simulate repo files
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)

        # Create a sample existing file path
        self.existing_file_path = Path(self.tmpdir) / "path" / "to" / "a" / "file1.txt"
        self.existing_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.existing_file_path.write_text("one\n")

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_new_file_created_in_same_folder(self):
        """
        This test verifies that the editblock_coder.find_original_update_blocks correctly
        detects edits that create new files (empty SEARCH block) and edits to existing files.

        Before the fix, the code would fail to detect the new file creation properly,
        causing the test to fail. After the fix, it should detect both edits correctly.
        """
        edit = """
Here's the change:

path/to/a/file2.txt
```python
<<<<<<< SEARCH
=======
three
>>>>>>> REPLACE
```

another change

path/to/a/file1.txt
```python
<<<<<<< SEARCH
one
=======
two
>>>>>>> REPLACE
```

Hope you like it!
"""

        # Provide valid_fnames only for existing file to simulate repo files known
        edits = list(
            eb.find_original_update_blocks(edit, valid_fnames=["path/to/a/file1.txt"])
        )
        # We expect two edits:
        # - One creating new file path/to/a/file2.txt with empty original content and "three\n" replacement
        # - One editing existing file path/to/a/file1.txt from "one\n" to "two\n"
        self.assertEqual(
            edits,
            [
                ("path/to/a/file2.txt", "", "three\n"),
                ("path/to/a/file1.txt", "one\n", "two\n"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
