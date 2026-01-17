# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders with validation.

Provides domain-specific methods for creating nodes in a Bag with
validation support.

Exports:
    element: Decorator to mark methods as element handlers
    abstract: Decorator to define abstract elements (for inheritance only)
    BagBuilderBase: Abstract base class for all builders
    SchemaBuilder: Builder for creating schemas programmatically
    Regex: Regex pattern constraint for string validation
    Range: Range constraint for numeric validation

Schema conventions:
    - Elements stored by name: 'div', 'span'
    - Abstracts prefixed with '@': '@flow', '@phrasing'
    - Use inherits_from='@abstract' to inherit sub_tags

compile_* parameters:
    Both @element and @abstract support compile_* parameters for code generation.
    Parameters can be passed as:
    - compile_kwargs dict: compile_kwargs={'module': 'x', 'class': 'Y'}
    - Individual kwargs: compile_module='x', compile_class='Y'
    - Mixed: both approaches are merged (individual kwargs override dict)

    When using inherits_from, compile_kwargs are inherited from the abstract
    and merged with the element's own compile_kwargs (element overrides abstract).

    Example:
        @abstract(sub_tags='child', compile_module='textual.containers')
        def base_container(self): ...

        @element(inherits_from='@base_container', compile_class='Vertical')
        def vertical(self): ...
        # Result: compile_kwargs = {'module': 'textual.containers', 'class': 'Vertical'}

sub_tags cardinality syntax:
    foo      -> any number (0..N)
    foo[1]   -> exactly 1
    foo[3]   -> exactly 3
    foo[0:]  -> 0 or more
    foo[:2]  -> 0 to 2
    foo[1:3] -> 1 to 3

Constraint classes for use with Annotated:
    Regex: regex pattern for strings
    Range: min/max value constraints for numbers (ge, le, gt, lt)

Type hints supported:
    - Basic types: int, str, bool, float, Decimal
    - Literal['a', 'b'] for enum-like constraints
    - list[T], dict[K, V], tuple[...], set[T] for generics
    - X | None for optional
    - Annotated[T, validator...] for validators

SchemaBuilder Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builder import SchemaBuilder
    >>>
    >>> schema = Bag(builder=SchemaBuilder)
    >>> schema.item('@container', sub_tags='child', compile_module='textual.containers')
    >>> schema.item('vertical', inherits_from='@container', compile_class='Vertical')
    >>> schema.item('br', sub_tags='')  # void element
    >>> schema.builder.compile('schema.msgpack')
"""

from __future__ import annotations

import inspect
import re
import sys
import types
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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
    inherits_from: str | None = None,
    compile_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator to mark a method as element handler.

    Args:
        tags: Tag names this method handles. If None, uses method name.
        sub_tags: Valid child tags with cardinality. Syntax:
            'a,b,c'     -> a, b, c each exactly once
            'a[],b[]'   -> a and b any number of times
            'a[2],b[0:]' -> a exactly twice, b zero or more
            '' (empty)  -> no children allowed (void element)
        inherits_from: Abstract element name to inherit sub_tags from.
        compile_kwargs: Dict of compilation parameters (module, class, etc.).
        **kwargs: Additional compile_* parameters are extracted and merged
            into compile_kwargs. E.g., compile_module='x' -> {'module': 'x'}.

    Example:
        @element(sub_tags='header,content[],footer')
        def page(self): ...

        @element(
            sub_tags='child',
            compile_kwargs={'module': 'textual.containers'},
            compile_class='Vertical',  # merged into compile_kwargs
        )
        def container(self): ...
    """
    # Extract compile_* from kwargs and merge with compile_kwargs
    merged_compile = dict(compile_kwargs) if compile_kwargs else {}
    for key, value in kwargs.items():
        if key.startswith("compile_"):
            merged_compile[key[8:]] = value  # strip "compile_" prefix

    def decorator(func: Callable) -> Callable:
        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "tags": tags,
                "sub_tags": sub_tags,
                "inherits_from": inherits_from,
                "compile_kwargs": merged_compile if merged_compile else None,
            }.items()
            if v is not None
        }
        return func

    return decorator


