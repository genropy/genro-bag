# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Decorator for builder methods with tag registration and validation rules."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from .validations import (
    extract_attrs_from_signature,
    parse_tag_spec,
    validate_call_args,
)


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
            tag, min_c, max_c = parse_tag_spec(spec)
            parsed_children[tag] = (min_c, max_c)

    def decorator(func: Callable) -> Callable:
        attrs_spec: dict[str, dict[str, Any]] | None = None
        if validate:
            attrs_spec = extract_attrs_from_signature(func)

        @wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            # Remap underscore-prefixed params to non-prefixed for user methods
            # This allows HTML attributes like target='_blank' to not clash
            if "_tag" in kwargs:
                kwargs["tag"] = kwargs.pop("_tag")
            if "_label" in kwargs:
                kwargs["label"] = kwargs.pop("_label")

            if attrs_spec:
                validate_call_args(kwargs, attrs_spec)
            return func(self, *args, **kwargs)

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
