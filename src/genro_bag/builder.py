# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders with validation.

Provides domain-specific methods for creating nodes in a Bag with
validation support.

Exports:
    element: Decorator to mark methods as element handlers
    abstract: Decorator to define abstract elements (for inheritance only)
    BagBuilderBase: Abstract base class for all builders
    Regex: Regex pattern constraint for string validation
    Range: Range constraint for numeric validation

Schema conventions:
    - Elements stored by name: 'div', 'span'
    - Abstracts prefixed with '@': '@flow', '@phrasing'
    - Use inherits_from='@abstract' to inherit sub_tags

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
from abc import ABC
from collections.abc import Callable
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

from .bag import Bag

if TYPE_CHECKING:
    from .bagnode import BagNode


# =============================================================================
# Decorators (Public API)
# =============================================================================


def element(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    sub_tags_order: str | None = None,
    inherits_from: str | None = None,
) -> Callable:
    """Decorator to mark a method as element handler.

    Args:
        tags: Tag names this method handles.
        sub_tags: Valid child tags with optional cardinality.
        sub_tags_order: Optional ordering constraint.
        inherits_from: Abstract element to inherit sub_tags from.
    """

    def decorator(func: Callable) -> Callable:
        func._decorator = {  # type: ignore[attr-defined]
            k: v for k, v in {
                "tags": tags,
                "sub_tags": sub_tags,
                "sub_tags_order": sub_tags_order,
                "inherits_from": inherits_from,
            }.items() if v is not None
        }
        return func

    return decorator


def abstract(
    sub_tags: str | tuple[str, ...] = "",
    sub_tags_order: str = "",
) -> Callable:
    """Decorator to define an abstract element (for inheritance only)."""

    def decorator(func: Callable) -> Callable:
        func._decorator = {  # type: ignore[attr-defined]
            "abstract": True,
            "sub_tags": sub_tags,
            "sub_tags_order": sub_tags_order,
        }
        return func

    return decorator


# =============================================================================
# Validator classes (Annotated metadata)
# =============================================================================


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


# =============================================================================
# BagBuilderBase
# =============================================================================


