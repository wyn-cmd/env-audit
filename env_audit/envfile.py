import os

# Reference env files are looked up in this order. The first one that exists is
# treated as the contract the source code has to satisfy. A plain .env is last
# because a project without an example file should still get a useful answer.
REFERENCE_NAMES = (
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    ".env",
)


# Returns the path of the first reference env file in root, or None.
def find_reference(root):
    for name in REFERENCE_NAMES:
        candidate = os.path.join(root, name)
        if os.path.isfile(candidate):
            return candidate
    return None


# Returns True when name is shaped like a shell variable and can be used as an
# environment variable name.
def is_variable_name(name):
    if not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    return all(character.isalnum() or character == "_" for character in name)


# Parses a .env style file into an ordered mapping of name to raw value.
# Comments, blank lines and the export prefix are stripped. A value keeps its
# quotes exactly as written, since this tool compares names and never values.
def parse_env_file(path):
    entries = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return entries
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if not is_variable_name(name):
            continue
        entries[name] = value.strip()
    return entries
