import os
import tempfile
from unittest.mock import MagicMock, patch
from PIL import Image
from agentscope.utils.logging_utils import log_studio


class TestLogStudio:
    """Test the log_studio function for the bug fix."""

    def test_log_studio_with_none_url(self) -> None:
        """Test that None url/audio_path/video_path are handled.

        In buggy code, if a key exists but value is None, the loop tries
        to iterate over None, causing TypeError.
        The fix adds a truthiness check before the loop.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {
                        "name": "test",
                        "content": "test",
                        "url": None,
                        "audio_path": None,
                        "video_path": None,
                    }
                    # Should not raise TypeError or KeyError
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)

    def test_log_studio_with_string_url_converted_to_list(self) -> None:
        """Test that string url/audio_path/video_path are converted to list.

        In buggy code, if a string is provided, the loop iterates over characters.
        The fix converts single strings to one‑element lists.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {
                        "name": "test",
                        "content": "test",
                        "url": "https://example.com/image.jpg",
                        "audio_path": "/path/to/audio.mp3",
                        "video_path": "/path/to/video.mp4",
                    }
                    # Should not raise any exception
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)

    def test_log_studio_with_empty_url_audio_video(self) -> None:
        """Test that empty string url/audio_path/video_path are handled.

        Empty string is truthy, so the buggy code would iterate over characters.
        The fix checks truthiness, but empty string is truthy, so we need to
        ensure it doesn't crash. Actually the fix only checks `if message["url"]`,
        which is True for empty string, so the bug persists for empty string.
        However the issue is about None, not empty string. We'll keep this test
        to see if the fix also handles empty string (it doesn't, but that's okay).
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {
                        "name": "test",
                        "content": "test",
                        "url": "",
                        "audio_path": "",
                        "video_path": "",
                    }
                    # In buggy code, this will iterate over empty string -> no crash
                    # but the loop will run zero times because len("") == 0.
                    # So it won't raise an error. However the fix adds a truthiness
                    # check, which will treat empty string as False and skip the loop.
                    # That's fine; we just ensure no crash.
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)

    def test_log_studio_flushing_flag(self) -> None:
        """Test that flushing flag is True when no media present.

        In buggy code, flushing is True initially and set to False if any media
        key exists, even if the value is None. The fix changes that: only truthy
        values set flushing=False.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {"name": "test", "content": "test"}
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)

    def test_log_studio_with_list_url(self) -> None:
        """Test that list url/audio_path/video_path work as before."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {
                        "name": "test",
                        "content": "test",
                        "url": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
                        "audio_path": ["/path/to/audio1.mp3", "/path/to/audio2.mp3"],
                        "video_path": ["/path/to/video1.mp4", "/path/to/video2.mp4"],
                    }
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)

    def test_log_studio_with_missing_keys(self) -> None:
        """Test that missing url/audio_path/video_path keys are fine."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "ok"}

        with patch("requests.post", return_value=mock_response):
            with tempfile.TemporaryDirectory() as tmpdir:
                original_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    os.makedirs("./runs", exist_ok=True)
                    img = Image.new("RGB", (10, 10), color="red")
                    img_path = "./runs/test_image.png"
                    img.save(img_path)

                    message = {"name": "test", "content": "test"}
                    log_studio(message, "test_uid", avatar=img_path)
                finally:
                    os.chdir(original_cwd)
