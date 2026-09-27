import logging
from unittest.mock import MagicMock

import pytest

from strands.vended_plugins.skills.agent_skills import AgentSkills
from strands.vended_plugins.skills.skill import Skill


def _make_skill_dir(parent, name, description="A test skill"):
    skill_dir = parent / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n# Instructions for {name}\n"
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


class TestResolveUrlSkills:
    """Tests for _resolve_skills with URL sources."""

    _SKILL_MODULE = "strands.vended_plugins.skills.skill"
    _SAMPLE_CONTENT = "---\nname: url-skill\ndescription: A URL skill\n---\n# Instructions\n"

    def _mock_urlopen(self, content):
        """Create a mock urlopen context manager returning the given content."""
        mock_response = MagicMock()
        mock_response.read.return_value = content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    def test_resolve_url_source(self):
        """Test resolving a URL string as a skill source."""
        from unittest.mock import patch

        with patch(
            f"{self._SKILL_MODULE}.urllib.request.urlopen", return_value=self._mock_urlopen(self._SAMPLE_CONTENT)
        ):
            plugin = AgentSkills(skills=["https://example.com/SKILL.md"])

        assert len(plugin.get_available_skills()) == 1
        assert plugin.get_available_skills()[0].name == "url-skill"

    def test_resolve_mixed_url_and_local(self, tmp_path):
        """Test resolving a mix of URL and local filesystem sources."""
        from unittest.mock import patch

        _make_skill_dir(tmp_path, "local-skill")

        with patch(
            f"{self._SKILL_MODULE}.urllib.request.urlopen", return_value=self._mock_urlopen(self._SAMPLE_CONTENT)
        ):
            plugin = AgentSkills(
                skills=[
                    "https://example.com/SKILL.md",
                    str(tmp_path / "local-skill"),
                ]
            )

        assert len(plugin.get_available_skills()) == 2
        names = {s.name for s in plugin.get_available_skills()}
        assert names == {"url-skill", "local-skill"}

    def test_resolve_url_failure_skips_gracefully(self, caplog):
        """Test that a failed URL fetch is skipped with a warning."""
        import urllib.error
        from unittest.mock import patch

        with (
            patch(
                f"{self._SKILL_MODULE}.urllib.request.urlopen",
                side_effect=urllib.error.HTTPError(
                    url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
                ),
            ),
            caplog.at_level(logging.WARNING),
        ):
            plugin = AgentSkills(skills=["https://example.com/broken/SKILL.md"])

        assert len(plugin.get_available_skills()) == 0
        assert "failed to load skill from URL" in caplog.text

    def test_resolve_duplicate_url_skills_warns(self, caplog):
        """Test that duplicate skill names from URLs log a warning."""
        from unittest.mock import patch

        with (
            patch(
                f"{self._SKILL_MODULE}.urllib.request.urlopen",
                return_value=self._mock_urlopen(self._SAMPLE_CONTENT),
            ),
            caplog.at_level(logging.WARNING),
        ):
            plugin = AgentSkills(
                skills=[
                    "https://example.com/a/SKILL.md",
                    "https://example.com/b/SKILL.md",
                ]
            )

        assert len(plugin.get_available_skills()) == 1
        assert "duplicate skill name" in caplog.text


class TestSkillFromUrl:
    """Tests for Skill.from_url."""

    _SKILL_MODULE = "strands.vended_plugins.skills.skill"
    _SAMPLE_CONTENT = "---\nname: my-skill\ndescription: A remote skill\n---\nRemote instructions.\n"

    def _mock_urlopen(self, content):
        """Create a mock urlopen context manager returning the given content."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.read.return_value = content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    def test_from_url_returns_skill(self):
        """Test loading a skill from a URL returns a single Skill."""
        from unittest.mock import patch

        mock_response = self._mock_urlopen(self._SAMPLE_CONTENT)
        with patch(f"{self._SKILL_MODULE}.urllib.request.urlopen", return_value=mock_response):
            skill = Skill.from_url("https://raw.githubusercontent.com/org/repo/main/SKILL.md")

        assert isinstance(skill, Skill)
        assert skill.name == "my-skill"
        assert skill.description == "A remote skill"
        assert "Remote instructions." in skill.instructions
        assert skill.path is None

    def test_from_url_invalid_url_raises(self):
        """Test that a non-HTTPS URL raises ValueError."""
        with pytest.raises(ValueError, match="not a valid HTTPS URL"):
            Skill.from_url("./local-path")

    def test_from_url_http_rejected(self):
        """Test that http:// URLs are rejected."""
        with pytest.raises(ValueError, match="not a valid HTTPS URL"):
            Skill.from_url("http://example.com/SKILL.md")

    def test_from_url_http_error_raises(self):
        """Test that HTTP errors propagate as RuntimeError."""
        import urllib.error
        from unittest.mock import patch

        with patch(
            f"{self._SKILL_MODULE}.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
            ),
        ):
            with pytest.raises(RuntimeError, match="HTTP 404"):
                Skill.from_url("https://example.com/SKILL.md")

    def test_from_url_network_error_raises(self):
        """Test that network errors propagate as RuntimeError."""
        import urllib.error
        from unittest.mock import patch

        with patch(
            f"{self._SKILL_MODULE}.urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            with pytest.raises(RuntimeError, match="failed to fetch"):
                Skill.from_url("https://example.com/SKILL.md")

    def test_from_url_strict_mode(self):
        """Test that strict mode is forwarded to from_content."""
        from unittest.mock import patch

        bad_content = "---\nname: BAD_NAME\ndescription: Bad\n---\nBody."

        with patch(f"{self._SKILL_MODULE}.urllib.request.urlopen", return_value=self._mock_urlopen(bad_content)):
            with pytest.raises(ValueError):
                Skill.from_url("https://example.com/SKILL.md", strict=True)

    def test_from_url_invalid_content_raises(self):
        """Test that non-SKILL.md content (e.g. HTML page) raises ValueError."""
        from unittest.mock import patch

        html_content = "<html><body>Not a SKILL.md</body></html>"

        with patch(f"{self._SKILL_MODULE}.urllib.request.urlopen", return_value=self._mock_urlopen(html_content)):
            with pytest.raises(ValueError, match="frontmatter"):
                Skill.from_url("https://example.com/SKILL.md")
