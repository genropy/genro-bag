# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase - Abstract base class for Bag builders with validation.

Provides domain-specific methods for creating nodes in a Bag with
validation support.

Exports:
    element: Decorator to mark methods as element handlers
    abstract: Decorator to define abstract elements (for inheritance only)
    component: Decorator to mark methods as component handlers (composite structures)
    BagBuilderBase: Abstract base class for all builders
    SchemaBuilder: Builder for creating schemas programmatically
    Regex: Regex pattern constraint for string validation
    Range: Range constraint for numeric validation

Decorators:
    @element: Simple elements with optional adapter logic. Body can be empty (...).
    @abstract: Define sub_tags for inheritance. Cannot be instantiated directly.
    @component: Composite structures with required handler body. Receives a Bag
        to populate and returns it. Components can use a different builder internally.

Schema conventions:
    - Elements stored by name: 'div', 'span'
    - Abstracts prefixed with '@': '@flow', '@phrasing'
    - Use inherits_from='@abstract' to inherit sub_tags (only for @element)

Validation parameters:
    sub_tags: Controls which children are allowed (with cardinality).
    parent_tags: Controls where the element can be placed (comma-separated list).

sub_tags semantics:
    None     -> no validation (sub_tags not specified)
    ""       -> leaf element (no children allowed)
    "*"      -> accepts any children (container)
    "foo"    -> accepts only "foo" children

sub_tags cardinality syntax (when not "*"):
    foo      -> any number (0..N)
    foo[1]   -> exactly 1
    foo[3]   -> exactly 3
    foo[0:]  -> 0 or more
    foo[:2]  -> 0 to 2
    foo[1:3] -> 1 to 3

compile_* parameters:
    Both @element and @abstract support compile_* parameters for code generation.
    Parameters can be passed as:
    - compile_kwargs dict: compile_kwargs={'module': 'x', 'class': 'Y'}
    - Individual kwargs: compile_module='x', compile_class='Y'
    - Mixed: both approaches are merged (individual kwargs override dict)

    When using inherits_from, compile_kwargs are inherited from the abstract
    and merged with the element's own compile_kwargs (element overrides abstract).

Constraint classes for use with Annotated:
    Regex: regex pattern for strings
    Range: min/max value constraints for numbers (ge, le, gt, lt)

Type hints supported:
    - Basic types: int, str, bool, float, Decimal
    - Literal['a', 'b'] for enum-like constraints
    - list[T], dict[K, V], tuple[...], set[T] for generics
    - X | None for optional
    - Annotated[T, validator...] for validators

Example - @element:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import BagBuilderBase, element

    >>> class MyBuilder(BagBuilderBase):
    ...     @element(sub_tags='item')
    ...     def container(self): ...
    ...
    ...     @element(parent_tags='container')  # can only be inside container
    ...     def item(self): ...

Example - @component:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import BagBuilderBase, element, component

    >>> class FormBuilder(BagBuilderBase):
    ...     @element()
    ...     def input(self): ...
    ...
    ...     @component(sub_tags='')  # closed component, returns parent
    ...     def login_form(self, component: Bag, **kwargs):
    ...         component.input(name='username')
    ...         component.input(name='password')
    ...         return component

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
import warnings
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
# Empty body detection (internal, needed by decorators)
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


# =============================================================================
# Decorators (Public API)
# =============================================================================


def element(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
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
        parent_tags: Valid parent tags (comma-separated). If specified,
            element can only be placed inside one of these parents.
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

        @element(parent_tags='ul,ol')  # can only be inside ul or ol
        def li(self): ...
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
                "parent_tags": parent_tags,
                "inherits_from": inherits_from,
                "compile_kwargs": merged_compile if merged_compile else None,
            }.items()
            if v is not None
        }
        return func

    return decorator


def abstract(
    sub_tags: str | tuple[str, ...] = "",
    parent_tags: str | tuple[str, ...] | None = None,
    inherits_from: str | None = None,
    compile_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator to define an abstract element (for inheritance only).

    Abstract elements are stored with '@' prefix and cannot be instantiated.
    They define sub_tags/parent_tags that can be inherited by concrete elements.

    Args:
        sub_tags: Valid child tags with cardinality (see element decorator).
        parent_tags: Valid parent tags with cardinality.
        inherits_from: Comma-separated list of abstract names to inherit from.
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
            "inherits_from": inherits_from or "",
        }
        if parent_tags is not None:
            result["parent_tags"] = parent_tags
        if merged_compile:
            result["compile_kwargs"] = merged_compile
        func._decorator = result  # type: ignore[attr-defined]
        return func

    return decorator


