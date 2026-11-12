import io
import unittest
import zipfile
from pathlib import Path
from urllib.parse import urlencode

from infinito_builder import core
from infinito_builder.web import MAX_BODY, make_app, manifest_from_form

SCHEMA = [
    {"name": "name", "help": "Name", "type": "string"},
    {"name": "port", "help": "Port", "type": "integer"},
    {"name": "database", "help": "DB", "type": "string", "choices": ["postgres", "none"], "default": "none"},
    {"name": "features", "help": "Features", "type": "string", "choices": ["email", "redis"], "multiple": True, "default": []},
    {"name": "volumes", "help": "Volumes", "type": "string", "multiple": True, "default": []},
]


def fake_render(manifest, core_path, roles_dir, force):
    if manifest.get("name") == "bad":
        raise core.CoreError("name: <script>bad</script>")
    role = Path(roles_dir) / f"web-app-cst-{manifest['name']}"
    (role / "meta").mkdir(parents=True)
    (role / "meta" / "main.yml").write_text("galaxy_info: {}\n")
    return role


def call(app, method, path, body=b"", content_type="application/x-www-form-urlencoded"):
    status = {}
    environ = {
        "REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
    }
    data = b"".join(app(environ, lambda s, h: status.update(code=s, headers=dict(h))))
    return status["code"], status["headers"], data


class WebTest(unittest.TestCase):
    def setUp(self):
        self.app = make_app("/nonexistent", SCHEMA, fake_render)

    def test_manifest_from_form_coerces_each_field(self):
        form = {"name": ["shop"], "port": ["8080"], "database": ["postgres"],
                "features": ["email", "redis"], "volumes": ["/data\n/srv/static\n"]}
        self.assertEqual(manifest_from_form(SCHEMA, form), {
            "name": "shop", "port": 8080, "database": "postgres",
            "features": ["email", "redis"], "volumes": ["/data", "/srv/static"],
        })

    def test_get_shows_form_without_upload(self):
        code, _, data = call(self.app, "GET", "/")
        self.assertEqual(code, "200 OK")
        self.assertIn(b'name="port"', data)
        self.assertNotIn(b'type="file"', data)
        self.assertNotIn(b"multipart", data)

    def test_post_returns_zip_with_role_manifest_and_snippet(self):
        body = urlencode({"name": "shop", "port": "8080"}).encode()
        code, headers, data = call(self.app, "POST", "/render", body)
        self.assertEqual(code, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/zip")
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertIn("ansible/roles/web-app-cst-shop/meta/main.yml", names)
        self.assertIn("infinito-builder.yml", names)
        self.assertIn("inventory-snippet.yml", names)

    def test_render_error_is_escaped_and_keeps_values(self):
        body = urlencode({"name": "bad", "port": "8080"}).encode()
        code, _, data = call(self.app, "POST", "/render", body)
        self.assertEqual(code, "400 Bad Request")
        self.assertIn(b"&lt;script&gt;bad&lt;/script&gt;", data)
        self.assertNotIn(b"<script>bad", data)
        self.assertIn(b'value="8080"', data)

    def test_rejects_upload_types_oversize_and_other_paths(self):
        self.assertEqual(call(self.app, "POST", "/render", b"x", "multipart/form-data")[0], "415 Unsupported Media Type")
        self.assertEqual(call(self.app, "POST", "/render", b"x" * (MAX_BODY + 1))[0], "413 Content Too Large")
        self.assertEqual(call(self.app, "GET", "/render")[0], "404 Not Found")


if __name__ == "__main__":
    unittest.main()
