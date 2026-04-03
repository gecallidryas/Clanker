from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True, frozen=True)
class ValidationErrorDetail:
    path: str
    message: str


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def _validate_node(value: Any, schema: dict[str, Any], path: str, errors: list[ValidationErrorDetail]) -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(ValidationErrorDetail(path=path, message=f"expected object, got {_json_type_name(value)}"))
            return
        properties = schema.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        required = schema.get("required")
        required_items = required if isinstance(required, list) else []
        for key in required_items:
            if key not in value:
                errors.append(ValidationErrorDetail(path=f"{path}.{key}" if path else str(key), message="is required"))
        additional = schema.get("additionalProperties", True)
        if additional is False:
            for key in value.keys():
                if key not in properties:
                    errors.append(ValidationErrorDetail(path=f"{path}.{key}" if path else str(key), message="is not allowed"))
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                _validate_node(value[key], child_schema, f"{path}.{key}" if path else str(key), errors)
        return
    if expected_type == "array":
        if not isinstance(value, list):
            errors.append(ValidationErrorDetail(path=path, message=f"expected array, got {_json_type_name(value)}"))
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_node(item, item_schema, f"{path}[{index}]", errors)
        return
    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(ValidationErrorDetail(path=path, message=f"expected string, got {_json_type_name(value)}"))
    elif expected_type == "integer":
        if not (isinstance(value, int) and not isinstance(value, bool)):
            errors.append(ValidationErrorDetail(path=path, message=f"expected integer, got {_json_type_name(value)}"))
    elif expected_type == "number":
        if not ((isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)):
            errors.append(ValidationErrorDetail(path=path, message=f"expected number, got {_json_type_name(value)}"))
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(ValidationErrorDetail(path=path, message=f"expected boolean, got {_json_type_name(value)}"))

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        errors.append(ValidationErrorDetail(path=path, message=f"value must be one of {enum_values}"))


def validate_arguments(arguments: dict[str, Any], schema: Optional[dict[str, Any]]) -> list[ValidationErrorDetail]:
    if not schema:
        return []
    normalized_arguments = arguments if isinstance(arguments, dict) else {}
    errors: list[ValidationErrorDetail] = []
    _validate_node(normalized_arguments, schema, "", errors)
    return errors
