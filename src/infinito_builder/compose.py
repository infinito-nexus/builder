DATABASE_IMAGES = {"postgres": "postgres", "mariadb": "mariadb", "mysql": "mariadb"}
FEATURE_IMAGES = {"redis": "redis", "valkey": "redis"}


def _image_base(image):
    return image.rsplit("/", 1)[-1].split(":", 1)[0].split("@", 1)[0]


def _container_port(entry):
    if isinstance(entry, dict):
        return int(entry["target"])
    return int(str(entry).split("/", 1)[0].rsplit(":", 1)[-1])


def _environment(env):
    if isinstance(env, dict):
        return {str(k): "" if v is None else str(v) for k, v in env.items()}
    return dict(item.split("=", 1) if "=" in item else (item, "") for item in env or [])


def _volumes(entries):
    paths = []
    for entry in entries or []:
        if isinstance(entry, dict):
            paths.append(entry["target"])
        else:
            parts = str(entry).split(":")
            paths.append(parts[1] if len(parts) > 1 else parts[0])
    return paths


def manifest_from_compose(compose):
    """Map a parsed compose file onto a builder manifest.

    Args:
        compose: the compose file as parsed by yaml.safe_load.

    Returns:
        (manifest, unmapped): the manifest dict and the names of the services
        that map onto nothing, in compose order.
    """
    services = compose.get("services") or {}
    manifest = {"database": "none", "login": "none", "features": []}
    app = None
    unmapped = []
    for name, service in services.items():
        base = _image_base(service.get("image", ""))
        if base in DATABASE_IMAGES and manifest["database"] == "none":
            manifest["database"] = DATABASE_IMAGES[base]
        elif base in FEATURE_IMAGES and FEATURE_IMAGES[base] not in manifest["features"]:
            manifest["features"].append(FEATURE_IMAGES[base])
        elif app is None and service.get("ports"):
            app = name
        else:
            unmapped.append(name)
    if app is None:
        return manifest, unmapped
    service = services[app]
    manifest.update(
        name=app,
        image=service.get("image", ""),
        port=_container_port(service["ports"][0]),
        environment=_environment(service.get("environment")),
        volumes=_volumes(service.get("volumes")),
    )
    return manifest, unmapped