class BagBuilderBase(ABC):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes in a Bag.
    All element definitions are stored in a unified _schema Bag.

    Schema conventions:
        - Elements: stored directly by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Abstracts define sub_tags for inheritance, cannot be used directly

    Usage:
        >>> bag = Bag(builder=MyBuilder)
        >>> bag.div()  # looks up 'div' in _schema, calls handler
    """

    _schema: Bag  # type: ignore[assignment]

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _schema Bag from @element decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._schema = Bag().fill_from(getattr(cls, "schema_path", None))

        for tag_list, handler_name, obj, decorator_info in _pop_decorated_methods(cls):
            if handler_name:
                setattr(cls, handler_name, obj)

            sub_tags = decorator_info.get("sub_tags", "")
            sub_tags_order = decorator_info.get("sub_tags_order", "")
            inherits_from = decorator_info.get("inherits_from", "")
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                cls._schema.set_item(tag, None,
                    handler_name=handler_name,
                    sub_tags=sub_tags,
                    sub_tags_order=sub_tags_order,
                    inherits_from=inherits_from,
                    call_args_validations=call_args_validations,
                )

    def __init__(self, bag: Bag) -> None:
        """Bind builder to bag. Enables node.parent navigation."""
        self.bag = bag
        self.bag.set_backref()

    # -------------------------------------------------------------------------
    # Element dispatch
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _schema and return handler with validation."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def wrapper(destination_bag: Bag, *args: Any, _tag: str = name, **kwargs: Any) -> Any:
            try:
                method = self._get_method(_tag, destination_bag, kwargs)
            except KeyError as err:
                raise AttributeError(f"'{type(self).__name__}' has no element '{_tag}'") from err
            kwargs["tag"] = _tag
            return method(destination_bag, *args, **kwargs)
        return wrapper

    def _default_element(
        self,
        _target: Bag,
        tag: str,
        node_label: str | None = None,
        value: Any = None,
        **attr: Any,
    ) -> BagNode:
        """Default handler for elements without custom handler."""
        return self.child(_target, tag, node_label=node_label, value=value, **attr)

    def child(
        self,
        _target: Bag,
        _tag: str,
        node_label: str | None = None,
        value: Any = None,
        node_position: str | None = None,
        **attr: Any,
    ) -> BagNode:
        """Create a child node in the target Bag."""
        if node_label is None:
            n = 0
            while f"{_tag}_{n}" in _target._nodes:
                n += 1
            node_label = f"{_tag}_{n}"

        node = _target.set_item(node_label, value, _position=node_position, **attr)
        node.tag = _tag

        return node

    def _command_on_node(
        self, node: BagNode, child_tag: str, node_position: str | int | None = None, **attrs: Any
    ) -> BagNode:
        """Add a child to a node with STRICT/SOFT validation."""
        if not self._can_add_child(node, child_tag, node_position=node_position):
            pattern = self._sub_tags_validation_pattern(node)
            raise ValueError(
                f"'{child_tag}' not allowed as child of '{node.tag}' (pattern: {pattern!r})"
            )

        call_args_validations = self._get_call_args_validations(child_tag)
        self._validate_call_args(attrs, call_args_validations)

        if not isinstance(node.value, Bag):
            node.value = Bag()
            node.value._builder = self

        child_node = self.child(node.value, child_tag, node_position=node_position, **attrs)

        if call_args_validations:
            soft_errors = self._check_required_attrs(attrs, call_args_validations)
            child_node._invalid_reasons.extend(soft_errors)

        return child_node

    # -------------------------------------------------------------------------
    # Schema access
    # -------------------------------------------------------------------------

    @property
    def schema(self) -> Bag:
        """Return the class schema."""
        return type(self)._schema

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema."""
        return self.schema.get_node(name) is not None

    def get_schema_info(self, name: str) -> tuple[str | None, str | None, dict | None]:
        """Return schema info for an element."""
        attrs = self.schema.get_attr(name)
        if attrs is None:
            raise KeyError(f"Element '{name}' not found in schema")

        result = dict(attrs)
        inherits_from = result.pop("inherits_from", None)

        if inherits_from:
            abstract_attrs = self.schema.get_attr(inherits_from)
            if abstract_attrs:
                merged = dict(abstract_attrs)
                for k, v in result.items():
                    if v:
                        merged[k] = v
                result = merged

        return (
            result.get("handler_name"),
            result.get("sub_tags"),
            result.get("call_args_validations"),
        )

    def __iter__(self):
        """Iterate over schema nodes."""
        return iter(self.schema)

    def __repr__(self) -> str:
        """Show builder schema summary."""
        count = sum(1 for _ in self)
        return f"<{type(self).__name__} ({count} elements)>"

    def __str__(self) -> str:
        """Show schema structure."""
        return str(self.schema)

    # -------------------------------------------------------------------------
    # Validation check
    # -------------------------------------------------------------------------

    def check(self, bag: Bag | None = None) -> list[tuple[str, BagNode, list[str]]]:
        """Return report of invalid nodes."""
        if bag is None:
            bag = self.bag
        invalid_nodes: list[tuple[str, BagNode, list[str]]] = []
        self._walk_check(bag, "", invalid_nodes)
        return invalid_nodes

    def _walk_check(
        self,
        bag: Bag,
        path: str,
        invalid_nodes: list[tuple[str, BagNode, list[str]]],
    ) -> None:
        """Walk tree collecting invalid nodes."""
        for node in bag:
            node_path = f"{path}.{node.label}" if path else node.label

            if node._invalid_reasons:
                invalid_nodes.append((node_path, node, node._invalid_reasons.copy()))

            node_value = node.get_value(static=True)
            if isinstance(node_value, Bag):
                self._walk_check(node_value, node_path, invalid_nodes)

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def compile(self, format: str = "xml") -> str:
        """Compile the bag to output format."""
        if format == "xml":
            result = self.bag.to_xml()
            return result if result is not None else ""
        elif format == "json":
            return self.bag.to_json()
        else:
            raise ValueError(f"Unknown format: {format}")

    # -------------------------------------------------------------------------
    # Sub-tags validation (internal)
    # -------------------------------------------------------------------------

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
        """Check if node accepts child_tag as child."""
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
        """Validate list of child tags against sub_tags spec and order."""
        if sub_tags == "":
            return len(tags) == 0

        if sub_tags is None:
            return True

        spec = _parse_sub_tags_spec(sub_tags)
        if not _validate_sub_tags_cardinality(tags, spec):
            return False

        if sub_tags_order:
            order_groups = _parse_sub_tags_order(sub_tags_order)
            if not _validate_sub_tags_order(tags, order_groups):
                return False

        return True

    def _accept_child(
        self, destination_bag: Bag, child_tag: str, node_position: str | int | None = None
    ) -> None:
        """Verify destination accepts child_tag. Raises ValueError if not allowed."""
        parent_node = destination_bag.parent_node
        if parent_node is None:
            return

        schema_node = self._schema.node(parent_node.tag)
        if schema_node is None:
            return

        sub_tags = schema_node.attr.get("sub_tags")
        sub_tags_order = schema_node.attr.get("sub_tags_order")

        if sub_tags is None:
            return

        current_tags = [n.tag for n in destination_bag]
        idx = destination_bag._nodes._parse_position(node_position)
        new_tags = current_tags[:idx] + [child_tag] + current_tags[idx:]

        if not self._validate_sub_tags(sub_tags, sub_tags_order, new_tags):
            raise ValueError(f"'{child_tag}' not allowed as child of '{parent_node.tag}'")

    # -------------------------------------------------------------------------
    # Call args validation (internal)
    # -------------------------------------------------------------------------

    def _get_method(self, tag: str, destination_bag: Bag, kwargs: dict) -> Callable:
        """Get handler method after validation. Raises KeyError if tag not in schema."""
        handler_name, _, call_args_validations = self.get_schema_info(tag)
        self._validate_call_args(kwargs, call_args_validations)
        self._accept_child(destination_bag, tag, kwargs.get("node_position"))
        return getattr(self, handler_name) if handler_name else self._default_element

    def _get_call_args_validations(self, tag: str) -> dict[str, tuple[Any, list, Any]] | None:
        """Return attribute spec for a tag from schema."""
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None
        return schema_node.attr.get("call_args_validations")

    def _validate_call_args(
        self,
        args: dict[str, Any],
        spec: dict[str, tuple[Any, list, Any]] | None,
    ) -> None:
        """Validate type/pattern/range - raise on error."""
        if not spec:
            return

        errors = []

        for attr_name, (base_type, validators, _default) in spec.items():
            value = args.get(attr_name)
            if value is None:
                continue

            if not _check_type(value, base_type):
                errors.append(f"'{attr_name}': expected {base_type}, got {type(value).__name__}")
                continue

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
        """Return list of errors for missing required attrs (SOFT)."""
        errors: list[str] = []
        for attr_name, (_base_type, _validators, default) in spec.items():
            if default is inspect.Parameter.empty and args.get(attr_name) is None:
                errors.append(f"required attribute '{attr_name}' is missing")
        return errors