def component(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    builder: type[BagBuilderBase] | None = None,
    compile_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator to mark a method as component handler.

    Components are composite structures that receive a new Bag, populate it,
    and return it. The populated bag becomes the node's value.

    Unlike @element, @component REQUIRES a method body (ellipsis not allowed).
    The handler receives a fresh Bag as first parameter (after self) and
    should populate it with child elements.

    Args:
        tags: Tag names this component handles. If None, uses method name.
        sub_tags: Valid child tags AFTER the component is created. Controls
            return behavior of the component call:
            - '' (empty string): Closed/leaf component, returns parent bag
              (for chaining at same level)
            - defined or None: Open container, returns internal bag
              (for adding children to the component)
        parent_tags: Valid parent tags (comma-separated). If specified,
            component can only be placed inside one of these parents.
        builder: Optional builder class for the component's internal bag.
            If not specified, uses the same builder class as parent.
        compile_kwargs: Dict of compilation parameters (module, class, etc.).
        **kwargs: Additional compile_* parameters are extracted and merged
            into compile_kwargs.

    Handler signature:
        def handler(self, component: Bag, **kwargs) -> Bag | dict:
            # 'component' is the component's internal Bag to populate
            # Return the component, or a dict with extra attrs for the node

    Example - Closed component (sub_tags=''):
        @component(sub_tags='')
        def login_form(self, component: Bag, **kwargs):
            component.input(name='username')
            component.input(name='password')
            component.button('Login')
            return component

        # Usage: returns parent for chaining
        page.login_form()
        page.other_element()  # continues at same level

    Example - Open component (sub_tags defined):
        @component(sub_tags='item')
        def mylist(self, component: Bag, title='', **kwargs):
            component.header(title=title)
            return component

        # Usage: returns internal bag for adding children
        lst = page.mylist(title='My List')
        lst.item('First')
        lst.item('Second')

    Example - Return dict for node attributes:
        @component(sub_tags='')
        def card(self, component: Bag, title='', **kwargs):
            component.header(title)
            component.body()
            return {'css_class': 'card', 'data_id': '123'}
    """
    # Extract compile_* from kwargs and merge with compile_kwargs
    merged_compile = dict(compile_kwargs) if compile_kwargs else {}
    for key, value in kwargs.items():
        if key.startswith("compile_"):
            merged_compile[key[8:]] = value

    def decorator(func: Callable) -> Callable:
        # Components MUST have a real body (not ellipsis)
        if _is_empty_body(func):
            raise ValueError(
                f"@component '{func.__name__}' must have a body - ellipsis (...) not allowed"
            )

        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "component": True,
                "tags": tags,
                "sub_tags": sub_tags,
                "parent_tags": parent_tags,
                "builder": builder,
                "compile_kwargs": merged_compile if merged_compile else None,
            }.items()
            if v is not None
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
    Define elements using decorators:
        - @element: Simple elements (body can be empty or with adapter logic)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @component: Composite structures with required handler body

    Schema conventions:
        - Elements: stored directly by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Components: stored by name, marked with is_component=True

    Validation parameters:
        - sub_tags: Controls which children are allowed under this element
        - parent_tags: Controls where this element can be placed

    Schema loading priority:
        1. schema_path passed to constructor (builder_schema_path='...')
        2. schema_path class attribute
        3. @element and @component decorated methods

    Usage:
        >>> bag = Bag(builder=MyBuilder)
        >>> bag.div()  # looks up 'div' in schema, calls handler
        >>> # With custom schema:
        >>> bag = Bag(builder=MyBuilder, builder_schema_path='custom.bag.mp')
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    schema_path: str | Path | None = None  # Default schema path (class attribute)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from @element and @component decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._class_schema = Bag().fill_from(getattr(cls, "schema_path", None))

        for tag_list, method_name, obj, decorator_info in _pop_decorated_methods(cls):
            if method_name:
                setattr(cls, method_name, obj)

            is_component = decorator_info.get("component", False)
            # For components: distinguish between sub_tags="" (closed) and absent (open)
            # Use sentinel to detect if sub_tags was explicitly set
            sub_tags = decorator_info.get("sub_tags") if is_component else decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            compile_kwargs = decorator_info.get("compile_kwargs")
            component_builder = decorator_info.get("builder")
            documentation = obj.__doc__
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                if is_component:
                    cls._class_schema.set_item(
                        tag,
                        None,
                        handler_name=method_name,
                        is_component=True,
                        component_builder=component_builder,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        compile_kwargs=compile_kwargs,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )
                else:
                    cls._class_schema.set_item(
                        tag,
                        None,
                        adapter_name=method_name,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        inherits_from=inherits_from,
                        compile_kwargs=compile_kwargs,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )

        # Check for name collisions with Bag and BagBuilderBase methods
        _rename_colliding_schema_tags(cls, cls._class_schema)

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
                info = self.get_schema_info(node_tag)
            except KeyError as err:
                raise AttributeError(f"'{type(self).__name__}' has no element '{node_tag}'") from err

            # Validazione sui kwargs originali, PRIMA del method
            node_value = args[0] if args else kwargs.get("node_value")
            self._validate_call_args(info, node_value, kwargs)

            # Check if this is a component
            if info.get("is_component"):
                return self._handle_component(destination_bag, info, node_tag, kwargs)

            # Se c'è un adapter, chiamalo per trasformare i kwargs
            adapter_name = info.get("adapter_name")
            if adapter_name:
                adapter = getattr(self, adapter_name)
                result = adapter(**kwargs)
                if isinstance(result, dict):
                    kwargs = result
                    node_value = kwargs.pop("node_value", node_value)

            # Rimuovi node_value dai kwargs per evitare duplicati
            kwargs.pop("node_value", None)
            return self._add_element(destination_bag, node_value, node_tag=node_tag, **kwargs)

        return wrapper

    def _handle_component(
        self,
        destination_bag: Bag,
        info: dict,
        node_tag: str,
        kwargs: dict,
    ) -> Bag | BagNode:
        """Handle component invocation.

        Creates an empty Bag, inserts it into destination, then calls the handler
        to populate it. This order ensures validation passes (empty bag has no children).

        Args:
            destination_bag: The parent Bag where component will be added.
            info: Schema info for the component.
            node_tag: The tag name for the component.
            kwargs: Arguments passed to the component.

        Returns:
            - If sub_tags='': returns destination_bag (closed/leaf component)
            - Otherwise: returns the component node (open container)
        """
        handler_name = info.get("handler_name")
        component_builder_class = info.get("component_builder")
        sub_tags = info.get("sub_tags")

        # 1. Create empty Bag with appropriate builder
        if component_builder_class is not None:
            component_bag = Bag(builder=component_builder_class)
        else:
            component_bag = Bag(builder=type(self))

        # 2. Insert node with empty Bag FIRST (validation passes)
        node = self._add_element(
            destination_bag,
            node_value=component_bag,
            node_tag=node_tag,
        )

        # 3. Call handler to populate the Bag (already inside node.value)
        handler = getattr(self, handler_name)
        result = handler(component_bag, **kwargs)

        # 4. Handler can return dict with extra attrs for the node
        if isinstance(result, dict):
            for key, value in result.items():
                if key != "node_value":
                    node.attr[key] = value

        # 5. Determine return value based on sub_tags
        # sub_tags='' (empty string) -> void/leaf, return parent bag
        # sub_tags defined or None -> open container, return internal bag
        if sub_tags == "":
            return destination_bag
        return component_bag

    def _add_element(
        self,
        build_where: Bag,
        node_value: Any = None,
        node_label: str | None = None,
        node_tag: str = "",
        **attr: Any,
    ) -> BagNode:
        """Add an element node to the bag.

        Called by the wrapper after optional adapter transformation.

        Args:
            build_where: The destination Bag where the node will be created.
            node_value: Node content (positional). Becomes node.value.
            node_label: Optional explicit label for the node.
            node_tag: The tag name for the element.
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
        self._validate_parent_tags(child_info, parent_node)

        node_label = node_label or self._auto_label(build_where, node_tag)
        child_node = build_where.set_item(node_label, node_value, _attributes=dict(attr), node_position=node_position)
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
        sub_tags_compiled: dict[str, tuple[int, int]] | str,
        children_tags: list[str],
    ) -> list[str]:
        """Validate a list of child tags against sub_tags spec.

        Args:
            node_tag: Tag of parent node (for error messages)
            sub_tags_compiled: Compiled sub_tags: "*" for any, or dict {tag: (min, max)}
            children_tags: List of child tags to validate

        Returns:
            List of invalid_reasons (missing required tags)

        Raises:
            ValueError: if tag not allowed or max exceeded
        """
        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            return []

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

        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            node._invalid_reasons = []
            return

        children_tags = [n.tag for n in node.value.nodes] if isinstance(node.value, Bag) else []

        node._invalid_reasons = self._validate_children_tags(
            node_tag, sub_tags_compiled, children_tags
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

        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
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

        self._validate_children_tags(target_node.tag, sub_tags_compiled, children_tags)

    def _validate_parent_tags(
        self,
        child_info: dict,
        parent_node: BagNode | None,
    ) -> None:
        """Validate that child can be placed in parent based on parent_tags.

        Args:
            child_info: Schema info for the child element.
            parent_node: The parent node (None if adding to root).

        Raises:
            ValueError: If parent_tags is specified and parent is not in the list.
        """
        parent_tags_compiled = child_info.get("parent_tags_compiled")
        if parent_tags_compiled is None:
            return

        parent_tag = parent_node.tag if parent_node else None
        if parent_tag not in parent_tags_compiled:
            valid_parents = ", ".join(sorted(parent_tags_compiled))
            raise ValueError(
                f"Element cannot be placed here: parent_tags requires one of [{valid_parents}], "
                f"but parent is '{parent_tag or 'root'}'"
            )

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
            - adapter_name: str | None
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
            # Support multiple inheritance: "alfa,beta" -> ["alfa", "beta"]
            # Parents are processed left-to-right, later parents override earlier ones
            parents = [p.strip() for p in inherits_from.split(",")]
            for parent in parents:
                abstract_attrs = self.schema.get_attr(parent)
                if abstract_attrs:
                    for k, v in abstract_attrs.items():
                        # Skip inherits_from from abstract - don't propagate it
                        if k == "inherits_from":
                            continue
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

        parent_tags = result.get("parent_tags")
        if parent_tags is not None:
            result["parent_tags_compiled"] = _parse_parent_tags_spec(parent_tags)

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
        "component",  # first param of @component methods
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
# Sub-tags and parent-tags validation utilities (internal)
# =============================================================================


def _parse_parent_tags_spec(spec: str) -> set[str]:
    """Parse parent_tags spec into set of valid parent tag names.

    Simple comma-separated list of tag names (no cardinality).

    Args:
        spec: Comma-separated list of tag names, e.g. "div, span, section".

    Returns:
        Set of valid parent tag names.
    """
    return {tag.strip() for tag in spec.split(",") if tag.strip()}


def _parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int]] | str:
    """Parse sub_tags spec into dict of {tag: (min, max)} or "*" for any.

    Semantics:
        ""       -> leaf element (no children allowed) - returns empty dict
        "*"      -> accepts any children (no validation) - returns "*"
        "foo"    -> accepts only "foo" children

    Cardinality syntax:
        foo      -> any number 0..N (min=0, max=sys.maxsize)
        foo[1]   -> exactly 1 (min=1, max=1)
        foo[3]   -> exactly 3 (min=3, max=3)
        foo[0:]  -> 0 or more (min=0, max=sys.maxsize)
        foo[:2]  -> 0 to 2 (min=0, max=2)
        foo[1:3] -> 1 to 3 (min=1, max=3)
        foo[]    -> ERROR (invalid syntax)

    Returns:
        "*" if spec is "*" (accepts any children)
        dict of {tag: (min, max)} otherwise
    """
    # Handle wildcard - accepts any children
    if spec == "*":
        return "*"

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


