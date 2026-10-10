import os
import subprocess
from fnmatch import fnmatch

from . import envfile
from .scanner import scan_tree


# Compares the environment variables read in a tree against the reference env
# file and returns a plain dictionary the report layer can render.
def run_audit(root, ignore=(), reference=None):
    ignored = {name.strip() for name in ignore if name and name.strip()}

    uses, files_scanned = scan_tree(root)

    reference_path = None
    declared = {}
    if reference:
        candidate = reference if os.path.isabs(reference) else os.path.join(root, reference)
        if os.path.isfile(candidate):
            reference_path = os.path.relpath(candidate, root)
            declared = envfile.parse_env_file(candidate)
    else:
        found = envfile.find_reference(root)
        if found:
            reference_path = os.path.relpath(found, root)
            declared = envfile.parse_env_file(found)

    undocumented = []
    for name in sorted(uses):
        if name in ignored or name in declared:
            continue
        undocumented.append((name, sorted(uses[name])))

    unused = [name for name in declared if name not in ignored and name not in uses]

    exposed = []
    if os.path.isfile(os.path.join(root, ".env")) and not is_git_ignored(root, ".env"):
        exposed.append(".env exists here and is not covered by a gitignore rule")

    return {
        "root": root,
        "reference": reference_path,
        "declared_count": len(declared),
        "files_scanned": files_scanned,
        "variables_read": len(uses),
        "undocumented": undocumented,
        "unused": unused,
        "exposed": exposed,
    }


# Returns True when git would ignore name at root. git is asked first because
# gitignore matching is subtle, and that answer is trusted only when git exits
# with 0 (ignored) or 1 (not ignored). Any other status means root is not a
# repository, so a rough pattern check over the ignore files is used instead.
def is_git_ignored(root, name):
    completed = None
    try:
        completed = subprocess.run(
            ["git", "-C", root, "check-ignore", "-q", "--", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None:
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
    return rough_ignore_match(root, name)


# Approximates gitignore matching for trees git cannot answer for. Only simple
# whole-name patterns are honoured, because a full gitignore engine is not
# worth keeping here. Negated patterns are skipped rather than honoured, which
# can only make this report more findings, never fewer.
def rough_ignore_match(root, name):
    patterns = []
    for relative in (".gitignore", os.path.join(".git", "info", "exclude")):
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if line and not line.startswith("#") and not line.startswith("!"):
                        patterns.append(line)
        except OSError:
            continue
    for pattern in patterns:
        cleaned = pattern.lstrip("/").rstrip("/")
        if not cleaned:
            continue
        if fnmatch(name, cleaned):
            return True
    return False