# =============================================================================
# Type hint parsing utilities (internal)
# =============================================================================


def _split_annotated(tp: Any) -> tuple[Any, list]:
    """Split Annotated type into base type and validators."""
    if get_origin(tp) is Annotated:
        base, *meta = get_args(tp)
        validators = [m for m in meta if callable(m)]
        return base, validators
    return tp, []


def _check_type(value: Any, tp: Any) -> bool:
    """Check if value matches the type annotation."""
    tp, _ = _split_annotated(tp)

    origin = get_origin(tp)
    args = get_args(tp)

    if tp is Any:
        return True

    if tp is type(None):
        return value is None

    if origin is Literal:
        return value in args

    if origin is types.UnionType:
        return any(_check_type(value, t) for t in args)

    try:
        from typing import Union
        if origin is Union:
            return any(_check_type(value, t) for t in args)
    except ImportError:
        pass

    if origin is None:
        try:
            return isinstance(value, tp)
        except TypeError:
            return True

    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    if origin is dict:
        if not isinstance(value, dict):
            return False
        if not args:
            return True
        k_t, v_t = args[0], args[1] if len(args) > 1 else Any
        return all(_check_type(k, k_t) and _check_type(v, v_t) for k, v in value.items())

    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_check_type(v, args[0]) for v in value)
        return len(value) == len(args) and all(
            _check_type(v, t) for v, t in zip(value, args, strict=True)
        )

    if origin is set:
        if not isinstance(value, set):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    try:
        return isinstance(value, origin)
    except TypeError:
        return True


