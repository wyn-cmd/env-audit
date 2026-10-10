import os
import tempfile
import unittest

from env_audit import scanner


def write(directory, relative, text):
    path = os.path.join(directory, relative)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class ScanFileTest(unittest.TestCase):
    def test_finds_python_reads_in_line_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "app.py", 'import os\nA = os.getenv("TOKEN")\nB = os.environ["DB_URL"]\n')
            self.assertEqual(scanner.scan_file(path), [("TOKEN", 2), ("DB_URL", 3)])

    def test_finds_javascript_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "index.js", "const a = process.env.API_URL;\nconst b = process.env['MODE'];\n")
            self.assertEqual(scanner.scan_file(path), [("API_URL", 1), ("MODE", 2)])

    def test_shell_matches_the_braced_form_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "run.sh", "echo $BARE\ncurl ${API_URL}\necho ${TIMEOUT:-30}\n")
            self.assertEqual(scanner.scan_file(path), [("API_URL", 2), ("TIMEOUT", 3)])

    def test_unknown_extension_yields_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "notes.txt", "os.getenv('NOPE')\n")
            self.assertEqual(scanner.scan_file(path), [])

    def test_duplicate_reads_are_all_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "app.py", 'a = os.getenv("TOKEN")\nb = os.getenv("TOKEN")\n')
            self.assertEqual(scanner.scan_file(path), [("TOKEN", 1), ("TOKEN", 2)])


class ScanTreeTest(unittest.TestCase):
    def test_skips_heavy_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "node_modules/pkg/index.js", "process.env.SHOULD_NOT_APPEAR\n")
            write(tmp, ".venv/lib/thing.py", "os.getenv('ALSO_NOT')\n")
            write(tmp, "src/app.py", 'os.getenv("REAL_ONE")\n')
            uses, files_scanned = scanner.scan_tree(tmp)
            self.assertEqual(list(uses), ["REAL_ONE"])
            self.assertEqual(files_scanned, 1)

    def test_records_relative_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "src/app.py", 'x = os.getenv("TOKEN")\n')
            uses, _ = scanner.scan_tree(tmp)
            self.assertEqual(uses["TOKEN"], [(os.path.join("src", "app.py"), 1)])


if __name__ == "__main__":
    unittest.main()
