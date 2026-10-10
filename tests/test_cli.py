import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from env_audit import cli


def write(directory, relative, text):
    path = os.path.join(directory, relative)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def run(argv):
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_clean_project_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "API_KEY=\n")
            write(tmp, "app.py", 'import os\na = os.getenv("API_KEY")\n')
            code, out, _ = run([tmp])
            self.assertEqual(code, 0)
            self.assertIn("no findings", out)

    def test_undocumented_variable_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "")
            write(tmp, "app.py", 'import os\na = os.getenv("MISSING")\n')
            code, out, _ = run([tmp])
            self.assertEqual(code, 1)
            self.assertIn("undocumented (1)", out)
            self.assertIn("MISSING", out)

    def test_unused_only_fails_under_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "STALE=\n")
            write(tmp, "app.py", "print('hello')\n")
            self.assertEqual(run([tmp])[0], 0)
            self.assertEqual(run([tmp, "--strict"])[0], 1)

    def test_exit_zero_flag_suppresses_the_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "")
            write(tmp, "app.py", 'import os\na = os.getenv("MISSING")\n')
            self.assertEqual(run([tmp, "--exit-zero"])[0], 0)

    def test_json_output_is_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "")
            write(tmp, "app.py", 'import os\na = os.getenv("MISSING")\n')
            code, out, _ = run([tmp, "--json"])
            payload = json.loads(out)
            self.assertEqual(code, 1)
            self.assertEqual(payload["undocumented"][0][0], "MISSING")

    def test_json_survives_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, ".env.example", "API_KEY=\n")
            write(tmp, "app.py", 'import os\na = os.getenv("API_KEY")\n')
            code, out, _ = run([tmp, "--json"])
            payload = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(payload["undocumented"], [])
            self.assertEqual(payload["reference"], ".env.example")

    def test_missing_directory_exits_two(self):
        code, _, err = run([os.path.join(tempfile.gettempdir(), "definitely-not-here-xyz")])
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)


if __name__ == "__main__":
    unittest.main()
