# env-audit

Every project grows a `.env.example` that nobody updates. The code reads `STRIPE_WEBHOOK_SECRET`, the example file still lists `STRIPE_KEY`, a new engineer copies the example, starts the service and watches it die at import time. env-audit reads both sides and reports which environment variables the source code reads but the reference file never declares, and which variables the reference file declares that nothing reads any more.

It works by static text matching rather than by running your code. That means it is fast, it never needs your real secrets, and it only sees reads that are written literally in the source. A name assembled at runtime, such as `os.getenv(prefix + "_TOKEN")`, will not be found. That limit is the honest shape of the tool, so it is stated in the output instead of being hidden.

## What it checks

- Variables read in source code that are missing from the reference env file, reported as `undocumented`.
- Variables present in the reference env file that no source file reads, reported as `unused`.
- A real `.env` file sitting at the repository root without a gitignore rule covering it, reported as `exposed`, because that is the file most likely to be committed by accident.

## Install

    pip install .

Or run it straight from a checkout with `python3 -m env_audit.cli`.

## Usage

    env-audit                     # audit the current directory
    env-audit path/to/project     # audit another tree
    env-audit --json              # machine readable output
    env-audit --ignore NODE_ENV   # skip a name on both sides, repeatable
    env-audit --strict            # treat unused declarations as failures too
    env-audit --exit-zero         # always exit 0, for a report-only job

Exit codes are `0` when nothing needs attention, `1` when there are findings, and `2` on a usage error.

## Output

    env-audit: 14 source file(s) scanned, 9 variable(s) read
    reference: .env.example (8 declared)

    undocumented (2)
      DATABASE_URL         app/db.py:11, app/db.py:52
      SENTRY_DSN           app/main.py:7

    unused (1)
      OLD_API_TOKEN

`--json` prints the same result as a single object with `undocumented`, `unused` and `exposed` arrays, which is what a CI step wants to read.

## Reading the result

`undocumented` is the finding that breaks deploys. A variable the code needs and the example omits means anyone starting from the example gets a crash or a silent default.

`unused` is usually stale documentation, but only `--strict` fails the run for it, because a reference file sometimes lists options that the code sets conditionally.

`exposed` means a `.env` exists at the root and git would not ignore it. The check asks `git check-ignore` when the directory is a repository and falls back to a simple look at `.gitignore` and `.git/info/exclude` when it is not.

## Languages

Python, JavaScript and TypeScript including `import.meta.env`, shell in the `${VAR}` form only, Ruby, Go and Java are recognised by file extension. Adding another language means adding one entry to `PATTERNS_BY_SUFFIX` in `env_audit/patterns.py`. Bare shell `$VAR` is deliberately skipped, because it is indistinguishable from any other dollar expansion and would flood the report.

## Tests

    python3 -m unittest discover -s tests -t .

The tests build throwaway project trees inside a temporary directory, so they never touch the repository you run them from.

## License

MIT.
