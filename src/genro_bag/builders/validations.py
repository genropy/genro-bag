# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Validation utilities for builder attributes.

This module provides validation functions and constraint classes for
validating builder element attributes at runtime.

Constraint classes for use with Annotated:
    Pattern: regex pattern for strings
    Min: minimum value for numbers
    Max: maximum value for numbers
    MinLength: minimum length for strings
    MaxLength: maximum length for strings
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

# Pattern for tag with optional cardinality: tag, tag[n], tag[n:], tag[:m], tag[n:m]
_TAG_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\[(\d*):?(\d*)\])?$")


class Pattern:
    """Regex pattern constraint for string validation."""

    def __init__(self, regex: str):
        self.regex = regex


class Min:
    """Minimum value constraint for numeric validation."""

    def __init__(self, value: int | float | Decimal):
        self.value = value


class Max:
    """Maximum value constraint for numeric validation."""

    def __init__(self, value: int | float | Decimal):
        self.value = value


class MinLength:
    """Minimum length constraint for string validation."""

    def __init__(self, value: int):
        self.value = value


class MaxLength:
    """Maximum length constraint for string validation."""

    def __init__(self, value: int):
        self.value = value


def parse_tag_spec(spec: str) -> tuple[str, int, int | None]:
    """Parse a tag specification with optional cardinality.

    Args:
        spec: Tag spec like 'foo', 'foo[1]', 'foo[1:]', 'foo[:2]', 'foo[1:3]'

    Returns:
        Tuple of (tag_name, min_count, max_count)

    Raises:
        ValueError: If spec format is invalid.
    """
    match = _TAG_PATTERN.match(spec.strip())
    if not match:
        raise ValueError(f"Invalid tag specification: '{spec}'")

    tag = match.group(1)
    min_str = match.group(2)
    max_str = match.group(3)

    # No brackets: unlimited (0..inf)
    if min_str is None and max_str is None:
        return tag, 0, None

    # Check if there was a colon in the original spec
    has_colon = ":" in spec

    if not has_colon:
        # tag[n] - exactly n
        n = int(min_str) if min_str else 0
        return tag, n, n

    # Has colon: slice syntax
    min_count = int(min_str) if min_str else 0
    max_count = int(max_str) if max_str else None

    return tag, min_count, max_count


def extract_attrs_from_signature(func: Callable) -> dict[str, dict[str, Any]] | None:
    """Extract attribute specs from function signature type hints.

    Extracts typed parameters (excluding self, target, tag, label, value, **kwargs)
    and converts them to attrs spec format for validation.

    Returns None if no typed parameters found.
    """
    sig = inspect.signature(func)
    attrs_spec: dict[str, dict[str, Any]] = {}

    # Skip these parameters - they're not user attributes
    # Include both old (target, tag, label) and new (_target, _tag, _label) names
    skip_params = {"self", "target", "tag", "label", "value", "_target", "_tag", "_label"}

    for name, param in sig.parameters.items():
        if name in skip_params:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            continue

        attr_spec = annotation_to_attr_spec(annotation)

        if param.default is inspect.Parameter.empty:
            attr_spec["required"] = True
        else:
            attr_spec["required"] = False
            if param.default is not None:
                attr_spec["default"] = param.default

        attrs_spec[name] = attr_spec

    return attrs_spec if attrs_spec else None


