# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Validation utilities for builder attributes.

This module provides validation functions and constraint classes for
validating builder element attributes at runtime.

Constraint classes for use with Annotated:
    Regex: regex pattern for strings
    Range: min/max value constraints for numbers (ge, le, gt, lt)

Type hints supported:
    - Basic types: int, str, bool, float, Decimal
    - Literal['a', 'b'] for enum-like constraints
    - list[T], dict[K, V], tuple[...], set[T] for generics
    - X | None for optional
    - Annotated[T, validator...] for validators
"""

from __future__ import annotations

import inspect
import re
import types
from dataclasses import dataclass
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..bag import Bag
    from ..bagnode import BagNode


# --- Validator classes (Annotated metadata) ---


@dataclass(frozen=True)
class Regex:
    """Regex pattern constraint for string validation."""

    pattern: str
    flags: int = 0

    def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError("Regex validator requires a str")
        if re.fullmatch(self.pattern, value, self.flags) is None:
            raise ValueError(f"must match pattern '{self.pattern}'")


@dataclass(frozen=True)
class Range:
    """Range constraint for numeric validation (Pydantic-style: ge, le, gt, lt)."""

    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None

    def __call__(self, value: Any) -> None:
        if not isinstance(value, (int, float, Decimal)):
            raise TypeError("Range validator requires int, float or Decimal")
        if self.ge is not None and value < self.ge:
            raise ValueError(f"must be >= {self.ge}")
        if self.le is not None and value > self.le:
            raise ValueError(f"must be <= {self.le}")
        if self.gt is not None and value <= self.gt:
            raise ValueError(f"must be > {self.gt}")
        if self.lt is not None and value >= self.lt:
            raise ValueError(f"must be < {self.lt}")


# --- Type hint parsing utilities ---


def split_annotated(tp: Any) -> tuple[Any, list]:
    """Split Annotated type into base type and validators.

    Args:
        tp: A type annotation, possibly Annotated.

    Returns:
        Tuple of (base_type, validators) where validators are callables.
    """
    if get_origin(tp) is Annotated:
        base, *meta = get_args(tp)
        validators = [m for m in meta if callable(m)]
        return base, validators
    return tp, []


def check_type(value: Any, tp: Any) -> bool:
    """Check if value matches the type annotation.

    Args:
        value: The value to check.
        tp: The type annotation to check against.

    Returns:
        True if value matches the type, False otherwise.
    """
    tp, _ = split_annotated(tp)

    origin = get_origin(tp)
    args = get_args(tp)

    # Any type
    if tp is Any:
        return True

    # None type
    if tp is type(None):
        return value is None

    # Literal['a', 'b', 'c']
    if origin is Literal:
        return value in args

    # Union / Optional (X | Y or Union[X, Y])
    if origin is types.UnionType:
        return any(check_type(value, t) for t in args)

    # typing.Union (for older Python compatibility)
    try:
        from typing import Union

        if origin is Union:
            return any(check_type(value, t) for t in args)
    except ImportError:
        pass

    # No origin - concrete type
    if origin is None:
        try:
            return isinstance(value, tp)
        except TypeError:
            # Special types not isinstanceable
            return True

    # Generic builtins
    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(check_type(v, t_item) for v in value)

    if origin is dict:
        if not isinstance(value, dict):
            return False
        if not args:
            return True
        k_t, v_t = args[0], args[1] if len(args) > 1 else Any
        return all(check_type(k, k_t) and check_type(v, v_t) for k, v in value.items())

    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:
            return all(check_type(v, args[0]) for v in value)
        return len(value) == len(args) and all(
            check_type(v, t) for v, t in zip(value, args, strict=True)
        )

    if origin is set:
        if not isinstance(value, set):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(check_type(v, t_item) for v in value)

    # Fallback for other origins
    try:
        return isinstance(value, origin)
    except TypeError:
        return True


def extract_validators_from_signature(fn: Callable) -> dict[str, tuple[Any, list, Any]]:
    """Extract type hints with validators from function signature.

    Args:
        fn: The function to extract from.

    Returns:
        Dict mapping parameter name to (base_type, validators, default) tuple.
    """
    # Skip these parameters - they're not user attributes
    skip_params = {"self", "target", "tag", "label", "value", "_target", "_tag", "_label"}

    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        return {}

    result = {}
    sig = inspect.signature(fn)

    for name, param in sig.parameters.items():
        if name in skip_params:
            continue
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue

        tp = hints.get(name)
        if tp is None:
            continue

        base, validators = split_annotated(tp)
        result[name] = (base, validators, param.default)

    return result


# --- Sub-tags validation utilities ---


def parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int | None]]:
    """Parse sub_tags spec into dict of {tag: (min, max)}.

    Args:
        spec: Comma-separated tags with optional cardinality.
            - 'div' → {'div': (0, None)} - any number
            - 'div[:1]' → {'div': (0, 1)} - at most 1
            - 'div[1:]' → {'div': (1, None)} - at least 1
            - 'div[2:5]' → {'div': (2, 5)} - between 2 and 5

    Returns:
        Dict mapping tag name to (min_count, max_count) tuple.
    """
    result: dict[str, tuple[int, int | None]] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)(?:\[(\d*):(\d*)\])?$", item)
        if match:
            tag = match.group(1)
            min_val = int(match.group(2)) if match.group(2) else 0
            max_val = int(match.group(3)) if match.group(3) else None
            result[tag] = (min_val, max_val)
    return result


def parse_sub_tags_order(order: str) -> list[set[str]]:
    """Parse sub_tags order spec into list of tag groups.

    Args:
        order: Groups separated by '>' with tags separated by ','.
            - 'a,b>c>d,e' → [{'a','b'}, {'c'}, {'d','e'}]

    Returns:
        List of sets, each set contains tags that can appear in any order
        within that group, but groups must appear in sequence.
    """
    result: list[set[str]] = []
    for group in order.split(">"):
        tags = {t.strip() for t in group.split(",") if t.strip()}
        if tags:
            result.append(tags)
    return result


def validate_sub_tags_membership(tags: list[str], allowed: set[str]) -> bool:
    """Check all tags are in allowed set."""
    return all(tag in allowed for tag in tags)


def validate_sub_tags_cardinality(
    tags: list[str], spec: dict[str, tuple[int, int | None]]
) -> bool:
    """Check tag counts match cardinality constraints."""
    from collections import Counter

    counts = Counter(tags)

    # Check each tag in the list is allowed
    for tag in counts:
        if tag not in spec:
            return False

    # Check cardinality constraints
    for tag, (min_count, max_count) in spec.items():
        count = counts.get(tag, 0)
        if count < min_count:
            return False
        if max_count is not None and count > max_count:
            return False

    return True


def validate_sub_tags_order(tags: list[str], order_groups: list[set[str]]) -> bool:
    """Check tags respect group ordering.

    Tags in earlier groups must appear before tags in later groups.
    Tags not in any group can appear anywhere.
    """
    current_group_idx = 0
    for tag in tags:
        # Find which group this tag belongs to
        tag_group_idx = None
        for i, group in enumerate(order_groups):
            if tag in group:
                tag_group_idx = i
                break

        if tag_group_idx is None:
            continue  # Tag not in order spec, can be anywhere

        if tag_group_idx < current_group_idx:
            return False  # Tag from earlier group after later group

        current_group_idx = tag_group_idx

    return True


# --- BuilderValidationsMixin ---


class BuilderValidationsMixin:
    """Mixin for builder child validation. Requires self._schema (Bag)."""

    def _get_sub_tags_spec(self, node: BagNode) -> tuple[str | None, str | None]:
        """Return (sub_tags, sub_tags_order) for the node's tag."""
        tag = node.tag
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None, None
        return (
            schema_node.attr.get("sub_tags"),
            schema_node.attr.get("sub_tags_order"),
        )

    def _sub_tags_validation_pattern(self, node: BagNode) -> str | None:
        """Return the sub_tags spec for the node's tag (for error messages)."""
        sub_tags, _ = self._get_sub_tags_spec(node)
        return sub_tags

    def _can_add_child(
        self, node: BagNode, child_tag: str, node_position: str | int | None = None
    ) -> bool:
        """Check if node accepts child_tag as child.

        Args:
            node: The node to add the child to
            child_tag: The tag of the child to add
            node_position: Insertion position (same syntax as NodeContainer._parse_position)
        """
        from ..bag import Bag

        sub_tags, sub_tags_order = self._get_sub_tags_spec(node)

        if not isinstance(node.value, Bag):
            return self._validate_sub_tags(sub_tags, sub_tags_order, [child_tag])

        idx = node.value._nodes._parse_position(node_position)
        current_tags = [n.tag for n in node.value]
        new_tags = current_tags[:idx] + [child_tag] + current_tags[idx:]
        return self._validate_sub_tags(sub_tags, sub_tags_order, new_tags)

    def _validate_sub_tags(
        self, sub_tags: str | None, sub_tags_order: str | None, tags: list[str]
    ) -> bool:
        """Validate list of child tags against sub_tags spec and order.

        Args:
            sub_tags: Sub-tags spec with cardinality (e.g. 'div,span[:1],p[1:]')
            sub_tags_order: Order spec (e.g. 'header>body,aside>footer')
            tags: List of child tags to validate

        Returns:
            True if valid, False otherwise.
        """
        # Leaf element (empty string)
        if sub_tags == "":
            return len(tags) == 0

        # No validation
        if sub_tags is None:
            return True

        # Parse and validate cardinality (includes membership check)
        spec = parse_sub_tags_spec(sub_tags)
        if not validate_sub_tags_cardinality(tags, spec):
            return False

        # Validate order if specified
        if sub_tags_order:
            order_groups = parse_sub_tags_order(sub_tags_order)
            if not validate_sub_tags_order(tags, order_groups):
                return False

        return True

    def _accept_child(
        self, destination_bag: Bag, child_tag: str, node_position: str | int | None = None
    ) -> None:
        """Verify destination accepts child_tag. Raises ValueError if not allowed."""
        parent_node = destination_bag.parent_node
        if parent_node is None:
            return  # root level, no validation

        schema_node = self._schema.node(parent_node.tag)
        if schema_node is None:
            return

        sub_tags = schema_node.attr.get("sub_tags")
        sub_tags_order = schema_node.attr.get("sub_tags_order")

        if sub_tags is None:
            return  # no validation

        current_tags = [n.tag for n in destination_bag]
        idx = destination_bag._nodes._parse_position(node_position)
        new_tags = current_tags[:idx] + [child_tag] + current_tags[idx:]

        if not self._validate_sub_tags(sub_tags, sub_tags_order, new_tags):
            raise ValueError(f"'{child_tag}' not allowed as child of '{parent_node.tag}'")

    def _get_method(self, tag: str, destination_bag: Bag, kwargs: dict) -> Callable:
        """Get handler method after validation. Raises KeyError if tag not in schema."""
        handler_name, _, call_args_validations = self.get_schema_info(tag)  # type: ignore[attr-defined]
        self._validate_call_args(kwargs, call_args_validations)
        self._accept_child(destination_bag, tag, kwargs.get("node_position"))
        return getattr(self, handler_name) if handler_name else self._default_element  # type: ignore[attr-defined]

    def _get_call_args_validations(self, tag: str) -> dict[str, tuple[Any, list, Any]] | None:
        """Return attribute spec for a tag from schema.

        Returns dict mapping attr name to (base_type, validators, default).
        """
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None
        return schema_node.attr.get("call_args_validations")

    def _validate_call_args(
        self,
        args: dict[str, Any],
        spec: dict[str, tuple[Any, list, Any]] | None,
    ) -> None:
        """Validate type/pattern/range - raise on error.

        Args:
            args: Dict of argument values to validate.
            spec: Dict mapping attr name to (base_type, validators, default).

        Raises:
            TypeError: If type check fails.
            ValueError: If validator fails.
        """
        if not spec:
            return

        errors = []

        for attr_name, (base_type, validators, _default) in spec.items():
            value = args.get(attr_name)
            if value is None:
                continue  # required is SOFT

            # Type check
            if not check_type(value, base_type):
                errors.append(f"'{attr_name}': expected {base_type}, got {type(value).__name__}")
                continue

            # Validator checks
            for v in validators:
                try:
                    v(value)
                except Exception as e:
                    errors.append(f"'{attr_name}': {e}")

        if errors:
            raise ValueError("Attribute validation failed: " + "; ".join(errors))

    def _check_required_attrs(
        self,
        args: dict[str, Any],
        spec: dict[str, tuple[Any, list, Any]],
    ) -> list[str]:
        """Return list of errors for missing required attrs (SOFT).

        Required = parameter has no default value (default is inspect.Parameter.empty).
        """
        errors: list[str] = []
        for attr_name, (_base_type, _validators, default) in spec.items():
            if default is inspect.Parameter.empty and args.get(attr_name) is None:
                errors.append(f"required attribute '{attr_name}' is missing")
        return errors

