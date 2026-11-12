# Infinito.Nexus Builder 🧱

Make your app Infinito.Nexus compatible: turn an existing web application into a `web-app-cst-<name>` role that the Infinito.Nexus framework deploys, from a few answers or from your `compose.yml`.

Scope and decisions: [001 - Builder](docs/requirements/001-builder.md).

## How it works

Core owns the role format. The builder fills a manifest, `infinito-builder.yml`, and renders it with the role skeleton of the core version you choose, so the generated role always matches the core that deploys it.

## Install

```sh
pip install infinito-builder
```

## Usage

```sh
infinito-builder import compose.yml
infinito-builder new --manifest infinito-builder.yml
infinito-builder new
```

`import` maps the compose file onto a manifest and lists the services it could not map. `new` renders `ansible/roles/web-app-cst-<name>/` into the current repository and prints the inventory snippet that tells Infinito.Nexus where to pull the role from. Without `--manifest`, `new` asks for every field.

`infinito-builder serve` runs the web form of builder.infinito.nexus on <http://127.0.0.1:8000/>: the same fields, answered with a zip of the role, its manifest and the inventory snippet. It accepts no uploads.

`--core v17.0.0` renders with that core release, `--core <path>` with a local core checkout; without it the latest release is used and cached under `~/.cache/infinito-builder/core/`.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

## License

[Infinito.Nexus Community License (Non-Commercial)](LICENSE.md).

## Author

Kevin Veen-Birkenbach <kevin@veen.world>
