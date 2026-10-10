import json


# Renders an audit result as the text a person reads in a terminal.
def render_text(result):
    lines = [
        "env-audit: %d source file(s) scanned, %d variable(s) read"
        % (result["files_scanned"], result["variables_read"])
    ]
    if result["reference"]:
        lines.append("reference: %s (%d declared)" % (result["reference"], result["declared_count"]))
    else:
        lines.append("reference: none found, so every variable read counts as undocumented")

    lines.extend(_section("undocumented", _locations(result["undocumented"])))
    lines.extend(_section("unused", list(result["unused"])))
    lines.extend(_section("exposed", list(result["exposed"])))

    if not (result["undocumented"] or result["unused"] or result["exposed"]):
        lines.append("")
        lines.append("no findings")
    return "\n".join(lines)


# Renders an audit result as JSON. Tuples become arrays, which is what a CI
# step reads.
def render_json(result):
    return json.dumps(result, indent=2, sort_keys=True)


# Turns (name, [(path, line), ...]) entries into (name, "path:line, ...") rows
# and cuts the list short so one hot variable cannot dominate the output.
def _locations(entries):
    rows = []
    for name, locations in entries:
        shown = ", ".join("%s:%d" % (path, line) for path, line in locations[:4])
        if len(locations) > 4:
            shown += ", and %d more" % (len(locations) - 4)
        rows.append((name, shown))
    return rows


# Builds one titled block, or nothing at all when the block is empty.
def _section(title, rows):
    if not rows:
        return []
    out = ["", "%s (%d)" % (title, len(rows))]
    for row in rows:
        if isinstance(row, tuple):
            out.append("  %-20s %s" % row)
        else:
            out.append("  %s" % row)
    return out
