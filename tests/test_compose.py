import unittest

from infinito_builder.compose import manifest_from_compose


class ManifestFromComposeTest(unittest.TestCase):
    def test_maps_app_database_feature_and_lists_unmapped(self):
        compose = {
            "services": {
                "db": {"image": "postgres:16"},
                "web": {
                    "image": "ghcr.io/acme/web:1.2.3",
                    "ports": ["127.0.0.1:8080:3000/tcp"],
                    "environment": ["MODE=prod", "EMPTY"],
                    "volumes": ["data:/var/lib/web", "/srv/static"],
                },
                "cache": {"image": "redis:7"},
                "worker": {"image": "ghcr.io/acme/web:1.2.3"},
            }
        }
        manifest, unmapped = manifest_from_compose(compose)
        self.assertEqual(manifest["name"], "web")
        self.assertEqual(manifest["image"], "ghcr.io/acme/web:1.2.3")
        self.assertEqual(manifest["port"], 3000)
        self.assertEqual(manifest["database"], "postgres")
        self.assertEqual(manifest["features"], ["redis"])
        self.assertEqual(manifest["environment"], {"MODE": "prod", "EMPTY": ""})
        self.assertEqual(manifest["volumes"], ["/var/lib/web", "/srv/static"])
        self.assertEqual(unmapped, ["worker"])

    def test_long_port_syntax_and_mysql_maps_to_mariadb(self):
        compose = {
            "services": {
                "app": {"image": "acme/app:2", "ports": [{"target": 80, "published": 8000}],
                        "environment": {"A": 1, "B": None}},
                "mysql": {"image": "mysql:8"},
            }
        }
        manifest, unmapped = manifest_from_compose(compose)
        self.assertEqual(manifest["port"], 80)
        self.assertEqual(manifest["database"], "mariadb")
        self.assertEqual(manifest["environment"], {"A": "1", "B": ""})
        self.assertEqual(unmapped, [])

    def test_no_published_port_leaves_app_fields_empty(self):
        manifest, unmapped = manifest_from_compose({"services": {"job": {"image": "acme/job:1"}}})
        self.assertNotIn("name", manifest)
        self.assertEqual(unmapped, ["job"])


if __name__ == "__main__":
    unittest.main()
