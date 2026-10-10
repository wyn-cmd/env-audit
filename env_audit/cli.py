import argparse
import os
import sys

from . import __version__
from .audit import run_audit
from .report import render_json, render_text


def build_parser():
    parser = argparse.ArgumentParser(
        prog="env-audit",
        description="Report environment variables that source code reads but the reference env file never declares.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory to audit, defaults to the current directory",
    )
    parser.add_argument(
        "--reference",
        metavar="FILE",
        help="env file to treat as the contract instead of the first .env.example found",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="NAME",
        help="variable to skip on both sides, repeat the flag for more than one",
    )
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail when the reference file declares a variable nothing reads",
    )
    parser.add_argument("--exit-zero", action="store_true", help="always exit 0")
    parser.add_argument("--version", action="version", version="env-audit " + __version__)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        sys.stderr.write("env-audit: not a directory: %s\n" % args.path)
        return 2

    result = run_audit(root, ignore=args.ignore, reference=args.reference)

    if args.json:
        sys.stdout.write(render_json(result) + "\n")
    else:
        sys.stdout.write(render_text(result) + "\n")

    if args.exit_zero:
        return 0
    if result["undocumented"] or result["exposed"]:
        return 1
    if args.strict and result["unused"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
