import html
import io
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

import yaml

from . import core
from .fields import coerce
from .snippet import inventory_snippet

BRAND = "/_infinito/cdn/roles/web-app-cst-brand/latest/v1/"
MAX_BODY = 64 * 1024
FORM_TYPE = "application/x-www-form-urlencoded"


def manifest_from_form(schema, form):
    """Build a manifest from a submitted form.

    Args:
        schema: the core skeleton schema.
        form: the parsed form, as parse_qs returns it.
    """
    manifest = {}
    for field in schema:
        values = form.get(field["name"], [])
        if field.get("multiple") and not field.get("choices"):
            values = [line for value in values for line in value.splitlines()]
        raw = values if field.get("multiple") else (values[0] if values else "")
        value = coerce(field, raw)
        if value is not None:
            manifest[field["name"]] = value
    return manifest


def _control(field, value):
    name = html.escape(field["name"])
    choices = field.get("choices")
    if choices and field.get("multiple"):
        boxes = "".join(
            f'<label><input type="checkbox" name="{name}" value="{html.escape(c)}"'
            f'{" checked" if c in (value or []) else ""}> {html.escape(c)}</label> '
            for c in choices
        )
        return f"<fieldset><legend>{html.escape(field['help'])}</legend>{boxes}</fieldset>"
    label = f'<label for="{name}">{html.escape(field["help"])}</label><br>'
    if choices:
        options = "" if field.get("default") else '<option value=""></option>'
        options += "".join(
            f'<option{" selected" if c == value else ""}>{html.escape(c)}</option>' for c in choices
        )
        return f'{label}<select id="{name}" name="{name}">{options}</select>'
    if field.get("multiple"):
        text = "\n".join(value or [])
        return f'{label}<textarea id="{name}" name="{name}" rows="3">{html.escape(text)}</textarea>'
    kind = "number" if field.get("type") == "integer" else "text"
    shown = "" if value is None else html.escape(str(value))
    return f'{label}<input id="{name}" type="{kind}" name="{name}" value="{shown}">'


def page(schema, values=None, errors=()):
    """Render the builder page: the form, and the errors of a failed render.

    Args:
        schema: the core skeleton schema.
        values: the values to prefill, by field name; defaults otherwise.
        errors: the error lines to show above the form.
    """
    values = values or {}
    controls = "".join(
        f"<p>{_control(f, values.get(f['name'], f.get('default')))}</p>" for f in schema
    )
    problems = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
    alert = f'<ul role="alert">{problems}</ul>' if problems else ""
    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Infinito.Nexus Builder</title>
<link rel="stylesheet" href="{BRAND}tokens.css">
<link rel="stylesheet" href="{BRAND}brand.css">
</head>
<body>
<header class="brand-header">
<svg class="brand-motif" data-motif="builder" viewBox="0 0 32 32" aria-hidden="true"><use href="{BRAND}motifs.svg#motif-builder"></use><use class="brand-motif-motion" href="{BRAND}motifs.svg#motif-builder-motion"></use></svg>
<strong class="brand-logo">Infinito.Nexus Builder</strong>
<svg class="brand-avatar" aria-hidden="true"><use href="{BRAND}beaver.svg#beaver"></use></svg>
</header>
<main>
<h1>Make your app Infinito.Nexus compatible</h1>
<p>Describe your application. You get a <code>web-app-cst</code> role for your repository, its manifest and the inventory snippet that tells Infinito.Nexus where to pull it from.</p>
{alert}
<form method="post" action="/render">
{controls}
<p><button type="submit">Build role</button></p>
</form>
</main>
<footer class="brand-footer"><p>Infinito.Nexus Builder</p></footer>
</body>
</html>
"""


def _zip(manifest, core_path, render):
    with tempfile.TemporaryDirectory(prefix="infinito-builder-") as tmp:
        role = render(manifest, core_path, Path(tmp) / "ansible" / "roles", False)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(role.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(tmp).as_posix())
            archive.writestr("infinito-builder.yml", yaml.safe_dump(manifest, sort_keys=False))
            archive.writestr("inventory-snippet.yml", inventory_snippet(role, tmp))
        return role.name, buffer.getvalue()


def make_app(core_path, schema=None, render=core.render):
    """Return the WSGI application of builder.infinito.nexus.

    Args:
        core_path: the core checkout whose skeleton renders the roles.
        schema: the core skeleton schema; read from core_path when omitted.
        render: the function that renders a manifest into a roles directory.
    """
    schema = schema if schema is not None else core.schema(core_path)

    def app(environ, start_response):
        method, path = environ.get("REQUEST_METHOD"), environ.get("PATH_INFO", "/")

        def reply(status, body, content_type="text/html; charset=utf-8", extra=()):
            data = body.encode("utf-8") if isinstance(body, str) else body
            start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(data))), *extra])
            return [data]

        if path == "/" and method == "GET":
            return reply("200 OK", page(schema))
        if path != "/render" or method != "POST":
            return reply("404 Not Found", "not found", "text/plain; charset=utf-8")
        if not environ.get("CONTENT_TYPE", "").startswith(FORM_TYPE):
            return reply("415 Unsupported Media Type", "form data only", "text/plain; charset=utf-8")
        length = int(environ.get("CONTENT_LENGTH") or 0)
        if length > MAX_BODY:
            return reply("413 Content Too Large", "request too large", "text/plain; charset=utf-8")
        form = parse_qs(environ["wsgi.input"].read(length).decode("utf-8"), keep_blank_values=True)
        try:
            manifest = manifest_from_form(schema, form)
            name, data = _zip(manifest, core_path, render)
        except (ValueError, core.CoreError) as exc:
            return reply("400 Bad Request", page(schema, _submitted(schema, form), str(exc).splitlines()))
        disposition = ("Content-Disposition", f'attachment; filename="{name}.zip"')
        return reply("200 OK", data, "application/zip", [disposition])

    return app


def _submitted(schema, form):
    return {
        f["name"]: form.get(f["name"], []) if f.get("multiple") else form.get(f["name"], [""])[0]
        for f in schema
    }


def serve(core_path, host, port):
    with make_server(host, port, make_app(core_path)) as server:
        print(f"builder on http://{host}:{port}/")
        server.serve_forever()
