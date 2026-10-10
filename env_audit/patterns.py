import re

# Regexes that pull the name of an environment variable out of source code.
# Every pattern must expose the variable name as capture group 1, because the
# scanner reads group 1 and nothing else.
# Adding a language means adding one entry to PATTERNS_BY_SUFFIX below.

_PYTHON = [
    re.compile(r"os\.environ\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"),
    re.compile(r"os\.environ\.get\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
    re.compile(r"os\.environ\.setdefault\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
]

_JS = [
    re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"process\.env\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"),
    re.compile(r"import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
]

# Shell matches the braced form only. A bare $VAR is indistinguishable from
# every other dollar expansion and would bury the real findings in noise.
_SHELL = [
    re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::[-=?+][^}]*)?\}"),
]

_RUBY = [
    re.compile(r"ENV\[\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"),
    re.compile(r"ENV\.fetch\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
]

_GO = [
    re.compile(r"os\.Getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
    re.compile(r"os\.LookupEnv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
]

_JAVA = [
    re.compile(r"System\.getenv\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
]

# Maps a lowercased file extension to the patterns used for that language.
PATTERNS_BY_SUFFIX = {
    ".py": _PYTHON,
    ".pyi": _PYTHON,
    ".js": _JS,
    ".jsx": _JS,
    ".mjs": _JS,
    ".cjs": _JS,
    ".ts": _JS,
    ".tsx": _JS,
    ".vue": _JS,
    ".svelte": _JS,
    ".sh": _SHELL,
    ".bash": _SHELL,
    ".zsh": _SHELL,
    ".ksh": _SHELL,
    ".rb": _RUBY,
    ".go": _GO,
    ".java": _JAVA,
    ".kt": _JAVA,
    ".kts": _JAVA,
}
