#!/usr/bin/env python3
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"Running: `{' '.join(cmd)}`")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def run_uv(args: list[str]) -> None:
    cmd = ["uv", "run", "--active"] + args
    run(cmd)


def main() -> None:
    args = sys.argv[1:]
    if len(args) > 1 or (args and args[0] != "--fix"):
        print(f"Usage: {args[0]} [--fix]", file=sys.stderr)
        print(args, file=sys.stderr)
        sys.exit(2)

    if "--fix" in args:
        run_uv(["ruff", "format"])
        run_uv(["ruff", "check", "--fix"])
        run_uv(["pyright"])
    else:
        run_uv(["ruff", "format", "--check"])
        run_uv(["ruff", "check"])
        run_uv(["pyright"])


if __name__ == "__main__":
    main()
