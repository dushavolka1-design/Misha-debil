from __future__ import annotations

from typing import Any

from app.services.analysis.schema import FACTS_RESPONSE_SCHEMA, FINDING_ITEM_SCHEMA


class SchemaValidationError(ValueError):
    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def validate_against_schema(instance: Any, schema: dict, path: str = "$") -> None:
    """Minimal JSON Schema subset: type, required, enum, additionalProperties=False, min/max."""
    if "type" in schema and not _type_ok(instance, schema["type"]):
        raise SchemaValidationError(f"type mismatch at {path}", path=path)

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"enum mismatch at {path}", path=path)

    if schema.get("type") == "string":
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaValidationError(f"minLength at {path}", path=path)
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SchemaValidationError(f"maxLength at {path}", path=path)

    if schema.get("type") == "number" or schema.get("type") == "integer":
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"minimum at {path}", path=path)
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"maximum at {path}", path=path)

    if schema.get("type") == "object":
        assert isinstance(instance, dict)
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise SchemaValidationError(f"missing required {path}.{key}", path=f"{path}.{key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = set(instance) - set(props)
            if extras:
                raise SchemaValidationError(
                    f"additional properties not allowed at {path}: {sorted(extras)}",
                    path=path,
                )
        for key, child in instance.items():
            if key in props:
                validate_against_schema(child, props[key], f"{path}.{key}")

    if schema.get("type") == "array":
        assert isinstance(instance, list)
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                validate_against_schema(item, item_schema, f"{path}[{i}]")


def validate_finding(finding: dict) -> None:
    validate_against_schema(finding, FINDING_ITEM_SCHEMA)


def validate_facts_payload(payload: dict) -> None:
    validate_against_schema(payload, FACTS_RESPONSE_SCHEMA)


def reject_invalid_llm_findings(findings: list[dict]) -> tuple[list[dict], list[str]]:
    """Return only schema-valid findings; do not silently repair."""
    ok: list[dict] = []
    rejected: list[str] = []
    for i, f in enumerate(findings):
        try:
            validate_finding(f)
            if not f.get("citation"):
                raise SchemaValidationError("citation required")
            ok.append(f)
        except SchemaValidationError as exc:
            rejected.append(f"finding[{i}]: {exc}")
    return ok, rejected
