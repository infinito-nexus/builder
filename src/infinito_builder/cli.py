import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from . import core, load_manifest, manifest_from_compose
from .fields import coerce
from .snippet import inventory_snippet
from .web import serve

MANIFEST = "infinito-builder.yml"


def _ask(field):
    choices = field.get("choices")
    hint = f" [{'/'.join(choices)}]" if choices else ""
    default = field.get("default")
    shown = ",".join(default) if isinstance(default, list) else default
    return coerce(field, input(f"{field['help']}{hint}{f' ({shown})' if shown not in (None, '') else ''}: "))


def cmd_new(args):
    core_path = core.resolve(args.core)
    target = Path(args.target)
    if args.manifest:
        manifest = load_manifest(args.manifest)
    else:
        manifest = {f["name"]: _ask(f) for f in core.schema(core_path)}
        (target / MANIFEST).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    role = core.render(manifest, core_path, target / "ansible" / "roles", args.force)
    print(f"rendered {role}")
    print("inventory snippet (core requirement 046):")
    print(inventory_snippet(role, target))


def cmd_import(args):
    compose = yaml.safe_load(Path(args.compose).read_text(encoding="utf-8")) or {}
    manifest, unmapped = manifest_from_compose(compose)
    Path(args.output).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(f"wrote {args.output}")
    if "name" not in manifest:
        print("no service publishes a port: name, image and port stay empty", file=sys.stderr)
    for name in unmapped:
        print(f"unmapped service: {name}", file=sys.stderr)


def cmd_serve(args):
    serve(core.resolve(args.core), args.host, args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="infinito-builder")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="render a web-app-cst role from a manifest or the wizard")
    new.add_argument("--manifest", help=f"manifest file; without it the wizard asks and writes {MANIFEST}")
    new.add_argument("--core", help="local core checkout or vX.Y.Z tag (default: latest tag)")
    new.add_argument("--target", default=".", help="application repository root")
    new.add_argument("--force", action="store_true", help="replace an existing role directory")
    new.set_defaults(func=cmd_new)
    imp = sub.add_parser("import", help="write a manifest from a compose file")
    imp.add_argument("compose", help="compose file")
    imp.add_argument("--output", default=MANIFEST, help="manifest file to write")
    imp.set_defaults(func=cmd_import)
    srv = sub.add_parser("serve", help="serve the builder web form locally")
    srv.add_argument("--core", help="local core checkout or vX.Y.Z tag (default: latest tag)")
    srv.add_argument("--host", default="127.0.0.1", help="address to listen on")
    srv.add_argument("--port", type=int, default=8000, help="port to listen on")
    srv.set_defaults(func=cmd_serve)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (core.CoreError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
