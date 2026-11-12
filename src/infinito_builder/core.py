import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CORE_URL = "https://github.com/infinito-nexus/core"
SPARSE_FILE = "cli/contributing/role/skeleton/sparse.txt"
MODULE = "cli.contributing.role.skeleton"
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


class CoreError(RuntimeError):
    pass


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "infinito-builder" / "core"


def latest_tag():
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", CORE_URL],
        check=True, capture_output=True, text=True,
    ).stdout
    tags = [line.rsplit("/", 1)[-1] for line in out.splitlines()]
    versions = [(tuple(map(int, m.groups())), t) for t in tags if (m := TAG.match(t))]
    if not versions:
        raise CoreError(f"no vX.Y.Z tag found at {CORE_URL}")
    return max(versions)[1]


def fetch(tag):
    target = cache_dir() / tag
    if target.is_dir():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{tag}.", dir=target.parent))
    try:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", tag,
             "--filter=blob:none", "--sparse", CORE_URL, str(staging)],
            check=True,
        )
        sparse = ["git", "sparse-checkout", "set", "--no-cone"]
        subprocess.run([*sparse, f"/{SPARSE_FILE}"], cwd=staging, check=True)
        sparse_file = staging / SPARSE_FILE
        if not sparse_file.is_file():
            raise CoreError(f"core {tag} has no role skeleton; pass --core with a newer tag or a checkout")
        patterns = sparse_file.read_text(encoding="utf-8").split()
        subprocess.run([*sparse, *patterns], cwd=staging, check=True)
        try:
            staging.rename(target)
        except OSError:
            if not target.is_dir():
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def resolve(core=None):
    """Return a core directory that holds the skeleton renderer.

    Args:
        core: a local core checkout, a vX.Y.Z tag, or None for the latest tag.
    """
    if core and Path(core).is_dir():
        return Path(core).resolve()
    return fetch(core or latest_tag())


def _run(core_path, *args, stdin=None):
    proc = subprocess.run(
        [sys.executable, "-m", MODULE, *args],
        cwd=core_path, input=stdin, capture_output=True, text=True,
    )
    if proc.returncode:
        raise CoreError(proc.stderr.strip() or f"{MODULE} exited {proc.returncode}")
    return proc.stdout


def schema(core_path):
    return json.loads(_run(core_path, "schema"))


def render(manifest, core_path, roles_dir, force=False):
    args = ["render", "--target", str(roles_dir)] + (["--force"] if force else [])
    return Path(_run(core_path, *args, stdin=json.dumps(manifest)).strip())
