#!/usr/bin/env python3
import subprocess
import sys


def run(*cmd):
    return subprocess.run(cmd, check=False)


def ruff_modified(files):
    """Files that differ between working tree and index after ruff ran."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--"] + files,
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.splitlines() if f in files]


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    run("ruff", "format", *files)
    run("ruff", "check", "--fix", "--exit-zero", *files)

    # Stage only the files ruff actually changed — include fixes in this commit
    changed = ruff_modified(files)
    if changed:
        subprocess.run(["git", "add", "--"] + changed, check=True)

    # Fail only if unfixable lint errors remain
    result = run("ruff", "check", *files)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
