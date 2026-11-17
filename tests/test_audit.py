import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from env_audit.audit import is_git_ignored, run_audit, rough_ignore_match


# Isolates git calls from machine-wide configuration so global excludes do not affect tests.
CLEAN_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def write(directory, relative, text):
    path = os.path.join(directory, relative)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


# Creates a repository at root or skips the test if git is not installed or fails to init.
def make_repository(case, root):
    git_bin = shutil.which("git")
    if not git_bin:
        case.skipTest("git is not installed")
        return

    res = subprocess.run(
        [git_bin, "init", "--quiet", root],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, **CLEAN_GIT_ENV},
    )
    if res.returncode != 0:
        case.skipTest("git init failed in this environment")


class RunAuditTest(unittest.TestCase):
    def test_flags_undocumented_and_unused(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "API_KEY=abc\nOLD_TOKEN=gone\n")
            write(tmp, "app.py", 'import os\na = os.getenv("API_KEY")\nb = os.getenv("NEW_URL")\n')
            result = run_audit(tmp)
            
            undocumented = [entry[0] for entry in result["undocumented"]]
            self.assertEqual(undocumented, ["NEW_URL"])
            self.assertEqual(result["unused"], ["OLD_TOKEN"])
            self.assertEqual(result["reference"], ".env.example")
            self.assertEqual(result["declared_count"], 2)
            self.assertEqual(result["variables_read"], 2)

    def test_undocumented_entry_carries_its_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "")
            write(tmp, os.path.join("src", "app.py"), 'x = os.getenv("MISSING")\n')
            result = run_audit(tmp)
            self.assertEqual(
                result["undocumented"],
                [("MISSING", [(os.path.join("src", "app.py"), 1)])],
            )

    def test_ignore_removes_a_name_from_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "NODE_ENV=development\n")
            write(tmp, "app.py", 'import os\na = os.getenv("NODE_ENV")\n')
            
            plain = run_audit(tmp)
            self.assertEqual(plain["undocumented"], [])
            self.assertEqual(plain["unused"], [])
            
            ignored = run_audit(tmp, ignore=["NODE_ENV"])
            self.assertEqual(ignored["undocumented"], [])
            self.assertEqual(ignored["unused"], [])

    def test_no_reference_file_means_everything_is_undocumented(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "app.py", 'import os\na = os.getenv("ONLY_ONE")\n')
            result = run_audit(tmp)
            self.assertIsNone(result["reference"])
            self.assertEqual([e[0] for e in result["undocumented"]], ["ONLY_ONE"])

    def test_explicit_reference_path_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "custom.env", "TOKEN=\n")
            write(tmp, "app.py", 'import os\na = os.getenv("TOKEN")\n')
            result = run_audit(tmp, reference="custom.env")
            self.assertEqual(result["reference"], "custom.env")
            self.assertEqual(result["undocumented"], [])

    def test_missing_explicit_reference_does_not_fall_back_to_the_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "TOKEN=\n")
            write(tmp, "app.py", 'import os\na = os.getenv("TOKEN")\n')
            result = run_audit(tmp, reference="not-here.env")
            self.assertIsNone(result["reference"])
            self.assertEqual(result["declared_count"], 0)
            self.assertEqual([e[0] for e in result["undocumented"]], ["TOKEN"])

    def test_exposed_env_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env", "SECRET=1\n")
            write(tmp, ".env.example", "SECRET=\n")
            result = run_audit(tmp)
            self.assertEqual(len(result["exposed"]), 1)

    def test_gitignored_env_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env", "SECRET=1\n")
            write(tmp, ".env.example", "SECRET=\n")
            write(tmp, ".gitignore", ".env\n")
            result = run_audit(tmp)
            self.assertEqual(result["exposed"], [])


class IgnoreMatchTest(unittest.TestCase):
    def test_rough_match_finds_plain_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".gitignore", "*.log\n.env\n")
            self.assertTrue(rough_ignore_match(tmp, ".env"))
            self.assertFalse(rough_ignore_match(tmp, ".env.local"))

    def test_rough_match_honours_a_glob(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".gitignore", ".env*\n")
            self.assertTrue(rough_ignore_match(tmp, ".env.local"))

    def test_rough_match_without_ignore_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(rough_ignore_match(tmp, ".env"))

    def test_git_ignored_outside_a_repository_uses_the_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".gitignore", ".env\n")
            self.assertTrue(is_git_ignored(tmp, ".env"))

    def test_git_ignored_returns_false_without_any_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(is_git_ignored(tmp, ".env"))


# Covers cases where git is used to determine ignore status.
class GitRepositoryIgnoreTest(unittest.TestCase):
    def setUp(self):
        # Prevent machine-wide git config from affecting the results of the audit module.
        patcher = mock.patch.dict(os.environ, CLEAN_GIT_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_repository_reports_a_matching_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repository(self, tmp)
            write(tmp, ".gitignore", ".env\n")
            self.assertTrue(is_git_ignored(tmp, ".env"))

    def test_repository_answer_wins_over_the_rough_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repository(self, tmp)
            # A trailing slash tells git to ignore directories only, so the file remains non-ignored.
            write(tmp, ".gitignore", "/.env/\n")
            self.assertTrue(rough_ignore_match(tmp, ".env"))
            self.assertFalse(is_git_ignored(tmp, ".env"))


if __name__ == "__main__":
    unittest.main()