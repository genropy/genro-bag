# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders.

Provides domain-specific methods for creating nodes in a Bag with
validation support.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .validations import (
    BuilderValidationsMixin,
    extract_validators_from_signature,
)

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


def element(
    tags: str | tuple[str, ...] = "",
    sub_tags: str | tuple[str, ...] = "",
    sub_tags_order: str = "",
) -> Callable:
    """Decorator to mark a method as element handler.

    The decorator is a simple marker. All processing (tag parsing, attrs extraction,
    sub_tags spec parsing) happens in __init_subclass__.

    Args:
        tags: Tag names this method handles. Can be:
            - A comma-separated string: 'fridge, oven, sink'
            - A tuple of strings: ('fridge', 'oven', 'sink')
            If empty, the method name is used as the single tag.

        sub_tags: Valid child tags with optional cardinality (order-free). Can be:
            - A comma-separated string: 'tag1,tag2[:1],tag3[1:]'
            - A tuple of strings: ('tag1', 'tag2[:1]', 'tag3[1:]')
            Cardinality syntax:
            - 'tag' - any number of occurrences
            - 'tag[:N]' - at most N occurrences
            - 'tag[N:]' - at least N occurrences
            - 'tag[M:N]' - between M and N occurrences

        sub_tags_order: Optional ordering constraint. Groups separated by '>',
            tags within groups separated by ','. Tags in earlier groups must
            appear before tags in later groups. Tags not in order spec can
            appear anywhere.
            Example: 'header>nav,main,aside>footer'
    """

    def decorator(func: Callable) -> Callable:
        func._decorator = {  # type: ignore[attr-defined]
            "tags": tags,
            "sub_tags": sub_tags,
            "sub_tags_order": sub_tags_order,
        }
        return func

    return decorator


