import os
import tempfile
import shutil
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import patch

from agentscope.skill import LocalSkillLoader
from agentscope.workspace import LocalWorkspace


class TestSkillLoaderTildeExpansion(IsolatedAsyncioTestCase):
    """Test that LocalSkillLoader expands ~ in directory paths."""

    async def asyncSetUp(self) -> None:
        # Create a temporary directory to simulate a home directory
        self.home_dir = tempfile.mkdtemp()
        self.skill_dir = os.path.join(self.home_dir, "tilde_skill")
        os.makedirs(self.skill_dir)
        with open(
            os.path.join(self.skill_dir, "SKILL.md"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                """---
name: tilde_skill
description: A skill under the user home directory
---

This skill is loaded through a tilde path.
""",
            )

    async def asyncTearDown(self) -> None:
        if os.path.exists(self.home_dir):
            shutil.rmtree(self.home_dir)

    async def test_local_skill_loader_expands_tilde(self) -> None:
        """LocalSkillLoader should expand ~ to the user home directory."""
        # Patch environment to simulate HOME and USERPROFILE
        env = {"HOME": self.home_dir, "USERPROFILE": self.home_dir}
        drive, tail = os.path.splitdrive(self.home_dir)
        if drive:
            env["HOMEDRIVE"] = drive
            env["HOMEPATH"] = tail

        with patch.dict(os.environ, env, clear=False):
            loader = LocalSkillLoader(os.path.join("~", "tilde_skill"), scan_subdir=False)
            # The directory attribute should be the expanded absolute path
            self.assertEqual(loader.directory, os.path.abspath(self.skill_dir))
            skills = await loader.list_skills()

        self.assertEqual(len(skills), 1)
        skill = skills[0]
        self.assertEqual(skill.name, "tilde_skill")
        self.assertEqual(skill.description, "A skill under the user home directory")
        self.assertEqual(skill.dir, os.path.abspath(self.skill_dir))


class TestLocalWorkspaceTildeExpansion(IsolatedAsyncioTestCase):
    """Test that LocalWorkspace expands ~ in skill_paths and add_skill."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home_dir = tempfile.mkdtemp()
        self.skill_dir = os.path.join(self.home_dir, "tilde_skill")
        os.makedirs(self.skill_dir)
        with open(
            os.path.join(self.skill_dir, "SKILL.md"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                """---
name: tilde_skill
description: A skill under the user home directory
---

This skill is seeded through a tilde path.
""",
            )

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()
        if os.path.exists(self.home_dir):
            shutil.rmtree(self.home_dir)

    async def test_skill_paths_expands_tilde_on_init(self) -> None:
        """LocalWorkspace should expand ~ in skill_paths on initialization."""
        env = {"HOME": self.home_dir, "USERPROFILE": self.home_dir}
        drive, tail = os.path.splitdrive(self.home_dir)
        if drive:
            env["HOMEDRIVE"] = drive
            env["HOMEPATH"] = tail

        with patch.dict(os.environ, env, clear=False):
            workspace = LocalWorkspace(
                workdir=self.temp_dir.name,
                skill_paths=[os.path.join("~", "tilde_skill")],
            )
            # skill_paths should be normalized to absolute paths
            self.assertEqual(workspace.skill_paths, [os.path.abspath(self.skill_dir)])
            await workspace.initialize()

        skill_target = os.path.join(self.temp_dir.name, "skills", "tilde_skill")
        self.assertTrue(os.path.exists(os.path.join(skill_target, "SKILL.md")))

    async def test_add_skill_expands_tilde(self) -> None:
        """LocalWorkspace.add_skill should expand ~ in skill_path parameter."""
        env = {"HOME": self.home_dir, "USERPROFILE": self.home_dir}
        drive, tail = os.path.splitdrive(self.home_dir)
        if drive:
            env["HOMEDRIVE"] = drive
            env["HOMEPATH"] = tail

        workspace = LocalWorkspace(workdir=self.temp_dir.name)
        await workspace.initialize()
        with patch.dict(os.environ, env, clear=False):
            await workspace.add_skill(os.path.join("~", "tilde_skill"))

        skill_target = os.path.join(self.temp_dir.name, "skills", "tilde_skill")
        self.assertTrue(os.path.exists(os.path.join(skill_target, "SKILL.md")))
