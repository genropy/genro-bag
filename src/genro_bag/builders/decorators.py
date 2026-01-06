# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Decorators for builder methods validation rules.

This module provides the @element decorator for defining builder methods
with tag registration and validation rules.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, Union, get_args, get_origin

# Pattern for tag with optional cardinality: tag, tag[n], tag[n:], tag[:m], tag[n:m]
_TAG_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\[(\d*):?(\d*)\])?$")


def _parse_tag_spec(spec: str) -> tuple[str, int, int | None]:
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


def _extract_attrs_from_signature(func: Callable) -> dict[str, dict[str, Any]] | None:
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

        attr_spec = _annotation_to_attr_spec(annotation)

        if param.default is inspect.Parameter.empty:
            attr_spec["required"] = True
        else:
            attr_spec["required"] = False
            if param.default is not None:
                attr_spec["default"] = param.default

        attrs_spec[name] = attr_spec

    return attrs_spec if attrs_spec else None


def _annotation_to_attr_spec(annotation: Any) -> dict[str, Any]:
    """Convert a type annotation to attr spec dict.

    Handles:
    - int -> {'type': 'int'}
    - str -> {'type': 'string'}
    - bool -> {'type': 'bool'}
    - Literal['a', 'b'] -> {'type': 'enum', 'values': ['a', 'b']}
    - int | None -> {'type': 'int'} (optional handled separately)
    - Optional[int] -> {'type': 'int'}
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle Union types (including Optional which is Union[X, None])
    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _annotation_to_attr_spec(non_none_args[0])
        return {"type": "string"}

    # Handle Literal
    if origin is Literal:
        return {"type": "enum", "values": list(args)}

    # Handle basic types
    if annotation is int:
        return {"type": "int"}
    elif annotation is bool:
        return {"type": "bool"}
    elif annotation is str:
        return {"type": "string"}

    return {"type": "string"}


def _parse_tags(tags: str | tuple[str, ...]) -> list[str]:
    """Parse tags parameter into a list of tag names."""
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, tuple) and tags:
        return list(tags)
    return []


def element(
    tags: str | tuple[str, ...] = "",
    children: str | tuple[str, ...] = "",
    validate: bool = True,
) -> Callable:
    """Decorator to define element tags and validation rules for a builder method.

    The decorator registers the method as handler for the specified tags.
    If no tags are specified, the method name is used as the tag.

    Attribute validation is automatically extracted from function signature
    type hints when validate=True (default).

    Args:
        tags: Tag names this method handles. Can be:
            - A comma-separated string: 'fridge, oven, sink'
            - A tuple of strings: ('fridge', 'oven', 'sink')
            If empty, the method name is used as the single tag.

        children: Valid child tag specs for structure validation. Can be:
            - A comma-separated string: 'tag1, tag2[:1], tag3[1:]'
            - A tuple of strings: ('tag1', 'tag2[:1]', 'tag3[1:]')

            Each spec can be:
            - 'tag' - allowed, no cardinality constraint (0..inf)
            - 'tag[n]' - exactly n required
            - 'tag[n:]' - at least n required
            - 'tag[:m]' - at most m allowed
            - 'tag[n:m]' - between n and m (inclusive)
            Empty string or empty tuple means no children allowed (leaf node).

        validate: If True (default), extract attribute validation rules from
            function signature type hints. Set to False to disable validation.

    Example:
        >>> class MyBuilder(BagBuilderBase):
        ...     @element(tags='fridge, oven, sink')
        ...     def appliance(self, target, tag, **attr):
        ...         return self.child(target, tag, value='', **attr)
        ...
        ...     @element(children='section, item[1:]')
        ...     def menu(self, target, tag, **attr):
        ...         return self.child(target, tag, **attr)
    """
    tag_list = _parse_tags(tags)

    children_str = children if isinstance(children, str) else ",".join(children)
    has_refs = "=" in children_str

    parsed_children: dict[str, tuple[int, int | None]] = {}

    if not has_refs:
        if isinstance(children, str):
            specs = [s.strip() for s in children.split(",") if s.strip()]
        else:
            specs = list(children)

        for spec in specs:
            tag, min_c, max_c = _parse_tag_spec(spec)
            parsed_children[tag] = (min_c, max_c)

    def decorator(func: Callable) -> Callable:
        attrs_spec: dict[str, dict[str, Any]] | None = None
        if validate:
            attrs_spec = _extract_attrs_from_signature(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Remap underscore-prefixed params to non-prefixed for user methods
            # This allows HTML attributes like target='_blank' to not clash
            if "_tag" in kwargs:
                kwargs["tag"] = kwargs.pop("_tag")
            if "_label" in kwargs:
                kwargs["label"] = kwargs.pop("_label")

            if attrs_spec:
                _validate_attrs_from_spec(attrs_spec, kwargs)
            return func(*args, **kwargs)

        if has_refs:
            wrapper._raw_children_spec = children
            wrapper._valid_children = frozenset()
            wrapper._child_cardinality = {}
        else:
            wrapper._valid_children = frozenset(parsed_children.keys())
            wrapper._child_cardinality = parsed_children

        wrapper._element_tags = tuple(tag_list) if tag_list else None
        wrapper._attrs_spec = attrs_spec

        return wrapper

    return decorator


def _validate_attrs_from_spec(
    attrs_spec: dict[str, dict[str, Any]], kwargs: dict[str, Any]
) -> None:
    """Validate kwargs against attrs spec extracted from signature.

    Raises:
        ValueError: If validation fails.
    """
    errors = []

    for attr_name, attr_spec in attrs_spec.items():
        value = kwargs.get(attr_name)
        required = attr_spec.get("required", False)
        type_name = attr_spec.get("type", "string")

        if required and value is None:
            errors.append(f"'{attr_name}' is required")
            continue

        if value is None:
            continue

        if type_name == "int":
            if not isinstance(value, int):
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(f"'{attr_name}' must be an integer, got {type(value).__name__}")
                    continue

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

    if errors:
        raise ValueError("Attribute validation failed: " + "; ".join(errors))