def _pop_decorated_methods(cls: type):
    """Remove and yield decorated methods with their info and tags."""
    for name, obj in list(cls.__dict__.items()):
        if hasattr(obj, "_decorator"):
            delattr(cls, name)
            decorator_info = obj._decorator

            if decorator_info.get("abstract"):
                yield [f"@{name}"], None, obj, decorator_info
            elif decorator_info.get("component"):
                # Components always have handler_name (body required)
                tag_list = [] if name.startswith("_") else [name]
                tags_raw = decorator_info.get("tags")
                if tags_raw:
                    if isinstance(tags_raw, str):
                        tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
                    else:
                        tag_list.extend(tags_raw)
                handler_name = f"_comp_{tag_list[0]}"
                yield tag_list, handler_name, obj, decorator_info
            else:
                tag_list = [] if name.startswith("_") else [name]
                tags_raw = decorator_info.get("tags")
                if tags_raw:
                    if isinstance(tags_raw, str):
                        tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
                    else:
                        tag_list.extend(tags_raw)
                adapter_name = None if _is_empty_body(obj) else f"_el_{tag_list[0]}"
                yield tag_list, adapter_name, obj, decorator_info


def _rename_colliding_schema_tags(cls: type, schema: Bag) -> None:
    """Rename schema tags that collide with Bag or BagBuilderBase methods.

    Tags that collide are renamed to 'el_<tag>' and a warning is emitted.
    """
    # Get all method names from Bag and BagBuilderBase
    bag_methods = set(dir(Bag))
    builder_methods = set(dir(BagBuilderBase))
    reserved_names = bag_methods | builder_methods

    # Get all tag names from schema (excluding @abstract tags)
    schema_tags = {node.label for node in schema.nodes if not node.label.startswith("@")}

    # Find collisions
    collisions = schema_tags & reserved_names
    if not collisions:
        return

    # Rename colliding tags
    renamed = []
    for tag in collisions:
        new_tag = f"el_{tag}"
        node = schema.get_node(tag)
        if node is not None:
            # Get node data and attributes
            node_value = node.value
            node_attrs = dict(node.attr)
            # Remove old entry and add new one
            schema.pop(tag)
            schema.set_item(new_tag, node_value, **node_attrs)
            renamed.append(f"'{tag}' -> '{new_tag}'")

    # Emit warning
    if renamed:
        warnings.warn(
            f"Builder {cls.__name__}: schema tags renamed to avoid collision with "
            f"Bag/BagBuilderBase methods: {', '.join(sorted(renamed))}",
            UserWarning,
            stacklevel=3,
        )


