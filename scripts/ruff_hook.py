#!/usr/bin/env python3
import subprocess
import sys


def run(*cmd):
    return subprocess.run(cmd, check=False)


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    run("ruff", "format", *files)
    run("ruff", "check", "--fix", "--exit-zero", *files)
    subprocess.run(["git", "add", "--"] + files, check=True)
    result = run("ruff", "check", *files)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
