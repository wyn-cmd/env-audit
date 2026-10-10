import os
import tempfile
import unittest

from env_audit import envfile


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class ParseEnvFileTest(unittest.TestCase):
    def test_parses_plain_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(os.path.join(tmp, ".env.example"), "API_KEY=abc\nDB_URL=postgres://x\n")
            self.assertEqual(
                envfile.parse_env_file(path),
                {"API_KEY": "abc", "DB_URL": "postgres://x"},
            )

    def test_skips_comments_blanks_and_bad_names(self):
        text = "# a comment\n\n   \nexport TOKEN=one\nNOT_A_LINE\n1BAD=nope\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = write(os.path.join(tmp, ".env.example"), text)
            self.assertEqual(envfile.parse_env_file(path), {"TOKEN": "one"})

    def test_keeps_equals_signs_inside_a_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(os.path.join(tmp, ".env.example"), "CONN=a=b=c\n")
            self.assertEqual(envfile.parse_env_file(path), {"CONN": "a=b=c"})

    def test_missing_file_returns_nothing(self):
        self.assertEqual(envfile.parse_env_file("/no/such/.env.example"), {})


class FindReferenceTest(unittest.TestCase):
    def test_prefers_the_example_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(os.path.join(tmp, ".env"), "A=1\n")
            write(os.path.join(tmp, ".env.example"), "A=\n")
            self.assertEqual(envfile.find_reference(tmp), os.path.join(tmp, ".env.example"))

    def test_falls_back_to_a_plain_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(os.path.join(tmp, ".env"), "A=1\n")
            self.assertEqual(envfile.find_reference(tmp), os.path.join(tmp, ".env"))

    def test_returns_none_when_nothing_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(envfile.find_reference(tmp))


class VariableNameTest(unittest.TestCase):
    def test_accepts_shell_names(self):
        self.assertTrue(envfile.is_variable_name("_PRIVATE"))
        self.assertTrue(envfile.is_variable_name("A1"))
        self.assertTrue(envfile.is_variable_name("SENTRY_DSN"))

    def test_rejects_other_shapes(self):
        self.assertFalse(envfile.is_variable_name(""))
        self.assertFalse(envfile.is_variable_name("1A"))
        self.assertFalse(envfile.is_variable_name("A-B"))


if __name__ == "__main__":
    unittest.main()