# =============================================================================
# SchemaBuilder
# =============================================================================


class SchemaBuilder(BagBuilderBase):
    """Builder for creating builder schemas programmatically.

    Use SchemaBuilder to define schemas at runtime instead of using decorators.
    Creates schema nodes with the structure expected by BagBuilderBase.

    Note: SchemaBuilder cannot define @component - components require code
    handlers and must be defined using the @component decorator.

    Schema conventions:
        - Elements: stored by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Use inherits_from='@abstract' to inherit sub_tags

    Usage:
        schema = Bag(builder=SchemaBuilder)
        schema.item('@flow', sub_tags='p,span')
        schema.item('div', inherits_from='@flow')
        schema.item('li', parent_tags='ul,ol')  # li only inside ul or ol
        schema.item('br', sub_tags='')  # void element
        schema.builder.compile('schema.msgpack')
    """

    @element()
    def item(
        self,
        node_value: str,
        sub_tags: str | None = None,
        parent_tags: str | None = None,
        inherits_from: str | None = None,
        adapter_name: str | None = None,
        call_args_validations: dict[str, tuple[Any, list, Any]] | None = None,
        compile_kwargs: dict[str, Any] | None = None,
        documentation: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Define a schema item (element definition).

        Args:
            node_value: Element name to define (e.g., 'div', '@flow').
            sub_tags: Valid child tags with cardinality syntax.
            parent_tags: Comma-separated list of valid parent tags for this element.
            inherits_from: Abstract element name to inherit sub_tags from.
            adapter_name: Method name for adapter that transforms kwargs.
            call_args_validations: Validation spec for element attributes.
            compile_kwargs: Dict of compilation parameters (module, class, etc.).
            documentation: Documentation string for the element.
            **kwargs: Additional compile_* parameters are extracted and merged
                into compile_kwargs. E.g., compile_module='x' -> {'module': 'x'}.

        Returns:
            Dict with transformed kwargs for _default_element.
        """
        # Extract compile_* from kwargs and merge with compile_kwargs
        merged_compile = dict(compile_kwargs) if compile_kwargs else {}
        for key, value in kwargs.items():
            if key.startswith("compile_"):
                merged_compile[key[8:]] = value  # strip "compile_" prefix

        return {
            "node_label": node_value,
            "sub_tags": sub_tags,
            "parent_tags": parent_tags,
            "inherits_from": inherits_from,
            "adapter_name": adapter_name,
            "call_args_validations": call_args_validations,
            "compile_kwargs": merged_compile if merged_compile else None,
            "documentation": documentation,
        }

    def compile(self, destination: str | Path) -> None:  # type: ignore[override]
        """Save schema to MessagePack file for later loading by builders.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self.bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)  # type: ignore[arg-type]