def abstract(
    sub_tags: str | tuple[str, ...] = "",
    compile_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator to define an abstract element (for inheritance only).

    Abstract elements are stored with '@' prefix and cannot be instantiated.
    They define sub_tags that can be inherited by concrete elements.

    Args:
        sub_tags: Valid child tags with cardinality (see element decorator).
        compile_kwargs: Dict of compilation parameters (module, class, etc.).
        **kwargs: Additional compile_* parameters are extracted and merged
            into compile_kwargs. E.g., compile_module='x' -> {'module': 'x'}.

    Example:
        @abstract(sub_tags='span,a,em,strong')
        def phrasing(self): ...

        @element(inherits_from='@phrasing')
        def p(self): ...

        @abstract(
            sub_tags='child',
            compile_module='textual.containers',
        )
        def base_container(self): ...
    """
    # Extract compile_* from kwargs and merge with compile_kwargs
    merged_compile = dict(compile_kwargs) if compile_kwargs else {}
    for key, value in kwargs.items():
        if key.startswith("compile_"):
            merged_compile[key[8:]] = value  # strip "compile_" prefix

    def decorator(func: Callable) -> Callable:
        result: dict[str, Any] = {
            "abstract": True,
            "sub_tags": sub_tags,
        }
        if merged_compile:
            result["compile_kwargs"] = merged_compile
        func._decorator = result  # type: ignore[attr-defined]
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
    Each instance has its own _schema Bag (instance-level, not class-level).

    Schema conventions:
        - Elements: stored directly by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Abstracts define sub_tags for inheritance, cannot be used directly

    Schema loading priority:
        1. schema_path passed to constructor (builder_schema_path='...')
        2. schema_path class attribute
        3. @element decorated methods

    Usage:
        >>> bag = Bag(builder=MyBuilder)
        >>> bag.div()  # looks up 'div' in _schema, calls handler
        >>> # With custom schema:
        >>> bag = Bag(builder=MyBuilder, builder_schema_path='custom.bag.mp')
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    schema_path: str | Path | None = None  # Default schema path (class attribute)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from @element decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._class_schema = Bag().fill_from(getattr(cls, "schema_path", None))

        for tag_list, handler_name, obj, decorator_info in _pop_decorated_methods(cls):
            if handler_name:
                setattr(cls, handler_name, obj)

            sub_tags = decorator_info.get("sub_tags", "")
            inherits_from = decorator_info.get("inherits_from", "")
            compile_kwargs = decorator_info.get("compile_kwargs")
            documentation = obj.__doc__
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                cls._class_schema.set_item(
                    tag,
                    None,
                    handler_name=handler_name,
                    sub_tags=sub_tags,
                    inherits_from=inherits_from,
                    compile_kwargs=compile_kwargs,
                    documentation=documentation,
                    call_args_validations=call_args_validations,
                )

    def __init__(self, bag: Bag, schema_path: str | Path | None = None) -> None:
        """Bind builder to bag. Enables node.parent navigation.

        Args:
            bag: The Bag instance this builder is attached to.
            schema_path: Optional path to load schema from. If not provided,
                uses the class-level schema (_class_schema).
        """
        self.bag = bag
        self.bag.set_backref()

        if schema_path is not None:
            self._schema = Bag().fill_from(schema_path)
        else:
            self._schema = type(self)._class_schema

    # -------------------------------------------------------------------------
    # Element dispatch
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _schema and return handler with validation."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def wrapper(destination_bag: Bag, *args: Any, node_tag: str = name, **kwargs: Any) -> Any:
            try:
                method = self._get_method(node_tag)
            except KeyError as err:
                raise AttributeError(f"'{type(self).__name__}' has no element '{node_tag}'") from err
            kwargs["node_tag"] = node_tag
            return method(destination_bag, *args, **kwargs)

        return wrapper

    def _default_element(
        self,
        build_where: Bag,
        node_value: Any = None,
        node_label: str | None = None,
        node_tag: str = "",
        **attr: Any,
    ) -> BagNode:
        """Default handler for elements without custom handler.

        Args:
            build_where: The destination Bag where the node will be created.
            node_value: Node content (positional). Becomes node.value.
            node_label: Optional explicit label for the node.
            node_tag: The tag name for the element (passed via kwargs).
            **attr: Node attributes.
        """
        return self.child(build_where, node_tag, node_value, node_label=node_label, **attr)

    def child(
        self,
        build_where: Bag,
        node_tag: str,
        node_value: Any = None,
        node_label: str | None = None,
        node_position: str | int | None = None,
        **attr: Any,
    ) -> BagNode:
        """Create a child node in the target Bag with validation.

        Raises ValueError if validation fails, KeyError if parent tag not in schema.
        """
        parent_node = build_where._parent_node
        if parent_node and parent_node.tag:
            parent_info = self.get_schema_info(parent_node.tag)
            self._accept_child(parent_node, parent_info, node_tag, node_position)

        child_info = self.get_schema_info(node_tag)
        self._validate_call_args(child_info, node_value, attr)

        node_label = node_label or self._auto_label(build_where, node_tag)
        child_node = build_where.set_item(node_label, node_value, node_position=node_position, **attr)
        child_node.tag = node_tag

        if parent_node:
            self._validate_sub_tags(parent_node, parent_info)

        self._validate_sub_tags(child_node, child_info)

        return child_node

    def _auto_label(self, build_where: Bag, node_tag: str) -> str:
        """Generate unique label for a node: tag_0, tag_1, ..."""
        n = 0
        while f"{node_tag}_{n}" in build_where._nodes:
            n += 1
        return f"{node_tag}_{n}"

    def _validate_call_args(
        self,
        info: dict,
        node_value: Any,
        attr: dict[str, Any],
    ) -> None:
        """Validate attributes and node_value. Raises ValueError if invalid."""
        call_args_validations = info.get("call_args_validations")
        if not call_args_validations:
            return

        errors: list[str] = []
        all_args = dict(attr)
        if node_value is not None:
            all_args["node_value"] = node_value

        for attr_name, (base_type, validators, default) in call_args_validations.items():
            attr_value = all_args.get(attr_name)

            # Required check
            if default is inspect.Parameter.empty and attr_value is None:
                errors.append(f"required attribute '{attr_name}' is missing")
                continue

            if attr_value is None:
                continue

            # Type check
            if not _check_type(attr_value, base_type):
                errors.append(
                    f"'{attr_name}': expected {base_type}, got {type(attr_value).__name__}"
                )
                continue

            # Validator checks (Regex, Range, etc.)
            for v in validators:
                try:
                    v(attr_value)
                except Exception as e:
                    errors.append(f"'{attr_name}': {e}")

        if errors:
            raise ValueError("Validation failed: " + "; ".join(errors))

    def _validate_children_tags(
        self,
        node_tag: str,
        sub_tags_compiled: dict[str, tuple[int, int]],
        children_tags: list[str],
    ) -> list[str]:
        """Validate a list of child tags against sub_tags spec.

        Args:
            node_tag: Tag of parent node (for error messages)
            sub_tags_compiled: Compiled sub_tags dict {tag: (min, max)}
            children_tags: List of child tags to validate

        Returns:
            List of invalid_reasons (missing required tags)

        Raises:
            ValueError: if tag not allowed or max exceeded
        """
        bounds = {tag: list(minmax) for tag, minmax in sub_tags_compiled.items()}
        for tag in children_tags:
            minmax = bounds.get(tag)
            if minmax is None:
                raise ValueError(f"'{tag}' not allowed as child of '{node_tag}'")
            minmax[1] -= 1
            if minmax[1] < 0:
                raise ValueError(f"Too many '{tag}' in '{node_tag}'")
            minmax[0] -= 1

        # Warnings for missing required elements (min > 0 after decrement)
        return [tag for tag, (n_min, _) in bounds.items() if n_min > 0]

    def _validate_sub_tags(self, node: BagNode, info: dict) -> None:
        """Validate sub_tags constraints on node's existing children.

        Gets children_tags from node's actual children, calls _validate_children_tags,
        and sets node._invalid_reasons.

        Args:
            node: The node to validate.
            info: Schema info dict from get_schema_info().
        """
        node_tag = node.tag
        if not node_tag:
            node._invalid_reasons = []
            return

        sub_tags_compiled = info.get("sub_tags_compiled")
        if sub_tags_compiled is None:
            node._invalid_reasons = []
            return

        children_tags = [n.tag for n in node.value.nodes] if isinstance(node.value, Bag) else []

        node._invalid_reasons = self._validate_children_tags(
            node_tag, sub_tags_compiled, children_tags  # type: ignore[arg-type]
        )

    def _accept_child(
        self,
        target_node: BagNode,
        info: dict,
        child_tag: str,
        node_position: str | int | None,
    ) -> None:
        """Check if target_node can accept child_tag at node_position.

        Builds children_tags = current tags + new tag, calls _validate_children_tags.
        Raises ValueError if not valid.
        """
        sub_tags_compiled = info.get("sub_tags_compiled")
        if sub_tags_compiled is None:
            return

        # Build children_tags = current + new
        children_tags = (
            [n.tag for n in target_node.value.nodes] if isinstance(target_node.value, Bag) else []
        )

        # Insert new tag at correct position
        idx = (
            target_node.value._nodes._parse_position(node_position)
            if isinstance(target_node.value, Bag)
            else 0
        )
        children_tags.insert(idx, child_tag)

        self._validate_children_tags(target_node.tag, sub_tags_compiled, children_tags)  # type: ignore[arg-type]

    def _command_on_node(
        self, node: BagNode, child_tag: str, node_position: str | int | None = None, **attrs: Any
    ) -> BagNode:
        """Add a child to a node. Validation is delegated to child()."""
        if not isinstance(node.value, Bag):
            node.value = Bag()
            node.value.builder = self

        return self.child(node.value, child_tag, node_position=node_position, **attrs)

    # -------------------------------------------------------------------------
    # Schema access
    # -------------------------------------------------------------------------

    @property
    def schema(self) -> Bag:
        """Return the instance schema."""
        return self._schema

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema."""
        return self.schema.get_node(name) is not None

    def get_schema_info(self, name: str) -> dict:
        """Return info dict for an element.

        Returns dict with keys:
            - handler_name: str | None
            - sub_tags: str | None
            - sub_tags_compiled: dict[str, tuple[int, int]] | None
            - call_args_validations: dict | None

        Raises KeyError if element not in schema.
        """
        schema_node = self.schema.get_node(name)
        if schema_node is None:
            raise KeyError(f"Element '{name}' not found in schema")

        cached = schema_node.attr.get("_cached_info")  # type: ignore[union-attr]
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        result = dict(schema_node.attr)  # type: ignore[union-attr]
        inherits_from = result.pop("inherits_from", None)

        if inherits_from:
            abstract_attrs = self.schema.get_attr(inherits_from)
            if abstract_attrs:
                for k, v in abstract_attrs.items():
                    if k == "compile_kwargs":
                        # Merge compile_kwargs: abstract base + element overrides
                        inherited = v or {}
                        current = result.get("compile_kwargs") or {}
                        result["compile_kwargs"] = {**inherited, **current}
                    elif k not in result or not result[k]:
                        result[k] = v

        sub_tags = result.get("sub_tags")
        if sub_tags is not None:
            result["sub_tags_compiled"] = _parse_sub_tags_spec(sub_tags)

        schema_node.attr["_cached_info"] = result  # type: ignore[union-attr]
        return result

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

    def compile(self, *args: Any, **kwargs: Any) -> Any:
        """Compile the bag to output format.

        This is a base implementation that subclasses can override.
        Return type varies by builder (str, Iterator, bytes, None, etc.).
        """
        format = kwargs.get("format", "xml")
        if format == "xml":
            result = self.bag.to_xml()
            return result if result is not None else ""
        if format == "json":
            return self.bag.to_json()
        raise ValueError(f"Unknown format: {format}")

    # -------------------------------------------------------------------------
    # Schema documentation
    # -------------------------------------------------------------------------

    def schema_to_md(self, title: str | None = None) -> str:
        """Generate Markdown documentation for the builder schema.

        Creates a formatted Markdown document with tables for abstract
        and concrete elements, including all schema information.

        Args:
            title: Optional title for the document. Defaults to class name.

        Returns:
            Markdown string with schema documentation.
        """
        from .builders.markdown import MarkdownBuilder

        doc = Bag(builder=MarkdownBuilder)
        builder_name = title or type(self).__name__

        doc.h1(f"Schema: {builder_name}")

        # Collect abstracts and elements
        abstracts: list[tuple[str, dict]] = []
        elements: list[tuple[str, dict]] = []

        for node in self.schema:
            name = node.label
            info = self.get_schema_info(name)
            if name.startswith("@"):
                abstracts.append((name[1:], info))
            else:
                elements.append((name, info))

        # Abstract elements section
        if abstracts:
            doc.h2("Abstract Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Sub Tags")
            header.th("Documentation")

            for name, info in sorted(abstracts):
                row = table.tr()
                row.td(f"`@{name}`")
                row.td(f"`{info.get('sub_tags') or '-'}`")
                row.td(info.get("documentation") or "-")

        # Concrete elements section
        if elements:
            doc.h2("Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Inherits")
            header.th("Sub Tags")
            header.th("Call Args")
            header.th("Compile")
            header.th("Documentation")

            for name, info in sorted(elements):
                row = table.tr()
                row.td(f"`{name}`")

                inherits = info.get("inherits_from")
                row.td(f"`{inherits}`" if inherits else "-")

                sub_tags = info.get("sub_tags")
                row.td(f"`{sub_tags}`" if sub_tags else "-")

                call_args = info.get("call_args_validations")
                if call_args:
                    args_str = ", ".join(call_args.keys())
                    row.td(f"`{args_str}`")
                else:
                    row.td("-")

                compile_kwargs = info.get("compile_kwargs") or {}
                compile_parts = []
                if "template" in compile_kwargs:
                    # Escape backticks in template for markdown display
                    tmpl = compile_kwargs["template"].replace("`", "\\`")
                    tmpl = tmpl.replace("\n", "\\n")
                    compile_parts.append(f"template: {tmpl}")
                if "callback" in compile_kwargs:
                    compile_parts.append(f"callback: {compile_kwargs['callback']}")
                # Other compile_kwargs (module, class, etc.)
                for k, v in compile_kwargs.items():
                    if k not in ("template", "callback"):
                        compile_parts.append(f"{k}: {v}")
                if compile_parts:
                    row.td("`" + ", ".join(compile_parts) + "`")
                else:
                    row.td("-")

                row.td(info.get("documentation") or "-")

        return doc.builder.compile()

    # -------------------------------------------------------------------------
    # Value rendering (for compile)
    # -------------------------------------------------------------------------

    def _render_value(self, node: BagNode) -> str:
        """Render node value applying format and template transformations.

        Applies transformations in order:
        1. value_format (node attr) - format the raw value
        2. value_template (node attr) - apply runtime template
        3. compile_callback (schema) - call method to modify context in place
        4. compile_format (schema) - format from decorator
        5. compile_template (schema) - structural template from decorator

        Template placeholders available:
        - {node_value}: the node value
        - {node_label}: the node label
        - {attr_name}: any node attribute (e.g., {lang}, {href})

        Args:
            node: The BagNode to render.

        Returns:
            Rendered string value.
        """
        node_value = node.get_value(static=True)
        node_value = "" if node_value is None else str(node_value)

        # Build template context: node_value, node_label, and all attributes
        # Start with default values from schema for optional parameters
        tag = node.tag or node.label
        info = self.get_schema_info(tag)
        call_args = info.get("call_args_validations") or {}
        template_ctx: dict[str, Any] = {}
        for param_name, (default, _validators, _type) in call_args.items():
            if default is not None:
                template_ctx[param_name] = default
        # Override with actual node attributes
        template_ctx.update(node.attr)
        template_ctx["node_value"] = node_value
        template_ctx["node_label"] = node.label
        template_ctx["_node"] = node  # For callbacks needing full node access

        # 1. value_format from node attr (runtime)
        value_format = node.attr.get("value_format")
        if value_format:
            try:
                node_value = value_format.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 2. value_template from node attr (runtime)
        value_template = node.attr.get("value_template")
        if value_template:
            node_value = value_template.format(**template_ctx)
            template_ctx["node_value"] = node_value

        # 3-5. compile_callback, compile_format and compile_template from schema
        compile_kwargs = info.get("compile_kwargs") or {}

        # 3. compile_callback - call method to modify context in place
        compile_callback = compile_kwargs.get("callback")
        if compile_callback:
            method = getattr(self, compile_callback)
            method(template_ctx)
            node_value = template_ctx["node_value"]

        # 4. compile_format from schema
        compile_format = compile_kwargs.get("format")
        if compile_format:
            try:
                node_value = compile_format.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 5. compile_template from schema
        compile_template = compile_kwargs.get("template")
        if compile_template:
            node_value = compile_template.format(**template_ctx)

        return node_value

    # -------------------------------------------------------------------------
    # Call args validation (internal)
    # -------------------------------------------------------------------------

    def _get_method(self, tag: str) -> Callable:
        """Get handler method. Raises KeyError if tag not in schema.

        Validation is now delegated to child().
        """
        info = self.get_schema_info(tag)
        handler_name = info.get("handler_name")
        return getattr(self, handler_name) if handler_name else self._default_element

    def _get_call_args_validations(self, tag: str) -> dict[str, tuple[Any, list, Any]] | None:
        """Return attribute spec for a tag from schema."""
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None
        return schema_node.attr.get("call_args_validations")


# =============================================================================
# Type hint parsing utilities (internal)
# =============================================================================


def _split_annotated(tp: Any) -> tuple[Any, list]:
    """Split Annotated type into base type and validators.

    Handles Optional[Annotated[T, ...]] which appears as Union[Annotated[T, ...], None].
    """
    if get_origin(tp) is Annotated:
        base, *meta = get_args(tp)
        validators = [m for m in meta if callable(m)]
        return base, validators

    # Handle Optional[Annotated[...]] -> Union[Annotated[...], None]
    from typing import Union

    if get_origin(tp) is Union:
        args = get_args(tp)
        # Check if it's Optional (Union with NoneType)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            inner = non_none_args[0]
            if get_origin(inner) is Annotated:
                base, *meta = get_args(inner)
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
    skip_params = {
        "self",
        "build_where",
        "node_tag",
        "node_label",
        "node_position",
    }

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


def _parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int]]:
    """Parse sub_tags spec into dict of {tag: (min, max)}.

    Cardinality syntax:
        foo      -> any number 0..N (min=0, max=sys.maxsize)
        foo[1]   -> exactly 1 (min=1, max=1)
        foo[3]   -> exactly 3 (min=3, max=3)
        foo[0:]  -> 0 or more (min=0, max=sys.maxsize)
        foo[:2]  -> 0 to 2 (min=0, max=2)
        foo[1:3] -> 1 to 3 (min=1, max=3)
        foo[]    -> ERROR (invalid syntax)
    """
    result: dict[str, tuple[int, int]] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        # Try [min:max] format first
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d*):(\d*)\]$", item)
        if match:
            tag = match.group(1)
            min_val = int(match.group(2)) if match.group(2) else 0
            max_val = int(match.group(3)) if match.group(3) else sys.maxsize
            result[tag] = (min_val, max_val)
            continue
        # Try [n] format (exactly n)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]$", item)
        if match:
            tag = match.group(1)
            n = int(match.group(2))
            result[tag] = (n, n)
            continue
        # Check for invalid [] format
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[\]$", item)
        if match:
            raise ValueError(
                f"Invalid sub_tags syntax: '{item}' - use 'foo' for 0..N or 'foo[n]' for exact count"
            )
        # Plain tag name (0..N)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)$", item)
        if match:
            tag = match.group(1)
            result[tag] = (0, sys.maxsize)
    return result


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