def validate_call_args(
    args: dict[str, Any], spec: dict[str, dict[str, Any]]
) -> None:
    """Validate call arguments against attribute specification.

    Args:
        args: Dict of argument values to validate.
        spec: Dict mapping arg names to their validation specs.

    Raises:
        ValueError: If validation fails.
    """
    errors = []

    for attr_name, attr_spec in spec.items():
        value = args.get(attr_name)
        required = attr_spec.get("required", False)
        type_name = attr_spec.get("type", "string")

        if required and value is None:
            errors.append(f"'{attr_name}' is required")
            continue

        if value is None:
            continue

        if type_name == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"'{attr_name}' must be an integer, got {type(value).__name__}")
                    continue

            min_val = attr_spec.get("min")
            max_val = attr_spec.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"'{attr_name}' must be >= {min_val}, got {value}")
            if max_val is not None and value > max_val:
                errors.append(f"'{attr_name}' must be <= {max_val}, got {value}")

        elif type_name == "decimal":
            if not isinstance(value, Decimal):
                try:
                    value = Decimal(str(value))
                except Exception:
                    errors.append(f"'{attr_name}' must be a decimal, got {type(value).__name__}")
                    continue

            min_val = attr_spec.get("min")
            max_val = attr_spec.get("max")
            if min_val is not None and value < Decimal(str(min_val)):
                errors.append(f"'{attr_name}' must be >= {min_val}, got {value}")
            if max_val is not None and value > Decimal(str(max_val)):
                errors.append(f"'{attr_name}' must be <= {max_val}, got {value}")

        elif type_name == "bool":
            if not isinstance(value, bool):
                if isinstance(value, str):
                    if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                        errors.append(f"'{attr_name}' must be a boolean, got '{value}'")
                else:
                    errors.append(f"'{attr_name}' must be a boolean, got {type(value).__name__}")

        elif type_name == "enum":
            values = attr_spec.get("values", [])
            if values and value not in values:
                errors.append(f"'{attr_name}' must be one of {values}, got '{value}'")

        elif type_name == "string":
            str_value = str(value)

            pattern = attr_spec.get("pattern")
            if pattern and not re.fullmatch(pattern, str_value):
                errors.append(f"'{attr_name}' must match pattern '{pattern}', got '{str_value}'")

            min_len = attr_spec.get("minLength")
            max_len = attr_spec.get("maxLength")
            if min_len is not None and len(str_value) < min_len:
                errors.append(f"'{attr_name}' must have at least {min_len} characters, got {len(str_value)}")
            if max_len is not None and len(str_value) > max_len:
                errors.append(f"'{attr_name}' must have at most {max_len} characters, got {len(str_value)}")

    if errors:
        raise ValueError("Attribute validation failed: " + "; ".join(errors))


def annotation_to_attr_spec(annotation: Any) -> dict[str, Any]:
    """Convert a type annotation to attr spec dict.

    Handles:
    - int -> {'type': 'int'}
    - str -> {'type': 'string'}
    - bool -> {'type': 'bool'}
    - Decimal -> {'type': 'decimal'}
    - Literal['a', 'b'] -> {'type': 'enum', 'values': ['a', 'b']}
    - int | None -> {'type': 'int'} (optional handled separately)
    - Optional[int] -> {'type': 'int'}
    - Annotated[str, Pattern(r'...')] -> {'type': 'string', 'pattern': '...'}
    - Annotated[int, Min(1), Max(10)] -> {'type': 'int', 'min': 1, 'max': 10}
    """
    from typing import Annotated, Literal, Union, get_args, get_origin

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        base_type = args[0]
        constraints = args[1:]

        spec = annotation_to_attr_spec(base_type)

        for constraint in constraints:
            if isinstance(constraint, Pattern):
                spec["pattern"] = constraint.regex
            elif isinstance(constraint, Min):
                spec["min"] = constraint.value
            elif isinstance(constraint, Max):
                spec["max"] = constraint.value
            elif isinstance(constraint, MinLength):
                spec["minLength"] = constraint.value
            elif isinstance(constraint, MaxLength):
                spec["maxLength"] = constraint.value

        return spec

    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return annotation_to_attr_spec(non_none_args[0])
        return {"type": "string"}

    if origin is Literal:
        return {"type": "enum", "values": list(args)}

    if annotation is int:
        return {"type": "int"}
    elif annotation is bool:
        return {"type": "bool"}
    elif annotation is str:
        return {"type": "string"}
    elif annotation is Decimal:
        return {"type": "decimal"}

    return {"type": "string"}
