from pathlib import Path

import yaml

from . import core as _core
from .compose import manifest_from_compose

__all__ = ["load_manifest", "manifest_from_compose", "render"]


def load_manifest(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def render(manifest, core=None, target=".", force=False):
    """Render a manifest into <target>/ansible/roles/web-app-cst-<name>.

    Args:
        manifest: the builder manifest as a dict.
        core: a local core checkout, a vX.Y.Z tag, or None for the latest tag.
        target: the application repository root.
        force: replace an existing role directory.

    Returns:
        The path of the rendered role directory.
    """
    roles = Path(target) / "ansible" / "roles"
    return _core.render(manifest, _core.resolve(core), roles, force)