# =============================================================================
# SchemaBuilder
# =============================================================================


class SchemaBuilder(BagBuilderBase):
    """Builder for creating builder schemas.

    Creates schema nodes with the structure expected by BagBuilderBase:
    - node.label = element name (e.g., 'div') or abstract (e.g., '@flow')
    - node.value = None
    - node.attr = {sub_tags, inherits_from, ...}

    Schema conventions:
        - Elements: stored by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Use inherits_from='@abstract' to inherit sub_tags

    Usage:
        schema = Bag(builder=SchemaBuilder)
        schema.item('@flow', sub_tags='p,span')
        schema.item('div', inherits_from='@flow')
        schema.item('br', sub_tags='')  # void element
        schema.builder.compile('schema.msgpack')
    """

    @element()
    def item(
        self,
        build_where: Bag,
        node_tag: str,
        node_value: str,
        sub_tags: str | None = None,
        inherits_from: str | None = None,
        handler_name: str | None = None,
        call_args_validations: dict[str, tuple[Any, list, Any]] | None = None,
        compile_kwargs: dict[str, Any] | None = None,
        documentation: str | None = None,
        **kwargs: Any,
    ) -> BagNode:
        """Define a schema item (element definition).

        Args:
            build_where: The destination Bag where the node will be created.
            node_tag: The element tag ('item').
            node_value: Element name to define (e.g., 'div', '@flow').
            node_label: Ignored, node_value is used as label.
            sub_tags: Valid child tags with cardinality syntax.
            inherits_from: Abstract element name to inherit sub_tags from.
            handler_name: Method name for custom handler.
            call_args_validations: Validation spec for element attributes.
            compile_kwargs: Dict of compilation parameters (module, class, etc.).
            documentation: Documentation string for the element.
            **kwargs: Additional compile_* parameters are extracted and merged
                into compile_kwargs. E.g., compile_module='x' -> {'module': 'x'}.

        Returns:
            The created schema node.
        """
        # Extract compile_* from kwargs and merge with compile_kwargs
        merged_compile = dict(compile_kwargs) if compile_kwargs else {}
        for key, value in kwargs.items():
            if key.startswith("compile_"):
                merged_compile[key[8:]] = value  # strip "compile_" prefix

        return self.child(
            build_where,
            node_tag,
            node_label=node_value,
            sub_tags=sub_tags,
            inherits_from=inherits_from,
            handler_name=handler_name,
            call_args_validations=call_args_validations,
            compile_kwargs=merged_compile if merged_compile else None,
            documentation=documentation,
        )

    def compile(self, destination: str | Path) -> None:  # type: ignore[override]
        """Save schema to MessagePack file for later loading by builders.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self.bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)  # type: ignore[arg-type]