class BagBuilderBase(BuilderValidationsMixin, ABC):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes in a Bag.
    All element definitions are stored in a unified _schema Bag.

    Elements can be defined in two ways:

    1. Using @element decorator on methods:
        @element(sub_tags='item')
        def menu(self, target, tag, **attr):
            return self.child(target, tag, **attr)

        @element(tags='fridge, oven, sink')
        def appliance(self, target, tag, **attr):
            return self.child(target, tag, value='', **attr)

    2. Building _schema programmatically (e.g., from XSD):
        _schema = Bag()
        _schema.set_item('div', sub_tags_bag, handler='_el_generic')
        _schema.set_item('br', None, leaf=True)

    Schema structure (unified for both approaches):
        _schema is a Bag where each node represents an element:
        - node.label = element name
        - node.value = Bag of ordered sub_tags (None for leaf/no sub_tags spec)
        - node.attr = {
            handler: str (method name, e.g. '_el_foo'),
            sub_tags: str (allowed sub_tags with cardinality, e.g. 'item,section[:1]'),
            sub_tags_order: str (ordering constraint, e.g. 'header>body>footer'),
            call_args_validations: dict (attribute validation),
            leaf: bool (element has no sub_tags),
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
        return type(self)._schema.node(name) is not None

    def get_schema_info(self, name: str) -> tuple[str | None, str | None, dict | None]:
        """Return schema info for an element.

        Args:
            name: Element name to look up.

        Returns:
            Tuple of (handler, sub_tags, call_args_validations).

        Raises:
            KeyError: If element not found in schema.
        """
        schema_node = type(self)._schema.node(name)
        if schema_node is None:
            raise KeyError(f"Element '{name}' not found in schema")
        return (
            schema_node.attr.get("handler"),
            schema_node.attr.get("sub_tags"),
            schema_node.attr.get("call_args_validations"),
        )

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
            sub_tags_bag = node.get_value(static=True)
            is_leaf = node.attr.get("leaf", False)
            if is_leaf:
                lines.append(f"  {element} (leaf)")
            elif sub_tags_bag:
                sub_tag_names = ", ".join(n.label for n in sub_tags_bag)
                lines.append(f"  {element} -> [{sub_tag_names}]")
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

            # Extract call_args_validations from signature
            call_args_validations = extract_validators_from_signature(obj)

            # Get sub_tags spec (raw, will resolve refs at runtime)
            sub_tags_raw = decorator_info.get("sub_tags", "")
            sub_tags_order_raw = decorator_info.get("sub_tags_order", "")

            # Create entry in _schema for each tag
            for tag in tag_list:
                cls._schema.set_item(
                    tag,
                    None,  # sub_tags_bag populated later if needed
                    handler=new_name,
                    sub_tags=sub_tags_raw,
                    sub_tags_order=sub_tags_order_raw,
                    call_args_validations=call_args_validations,
                )

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
        """Create a child node in the target Bag.

        Args:
            _target: The Bag to add the child to.
            _tag: The node's type (stored in node.tag).
            node_label: Explicit label. If None, auto-generated as tag_N.
            value: If provided, creates a leaf node; otherwise creates a branch with empty Bag.
            node_position: Position specifier (see Bag.set_item for syntax).
            **attr: Node attributes.

        Returns:
            Always returns BagNode. For branches, the Bag is created lazily when
            children are added via _command_on_node().

        Note:
            _target and _tag use underscore prefix to avoid clashes with
            HTML attributes like target='_blank'.

            Validation of parent-child relationships is handled by _command_on_node()
            using _can_add_child() with regex patterns.
        """
        if node_label is None:
            n = 0
            while f"{_tag}_{n}" in _target._nodes:
                n += 1
            node_label = f"{_tag}_{n}"

        # Create node with provided value (or None for potential branch)
        node = _target.set_item(node_label, value, _position=node_position, **attr)
        node.tag = _tag

        return node

    def _command_on_node(
        self, node: BagNode, child_tag: str, node_position: str | int | None = None, **attrs: Any
    ) -> BagNode:
        """Add a child to a node with STRICT/SOFT validation.

        Called by BagNode.__getattr__ when builder is attached.

        STRICT validation (raises immediately):
        - Child not allowed by parent's children pattern
        - Wrong attribute type
        - Attribute pattern mismatch
        - Attribute value out of range

        SOFT validation (annotates in _invalid_reasons):
        - Required attribute missing
        - Minimum cardinality not met (after insert)

        Args:
            node: The parent BagNode
            child_tag: Tag of the child to add
            node_position: Insertion position
            **attrs: Attributes for the child

        Returns:
            The created child BagNode (may have _invalid_reasons populated)

        Raises:
            ValueError: If child_tag is not allowed under node (STRICT)
            TypeError: If attribute has wrong type (STRICT)
        """
        from ..bag import Bag

        # 1) STRICT: Verify child allowed by parent pattern
        if not self._can_add_child(node, child_tag, node_position=node_position):
            pattern = self._sub_tags_validation_pattern(node)
            raise ValueError(
                f"'{child_tag}' not allowed as child of '{node.tag}' (pattern: {pattern!r})"
            )

        # 2) Validate attribute types and patterns
        call_args_validations = self._get_call_args_validations(child_tag)
        self._validate_call_args(attrs, call_args_validations)

        # 3) Create Bag lazily if needed
        if not isinstance(node.value, Bag):
            node.value = Bag()
            node.value._builder = self

        # 4) Create child node
        child_node = self.child(node.value, child_tag, node_position=node_position, **attrs)

        # 5) SOFT: Check required attrs missing
        if call_args_validations:
            soft_errors = self._check_required_attrs(attrs, call_args_validations)
            child_node._invalid_reasons.extend(soft_errors)

        return child_node

    def check(self, bag: Bag | None = None) -> list[tuple[str, BagNode, list[str]]]:
        """Return report of invalid nodes.

        Walks the Bag tree and collects nodes with non-empty _invalid_reasons.
        Does NOT perform validation - just inspects existing errors that were
        annotated during node creation.

        Args:
            bag: The Bag to check. If None, uses self.bag.

        Returns:
            List of (path, node, reasons) tuples for each invalid node.
        """
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
        from ..bag import Bag

        for node in bag:
            node_path = f"{path}.{node.label}" if path else node.label

            if node._invalid_reasons:
                invalid_nodes.append((node_path, node, node._invalid_reasons.copy()))

            node_value = node.get_value(static=True)
            if isinstance(node_value, Bag):
                self._walk_check(node_value, node_path, invalid_nodes)

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
