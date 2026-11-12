import subprocess
from pathlib import Path

import yaml


def _git(target, *args):
    proc = subprocess.run(["git", *args], cwd=target, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def inventory_snippet(role, target):
    """Return the 046 inventory snippet that declares a rendered role.

    Args:
        role: the rendered role directory.
        target: the application repository root the role lives in.
    """
    rel = Path(role).resolve().relative_to(Path(target).resolve()).as_posix()
    source = {
        "url": _git(target, "config", "--get", "remote.origin.url") or "<git url of this repository>",
        "version": _git(target, "describe", "--tags", "--exact-match") or "<tag or full commit sha>",
        "path": rel,
    }
    return yaml.safe_dump(
        {"applications": {Path(role).name: {"custom": True, "source": source}}}, sort_keys=False
    )
