def coerce(field, raw):
    """Turn the raw text a user typed for one schema field into its value.

    Args:
        field: one entry of the core skeleton schema.
        raw: the text the user typed; for a multiple field a comma list or a list.

    Returns:
        The field's default for empty input, else a list, an int or the string.
    """
    if isinstance(raw, list):
        parts = [part.strip() for part in raw if part.strip()]
        return parts if parts or not field.get("multiple") else field.get("default")
    raw = (raw or "").strip()
    if not raw:
        return field.get("default")
    if field.get("multiple"):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if field.get("type") == "integer":
        return int(raw)
    return raw
