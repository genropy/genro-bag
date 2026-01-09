# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders.

Provides domain-specific methods for creating nodes in a Bag with
validation support.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .validations import extract_attrs_from_signature, parse_tag_spec, validate_call_args

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


def element(
    tags: str | tuple[str, ...] = "",
    children: str | tuple[str, ...] = "",
) -> Callable:
    """Decorator to mark a method as element handler.

    The decorator is a simple marker. All processing (tag parsing, attrs extraction,
    children spec parsing) happens in __init_subclass__.

    Args:
        tags: Tag names this method handles. Can be:
            - A comma-separated string: 'fridge, oven, sink'
            - A tuple of strings: ('fridge', 'oven', 'sink')
            If empty, the method name is used as the single tag.

        children: Valid child tag specs for structure validation. Can be:
            - A comma-separated string: 'tag1, tag2[:1], tag3[1:]'
            - A tuple of strings: ('tag1', 'tag2[:1]', 'tag3[1:]')
    """

    def decorator(func: Callable) -> Callable:
        func._decorator = {"tags": tags, "children_spec": children}  # type: ignore[attr-defined]
        return func

    return decorator


class BagBuilderBase(ABC):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes in a Bag.
    All element definitions are stored in a unified _schema Bag.

    Elements can be defined in two ways:

    1. Using @element decorator on methods:
        @element(children='item')
        def menu(self, target, tag, **attr):
            return self.child(target, tag, **attr)

        @element(tags='fridge, oven, sink')
        def appliance(self, target, tag, **attr):
            return self.child(target, tag, value='', **attr)

    2. Building _schema programmatically (e.g., from XSD):
        _schema = Bag()
        _schema.set_item('div', children_bag, handler='_el_generic')
        _schema.set_item('br', None, leaf=True)

    Schema structure (unified for both approaches):
        _schema is a Bag where each node represents an element:
        - node.label = element name
        - node.value = Bag of ordered children (None for leaf/no children spec)
        - node.attr = {
            handler: str (method name, e.g. '_el_foo'),
            children_spec: str (raw spec like 'item, section[:1]'),
            attrs_spec: dict (attribute validation),
            leaf: bool (element has no children),
            attrs: dict (for XSD-style validation)
          }

    Usage:
        >>> bag = Bag(builder=MyBuilder)
        >>> bag.fridge()  # looks up 'fridge' in _schema, calls handler
    """

    _schema: Bag  # type: ignore[assignment]

    def __init__(self, bag: Bag) -> None:
        """Initialize builder with its Bag."""
        self.bag = bag
        self.bag.set_backref()

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema. Supports 'name in builder'."""
        schema = getattr(type(self), "_schema", None)
        if schema is None:
            return False
        return schema.node(name) is not None

    def __iter__(self):
        """Iterate over element names in schema."""
        schema = getattr(type(self), "_schema", None)
        if schema is None:
            return iter([])
        return (node.label for node in schema)

    def __repr__(self) -> str:
        """Show builder schema summary."""
        schema = getattr(type(self), "_schema", None)
        if schema is None:
            return f"<{type(self).__name__} (no schema)>"
        return f"<{type(self).__name__} ({len(schema)} elements)>"

    def __str__(self) -> str:
        """Show detailed schema structure."""
        schema = getattr(type(self), "_schema", None)
        if schema is None:
            return f"{type(self).__name__}: no schema"

        lines = [f"{type(self).__name__} schema:"]
        for element in self:
            node = schema.node(element)
            children = node.get_value(static=True)
            is_leaf = node.attr.get("leaf", False)
            if is_leaf:
                lines.append(f"  {element} (leaf)")
            elif children:
                child_names = ", ".join(n.label for n in children)
                lines.append(f"  {element} -> [{child_names}]")
            else:
                lines.append(f"  {element}")
        return "\n".join(lines)

    def _resolve_ref(self, value: Any) -> Any:
        """Resolve =ref references by looking up _ref_<name> properties.

        References use the = prefix convention:
        - '=flow' -> looks up self._ref_flow property
        - '=phrasing' -> looks up self._ref_phrasing property

        Handles comma-separated strings with mixed refs and literals.
        """
        if isinstance(value, (set, frozenset)):
            resolved: set[Any] = set()
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
            resolved_parts: list[str] = []
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
        """Build _schema Bag from @element decorated methods."""
        from ..bag import Bag as BagClass

        super().__init_subclass__(**kwargs)

        # Create new _schema, inheriting from base if present
        cls._schema = BagClass()
        for base in cls.__mro__[1:]:
            if hasattr(base, "_schema") and base._schema is not None:
                # Copy nodes from parent schema
                for node in base._schema:
                    if cls._schema.node(node.label) is None:
                        cls._schema.set_item(
                            node.label,
                            node.get_value(static=True),
                            **node.attr
                        )
                break

        # Process decorated methods
        for name, obj in list(cls.__dict__.items()):
            decorator_info = getattr(obj, "_decorator", None)
            if not decorator_info:
                continue

            # Rename method: foo -> _el_foo
            new_name = f"_el_{name}"
            setattr(cls, new_name, obj)
            delattr(cls, name)

            # Parse tags
            tags_raw = decorator_info.get("tags", "")
            if isinstance(tags_raw, str):
                tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            else:
                tag_list = list(tags_raw) if tags_raw else []
            if not tag_list:
                tag_list = [name]

            # Extract attrs_spec from signature
            attrs_spec = extract_attrs_from_signature(obj)

            # Parse children_spec (raw, will resolve refs at runtime)
            children_raw = decorator_info.get("children_spec", "")

            # Create entry in _schema for each tag
            for tag in tag_list:
                cls._schema.set_item(
                    tag,
                    None,  # children_bag populated later if needed
                    handler=new_name,
                    children_spec=children_raw,
                    attrs_spec=attrs_spec,
                )

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _schema and return handler with validation."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        schema = getattr(type(self), "_schema", None)
        if schema is None:
            raise AttributeError(f"'{type(self).__name__}' has no element '{name}'")

        schema_node = schema.node(name)
        if schema_node is None:
            raise AttributeError(f"'{type(self).__name__}' has no element '{name}'")

        # Check if this element has a handler method (from @element decorator)
        handler_name = schema_node.attr.get("handler")
        if handler_name:
            attrs_spec = schema_node.attr.get("attrs_spec")
            method = getattr(self, handler_name)

            if attrs_spec:
                def wrapper(*args: Any, _tag: str = name, **kwargs: Any) -> Any:
                    validate_call_args(kwargs, attrs_spec)
                    kwargs["tag"] = _tag
                    return method(*args, **kwargs)
                return wrapper
            else:
                def simple_wrapper(*args: Any, _tag: str = name, **kwargs: Any) -> Any:
                    kwargs["tag"] = _tag
                    return method(*args, **kwargs)
                return simple_wrapper

        # No handler - create child directly from schema node (XSD-style)
        return self._create_child_from_node(name, schema_node)

    def _create_child_from_node(self, tag: str, schema_node: BagNode):
        """Create a child node using schema BagNode."""
        is_leaf = schema_node.attr.get("leaf", False)
        attrs_spec = schema_node.attr.get("attrs")
        children_bag = schema_node.get_value(static=True)
        builder = self

        def handler(_target, _tag: str = tag, node_label: str | None = None, value=None, **attr):
            if attrs_spec:
                validate_call_args(attr, attrs_spec)
                # Validate value content if spec has 'value' key (XSD text content)
                if "value" in attrs_spec and value is not None:
                    validate_call_args({"value": value}, {"value": attrs_spec["value"]})
            if value is None and is_leaf:
                value = ""
            return builder.child(_target, _tag, node_label=node_label, value=value, **attr)

        if children_bag is not None:
            valid = frozenset(node.label for node in children_bag)
            handler._valid_children = valid  # type: ignore[attr-defined]
            handler._child_cardinality = {}  # type: ignore[attr-defined]
        else:
            handler._valid_children = frozenset()  # type: ignore[attr-defined]
            handler._child_cardinality = {}  # type: ignore[attr-defined]

        return handler

    def _parse_children_spec(
        self, spec: str | set | frozenset
    ) -> tuple[frozenset[str], dict[str, tuple[int, int | None]]]:
        """Parse a children spec into validation rules."""
        resolved_spec = self._resolve_ref(spec)

        if isinstance(resolved_spec, (set, frozenset)):
            return frozenset(resolved_spec), {}

        parsed: dict[str, tuple[int, int | None]] = {}
        specs = [s.strip() for s in resolved_spec.split(",") if s.strip()]
        for tag_spec in specs:
            tag, min_c, max_c = parse_tag_spec(tag_spec)
            parsed[tag] = (min_c, max_c)

        return frozenset(parsed.keys()), parsed

    def child(
        self,
        _target: Bag,
        _tag: str,
        node_label: str | None = None,
        value: Any = None,
        node_position: str | None = None,
        node_builder: BagBuilderBase | None = None,
        **attr: Any,
    ) -> Bag | BagNode:
        """Create a child node in the target Bag.

        Args:
            _target: The Bag to add the child to.
            _tag: The node's type (stored in node.tag).
            node_label: Explicit label. If None, auto-generated as tag_N.
            value: If provided, creates a leaf node; otherwise creates a branch.
            node_position: Position specifier (see Bag.set_item for syntax).
            node_builder: Override builder for this branch and its descendants.
            **attr: Node attributes.

        Returns:
            Bag if branch (for adding children), BagNode if leaf.

        Note:
            _target and _tag use underscore prefix to avoid clashes with
            HTML attributes like target='_blank'.
        """
        from ..bag import Bag

        # Step 1: Pre-add - verify parent accepts this child
        parent_node = _target.parent_node
        if parent_node is not None:
            self._accepts_child(parent_node, _tag)

        if node_label is None:
            n = 0
            while f"{_tag}_{n}" in _target._nodes:
                n += 1
            node_label = f"{_tag}_{n}"

        child_builder = node_builder if node_builder is not None else _target._builder

        if value is not None:
            # Leaf node
            node = _target.set_item(node_label, value, _position=node_position, **attr)
            node.tag = _tag
            return node

        # Branch node
        child_bag = Bag(builder=child_builder)
        node = _target.set_item(node_label, child_bag, _position=node_position, **attr)
        node.tag = _tag
        return child_bag

    def _get_validation_rules(
        self, tag: str | None
    ) -> tuple[frozenset[str] | None, dict[str, tuple[int, int | None]]]:
        """Get validation rules for a tag from _schema."""
        if tag is None:
            return None, {}

        schema = getattr(type(self), "_schema", None)
        if schema is None:
            return None, {}

        schema_node = schema.node(tag)
        if schema_node is None:
            return None, {}

        # Check for children_spec string (from @element decorator)
        children_spec = schema_node.attr.get("children_spec")
        if children_spec:
            return self._parse_children_spec(children_spec)

        # Check for children Bag (from XSD or programmatic schema)
        children_bag = schema_node.get_value(static=True)
        if children_bag is not None:
            return frozenset(node.label for node in children_bag), {}

        # Element exists but has no children spec - leaf element
        return frozenset(), {}

    def _accepts_child(self, parent_node: BagNode, child_tag: str) -> None:
        """Verify that parent accepts child_tag. Raises ValueError if not.

        Args:
            parent_node: The parent BagNode.
            child_tag: Tag of the child to add.

        Raises:
            ValueError: If child_tag is not allowed under parent.
        """
        parent_tag = parent_node.tag
        if parent_tag is None:
            return  # Parent has no tag - no validation

        valid_children, _ = self._get_validation_rules(parent_tag)

        if valid_children is None:
            return  # Unknown parent tag - no validation

        if not valid_children:
            raise ValueError(
                f"'{parent_tag}' cannot have children, but got '{child_tag}'"
            )

        if child_tag not in valid_children:
            raise ValueError(
                f"'{child_tag}' is not a valid child of '{parent_tag}'. "
                f"Valid children: {', '.join(sorted(valid_children))}"
            )

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

    def compile(self, format: str = "xml") -> str:
        """Compile the bag to output format.

        Override in subclasses for custom output formats (HTML, SEPA XML, etc.).

        Args:
            format: Output format. Default supports 'xml' and 'json'.

        Returns:
            String representation in the requested format.

        Raises:
            ValueError: If format is not supported.
        """
        if format == "xml":
            result = self.bag.to_xml()
            return result if result is not None else ""
        elif format == "json":
            return self.bag.to_json()
        else:
            raise ValueError(f"Unknown format: {format}")