def _extract_validators_from_signature(fn: Callable) -> dict[str, tuple[Any, list, Any]]:
    """Extract type hints with validators from function signature."""
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

        base, validators = _split_annotated(tp)
        result[name] = (base, validators, param.default)

    return result


# =============================================================================
# Sub-tags validation utilities (internal)
# =============================================================================


def _parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int | None]]:
    """Parse sub_tags spec into dict of {tag: (min, max)}."""
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


def _parse_sub_tags_order(order: str) -> list[set[str]]:
    """Parse sub_tags order spec into list of tag groups."""
    result: list[set[str]] = []
    for group in order.split(">"):
        tags = {t.strip() for t in group.split(",") if t.strip()}
        if tags:
            result.append(tags)
    return result


def _validate_sub_tags_cardinality(
    tags: list[str], spec: dict[str, tuple[int, int | None]]
) -> bool:
    """Check tag counts match cardinality constraints."""
    from collections import Counter

    counts = Counter(tags)

    for tag in counts:
        if tag not in spec:
            return False

    for tag, (min_count, max_count) in spec.items():
        count = counts.get(tag, 0)
        if count < min_count:
            return False
        if max_count is not None and count > max_count:
            return False

    return True


def _validate_sub_tags_order(tags: list[str], order_groups: list[set[str]]) -> bool:
    """Check tags respect group ordering."""
    current_group_idx = 0
    for tag in tags:
        tag_group_idx = None
        for i, group in enumerate(order_groups):
            if tag in group:
                tag_group_idx = i
                break

        if tag_group_idx is None:
            continue

        if tag_group_idx < current_group_idx:
            return False

        current_group_idx = tag_group_idx

    return True


# =============================================================================
# Empty body detection (internal)
# =============================================================================


def _ref_empty_body(self): ...


def _ref_empty_body_with_docstring(self):
    """docstring"""
    ...


_EMPTY_BODY_BYTECODE = _ref_empty_body.__code__.co_code
_EMPTY_BODY_DOCSTRING_BYTECODE = _ref_empty_body_with_docstring.__code__.co_code


def _is_empty_body(func: Callable) -> bool:
    """Check if function body is empty (just ... or docstring + ...)."""
    code = func.__code__.co_code
    return code in (_EMPTY_BODY_BYTECODE, _EMPTY_BODY_DOCSTRING_BYTECODE)


def _pop_decorated_methods(cls: type):
    """Remove and yield decorated methods with their info and tags."""
    for name, obj in list(cls.__dict__.items()):
        if hasattr(obj, "_decorator"):
            delattr(cls, name)
            decorator_info = obj._decorator

            if decorator_info.get("abstract"):
                yield [f"@{name}"], None, obj, decorator_info
            else:
                tag_list = [] if name.startswith("_") else [name]
                tags_raw = decorator_info.get("tags")
                if tags_raw:
                    if isinstance(tags_raw, str):
                        tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
                    else:
                        tag_list.extend(tags_raw)
                handler_name = None if _is_empty_body(obj) else f"_el_{tag_list[0]}"
                yield tag_list, handler_name, obj, decorator_info
