# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders.

Provides domain-specific methods for creating nodes in a Bag with
validation support. Adapted from genro-treestore BuilderBase.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


class BagBuilderBase(ABC):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes
    in a Bag. There are two ways to define elements:

    1. Using @element decorator on methods:
        @element(children='item')
        def menu(self, target, tag, **attr):
            return self.child(target, tag, **attr)

        @element(tags='fridge, oven, sink')
        def appliance(self, target, tag, **attr):
            return self.child(target, tag, value='', **attr)

    2. Using _schema dict for external/dynamic definitions:
        class HtmlBuilder(BagBuilderBase):
            _schema = {
                'div': {'children': '=flow'},
                'br': {'leaf': True},
                'td': {
                    'children': '=flow',
                    'attrs': {
                        'colspan': {'type': 'int', 'min': 1, 'default': 1},
                        'rowspan': {'type': 'int', 'min': 0, 'default': 1},
                        'scope': {'type': 'enum', 'values': ['row', 'col']},
                    }
                },
            }

    Schema keys:
        - children: str or set of allowed child tags (supports =ref)
        - leaf: True if element has no children (value='')
        - attrs: dict of attribute specs for validation

    The lookup order is: decorated methods first, then _schema.

    Usage:
        >>> bag = Bag(builder=MyBuilder())
        >>> bag.fridge()  # calls appliance() with tag='fridge'
    """

    _element_tags: dict[str, str]
    _schema: dict[str, dict] = {}

    def _validate_attrs(
        self, tag: str, attrs: dict[str, Any], raise_on_error: bool = True
    ) -> list[str]:
        """Validate attributes against schema specification (pure Python).

        Args:
            tag: The tag name to get attrs spec for.
            attrs: Dict of attribute values to validate.
            raise_on_error: If True, raises ValueError on validation failure.

        Returns:
            List of error messages (empty if valid).
        """
        schema = getattr(self, "_schema", {})
        spec = schema.get(tag, {})
        attrs_spec = spec.get("attrs")

        if not attrs_spec:
            return []

        errors = []

        for attr_name, attr_spec in attrs_spec.items():
            value = attrs.get(attr_name)
            required = attr_spec.get("required", False)
            type_name = attr_spec.get("type", "string")

            if required and value is None:
                errors.append(f"'{attr_name}' is required for '{tag}'")
                continue

            if value is None:
                continue

            if type_name == "int":
                if not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        errors.append(
                            f"'{attr_name}' must be an integer, got {type(value).__name__}"
                        )
                        continue

                min_val = attr_spec.get("min")
                max_val = attr_spec.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"'{attr_name}' must be >= {min_val}, got {value}")
                if max_val is not None and value > max_val:
                    errors.append(f"'{attr_name}' must be <= {max_val}, got {value}")

            elif type_name == "bool":
                if not isinstance(value, bool):
                    if isinstance(value, str):
                        if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                            errors.append(f"'{attr_name}' must be a boolean, got '{value}'")
                    else:
                        errors.append(
                            f"'{attr_name}' must be a boolean, got {type(value).__name__}"
                        )

            elif type_name == "enum":
                values = attr_spec.get("values", [])
                if values and value not in values:
                    errors.append(f"'{attr_name}' must be one of {values}, got '{value}'")

        if errors and raise_on_error:
            raise ValueError(f"Attribute validation failed for '{tag}': " + "; ".join(errors))

        return errors

    def _resolve_ref(self, value: Any) -> Any:
        """Resolve =ref references by looking up _ref_<name> properties.

        References use the = prefix convention:
        - '=flow' -> looks up self._ref_flow property
        - '=phrasing' -> looks up self._ref_phrasing property

        Handles comma-separated strings with mixed refs and literals.
        """
        if isinstance(value, (set, frozenset)):
            resolved = set()
            for item in value:
                resolved_item = self._resolve_ref(item)
                if isinstance(resolved_item, (set, frozenset)):
                    resolved.update(resolved_item)
                elif isinstance(resolved_item, str):
                    resolved.update(t.strip() for t in resolved_item.split(",") if t.strip())
                else:
                    resolved.add(resolved_item)
            return frozenset(resolved) if isinstance(value, frozenset) else resolved

        if not isinstance(value, str):
            return value

        if "," in value:
            parts = [p.strip() for p in value.split(",") if p.strip()]
            resolved_parts = []
            for part in parts:
                resolved_part = self._resolve_ref(part)
                if isinstance(resolved_part, (set, frozenset)):
                    resolved_parts.extend(resolved_part)
                elif isinstance(resolved_part, str):
                    resolved_parts.append(resolved_part)
                else:
                    resolved_parts.append(str(resolved_part))
            return ", ".join(resolved_parts)

        if value.startswith("="):
            ref_name = value[1:]
            prop_name = f"_ref_{ref_name}"

            if hasattr(self, prop_name):
                resolved = getattr(self, prop_name)
                return self._resolve_ref(resolved)

            raise ValueError(
                f"Reference '{value}' not found: no '{prop_name}' property on {type(self).__name__}"
            )

        return value

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build the _element_tags dict from @element decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._element_tags = {}
        for base in cls.__mro__[1:]:
            if hasattr(base, "_element_tags"):
                cls._element_tags.update(base._element_tags)
                break

        for name, method in cls.__dict__.items():
            if name.startswith("_"):
                continue
            if not callable(method):
                continue

            element_tags = getattr(method, "_element_tags", None)
            if element_tags is None and hasattr(method, "_valid_children"):
                cls._element_tags[name] = name
            elif element_tags:
                for tag in element_tags:
                    cls._element_tags[tag] = name

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _element_tags or _schema and return handler."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        element_tags = getattr(type(self), "_element_tags", {})
        if name in element_tags:
            method_name = element_tags[name]
            return getattr(self, method_name)

        schema = getattr(self, "_schema", {})
        if name in schema:
            return self._make_schema_handler(name, schema[name])

        raise AttributeError(f"'{type(self).__name__}' has no element '{name}'")

    def _make_schema_handler(self, tag: str, spec: dict):
        """Create a handler function for a schema-defined element."""
        is_leaf = spec.get("leaf", False)
        builder = self

        def handler(_target, _tag: str = tag, _label: str | None = None, value=None, **attr):
            if value is None and is_leaf:
                value = ""
            return builder.child(_target, _tag, _label=_label, value=value, **attr)

        children_spec = spec.get("children")
        if children_spec is not None:
            handler._raw_children_spec = children_spec
            handler._valid_children, handler._child_cardinality = self._parse_children_spec(
                children_spec
            )
        else:
            handler._valid_children = frozenset()
            handler._child_cardinality = {}

        return handler

    def _parse_children_spec(
        self, spec: str | set | frozenset
    ) -> tuple[frozenset[str], dict[str, tuple[int, int | None]]]:
        """Parse a children spec into validation rules."""
        from .decorators import _parse_tag_spec

        resolved_spec = self._resolve_ref(spec)

        if isinstance(resolved_spec, (set, frozenset)):
            return frozenset(resolved_spec), {}

        parsed: dict[str, tuple[int, int | None]] = {}
        specs = [s.strip() for s in resolved_spec.split(",") if s.strip()]
        for tag_spec in specs:
            tag, min_c, max_c = _parse_tag_spec(tag_spec)
            parsed[tag] = (min_c, max_c)

        return frozenset(parsed.keys()), parsed

    def child(
        self,
        _target: Bag,
        _tag: str,
        _label: str | None = None,
        value: Any = None,
        _position: str | None = None,
        _builder: BagBuilderBase | None = None,
        **attr: Any,
    ) -> Bag | BagNode:
        """Create a child node in the target Bag.

        Args:
            _target: The Bag to add the child to.
            _tag: The node's type (stored in node.tag).
            _label: Explicit label. If None, auto-generated as tag_N.
            value: If provided, creates a leaf node; otherwise creates a branch.
            _position: Position specifier (see Bag.set_item for syntax).
            _builder: Override builder for this branch and its descendants.
            **attr: Node attributes.

        Returns:
            Bag if branch (for adding children), BagNode if leaf.

        Note:
            Parameters use underscore prefix (_target, _tag, _label) to avoid
            clashes with HTML attributes like target='_blank'.
        """
        from ..bag import Bag

        if _label is None:
            n = 0
            while f"{_tag}_{n}" in _target._nodes:
                n += 1
            _label = f"{_tag}_{n}"

        child_builder = _builder if _builder is not None else _target._builder

        if value is not None:
            # Leaf node
            _target.set_item(_label, value, _position=_position, **attr)
            node = _target.get_node(_label)
            node.tag = _tag
            return node
        else:
            # Branch node
            child_bag = Bag(builder=child_builder)
            _target.set_item(_label, child_bag, _position=_position, **attr)
            node = _target.get_node(_label)
            node.tag = _tag
            return child_bag

    def _get_validation_rules(
        self, tag: str | None
    ) -> tuple[frozenset[str] | None, dict[str, tuple[int, int | None]]]:
        """Get validation rules for a tag from decorated methods or schema."""
        if tag is None:
            return None, {}

        element_tags = getattr(type(self), "_element_tags", {})
        if tag in element_tags:
            method_name = element_tags[tag]
            method = getattr(self, method_name, None)
            if method is not None:
                raw_spec = getattr(method, "_raw_children_spec", None)
                if raw_spec is not None:
                    return self._parse_children_spec(raw_spec)
                valid = getattr(method, "_valid_children", None)
                cardinality = getattr(method, "_child_cardinality", {})
                return valid, cardinality

        schema = getattr(self, "_schema", {})
        if tag in schema:
            spec = schema[tag]
            children_spec = spec.get("children")
            if children_spec is not None:
                return self._parse_children_spec(children_spec)
            else:
                return frozenset(), {}

        return None, {}

    def check(self, bag: Bag, parent_tag: str | None = None, path: str = "") -> list[str]:
        """Check the Bag structure against this builder's rules.

        Args:
            bag: The Bag to check.
            parent_tag: The tag of the parent node (for context).
            path: Current path in the tree (for error messages).

        Returns:
            List of error messages (empty if valid).
        """
        from ..bag import Bag

        errors = []
        valid_children, cardinality = self._get_validation_rules(parent_tag)

        child_counts: dict[str, int] = {}
        for node in bag:
            child_tag = node.tag or node.label
            child_counts[child_tag] = child_counts.get(child_tag, 0) + 1

        for node in bag:
            child_tag = node.tag or node.label
            node_path = f"{path}.{node.label}" if path else node.label

            if valid_children is not None and child_tag not in valid_children:
                if valid_children:
                    errors.append(
                        f"'{child_tag}' is not a valid child of '{parent_tag}'. "
                        f"Valid children: {', '.join(sorted(valid_children))}"
                    )
                else:
                    errors.append(
                        f"'{child_tag}' is not a valid child of '{parent_tag}'. "
                        f"'{parent_tag}' cannot have children"
                    )

            node_value = node.get_value(static=True)
            if isinstance(node_value, Bag):
                child_errors = self.check(node_value, parent_tag=child_tag, path=node_path)
                errors.extend(child_errors)

        for tag, (min_count, max_count) in cardinality.items():
            actual = child_counts.get(tag, 0)

            if min_count > 0 and actual < min_count:
                errors.append(
                    f"'{parent_tag}' requires at least {min_count} '{tag}', but has {actual}"
                )
            if max_count is not None and actual > max_count:
                errors.append(
                    f"'{parent_tag}' allows at most {max_count} '{tag}', but has {actual}"
                )

        return errors
