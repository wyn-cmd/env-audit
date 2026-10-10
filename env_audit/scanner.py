import os

from .patterns import PATTERNS_BY_SUFFIX

# Directories that never hold hand written source worth scanning. The match is
# on the directory name alone, at any depth.
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "target",
    "vendor",
    ".next",
    ".nuxt",
    ".cache",
    "coverage",
    "htmlcov",
    ".idea",
    ".vscode",
}

# Anything larger than this is skipped. A minified bundle or a vendored blob
# will not hold a useful declaration and would only slow the walk down.
MAX_FILE_BYTES = 2 * 1024 * 1024


# Walks root and yields every file whose extension has known patterns.
def iter_source_files(root):
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            suffix = os.path.splitext(filename)[1].lower()
            if suffix in PATTERNS_BY_SUFFIX:
                yield os.path.join(current, filename)


# Returns the environment variables read in one file as (name, line) pairs,
# ordered by line number. Unreadable or oversized files yield nothing.
def scan_file(path):
    suffix = os.path.splitext(path)[1].lower()
    patterns = PATTERNS_BY_SUFFIX.get(suffix)
    if not patterns:
        return []
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return []
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return []
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            for match in pattern.finditer(line):
                found.append((match.group(1), number))
    found.sort(key=lambda item: item[1])
    return found


# Walks root and returns (uses, files_scanned) where uses maps a variable name
# to a sorted list of (relative_path, line) locations.
def scan_tree(root):
    uses = {}
    files_scanned = 0
    for path in iter_source_files(root):
        files_scanned += 1
        found = scan_file(path)
        if not found:
            continue
        relative = os.path.relpath(path, root)
        for name, line in found:
            uses.setdefault(name, []).append((relative, line))
    return uses, files_scanned
