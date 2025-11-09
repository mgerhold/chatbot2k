import subprocess
import sys


def check() -> None:
    sys.exit(subprocess.run(["poe", "check"]).returncode)


def fix() -> None:
    sys.exit(subprocess.run(["poe", "fix"]).returncode)


def test() -> None:
    sys.exit(subprocess.run(["poe", "test"]).returncode)
