# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag module - main container class.

The Bag is the core hierarchical data container of the Genro framework.
It provides an ordered, dict-like container where elements are BagNodes,
each with a label, value, and optional attributes.

Key features:
    - Hierarchical access via dot-separated paths: bag['a.b.c']
    - Ordered storage: elements maintain insertion order
    - No duplicate labels (unlike original gnrbag)
    - Backref mode for strict tree structure with parent references
    - Event subscription system for change notifications

Example:
    >>> bag = Bag()
    >>> bag['config.database.host'] = 'localhost'
    >>> bag['config.database.port'] = 5432
    >>> print(bag['config.database.host'])
    localhost

Async Usage with Resolvers:
    When using Bag with resolvers, the ``static`` parameter controls behavior:

    - ``static=True``: Always returns direct data (no resolver trigger)
    - ``static=False``: May trigger resolver if cache expired

    In **sync context**, no special handling is needed - async resolvers are
    automatically awaited via ``@smartasync``.

    In **async context**, the result may be a coroutine. Use ``smartawait``::

        from genro_toolbox import smartawait

        async def get_data():
            result = await smartawait(bag.get_item("path", static=False))
            return result

    Or explicitly check for coroutine::

        import inspect

        result = bag.get_item("path", static=False)
        if inspect.iscoroutine(result):
            result = await result
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from genro_toolbox import smartawait, smartcontinuation, smartsplit
from genro_toolbox.decorators import extract_kwargs
from genro_toolbox.typeutils import safe_is_instance

from .bag_parse import BagParser
from .bag_query import BagQuery
from .bag_serialize import BagSerializer
from .bagnode import BagNode, BagNodeContainer
from .resolver import BagCbResolver

_T = TypeVar("_T", str, list)


def _normalize_path(path: _T) -> _T:
    """Normalize a path for Bag access.

    Args:
        path: Path as dot-separated string or list of segments.

    Returns:
        The path unchanged (validation only).

    Note:
        Legacy genropy supported non-string paths (int, etc.) with automatic
        conversion. This is now handled by the compatibility layer.
        See: genro-bag-compat.normalizeItemPath()
    """
    return path


class Bag(BagParser, BagSerializer, BagQuery):
    """Hierarchical data container with path-based access.

    A Bag is an ordered container of BagNodes, accessible by label, numeric index,
    or hierarchical path. Nested elements can be accessed with dot-separated paths
    like 'a.b.c'.

    Unlike the original gnrbag, this implementation does NOT support duplicate labels.
    Each label at a given level must be unique.

    Inherits from:
        BagParser: Provides from_xml, from_tytx, from_json classmethods.
        BagSerializer: Provides to_xml, to_tytx, to_json instance methods.
        BagQuery: Provides query, digest, walk, keys, values, items, sum, sort methods.

    Attributes:
        _nodes: BagNodeContainer holding the BagNodes.
        _backref: If True, enables strict tree mode with parent references.
        _parent: Reference to parent Bag (only in backref mode).
        _parent_node: Reference to the BagNode containing this Bag.
        _upd_subscribers: Callbacks for update events.
        _ins_subscribers: Callbacks for insert events.
        _del_subscribers: Callbacks for delete events.
        _root_attributes: Attributes for the root bag.
        _builder: Optional builder for domain-specific node creation.
    """

    @extract_kwargs(builder=True)
    def __init__(self, source: dict[str, Any] | None = None, builder=None, builder_kwargs=None):
        """Create a new Bag.

        Args:
            source: Optional dict to initialize from. Keys become labels,
                values become node values.
            builder: Optional BagBuilderBase class for domain-specific
                node creation (e.g., HtmlBuilder for HTML generation).
            builder_kwargs: Extra kwargs passed to builder constructor.
                Can also be passed with builder_ prefix.

        Example:
            >>> bag = Bag({'a': 1, 'b': 2})
            >>> bag['a']
            1
            >>> from genro_bag.builders import HtmlBuilder
            >>> html = Bag(builder=HtmlBuilder)
            >>> html.div(id='main').p(value='Hello')
            >>> # With builder kwargs:
            >>> bag = Bag(builder=XsdBuilder, builder_xsd_source='schema.xsd')
        """
        self._nodes: BagNodeContainer = BagNodeContainer()
        self._backref: bool | str = False
        self._parent: Bag | None = None
        self._parent_node: BagNode | None = None
        self._upd_subscribers: dict = {}
        self._ins_subscribers: dict = {}
        self._del_subscribers: dict = {}
        self._root_attributes: dict | None = None
        self.builder = builder(self, **builder_kwargs) if builder else None

        if source:
            self.fill_from(source)

    def fill_from(
        self, source: dict[str, Any] | str | Path | Bag | None = None, format: str | None = None
    ) -> Bag:
        """Fill bag from a source and return self for chaining.

        Populates the bag with data from various sources:
        - None: No-op, returns self unchanged
        - dict: Keys become labels, values become node values
        - str (file path): Load from file based on extension:
            - .xml: Parse as XML
            - .bag.json: Parse as TYTX JSON
            - .bag.mp: Parse as TYTX MessagePack
        - Bag: Copy nodes from another Bag

        Existing nodes are cleared first (except when source is None).

        Args:
            source: Data source (dict, file path, Bag, or None).
            format: Force format for file loading ('xml', 'json', 'msgpack').
                If None, format is detected from file extension.

        Returns:
            Self for method chaining.

        Example:
            >>> bag = Bag().fill_from({'x': 1, 'y': {'z': 2}})
            >>> bag['y.z']
            2
            >>>
            >>> bag2 = Bag().fill_from('/path/to/data.bag.json')
            >>>
            >>> bag3 = Bag().fill_from(None)  # returns empty bag
            >>>
            >>> # Force XML format regardless of extension
            >>> bag4 = Bag().fill_from('/path/to/schema.xsd', format='xml')
        """
        if source is None:
            return self
        if isinstance(source, (str, Path)):
            self._fill_from_file(str(source), format=format)
        elif isinstance(source, Bag):
            self._fill_from_bag(source)
        elif isinstance(source, dict):
            self._fill_from_dict(source)
        else:
            raise TypeError(
                f"fill_from expects str, Path, Bag, dict, or None, got {type(source).__name__}"
            )
        return self

    def _fill_from_file(self, path: str, format: str | None = None) -> None:
        """Load bag contents from a file.

        Detects format from file extension (unless format is specified):
        - .bag.json: TYTX JSON format
        - .bag.mp: TYTX MessagePack format
        - .xml: XML format (with auto-detect for legacy GenRoBag)

        Args:
            path: Path to the file to load.
            format: Force format ('xml', 'json', 'msgpack'). If None, detect from extension.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file extension is not recognized and format not specified.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        # Determine format: explicit or from extension
        if format is None:
            if path.endswith(".bag.json"):
                format = "json"
            elif path.endswith(".bag.mp"):
                format = "msgpack"
            elif path.endswith(".xml"):
                format = "xml"
            else:
                raise ValueError(
                    f"Unrecognized file extension: {path}. Supported: .bag.json, .bag.mp, .xml"
                )

        # Load based on format
        if format == "json":
            with open(path, encoding="utf-8") as f:
                data = f.read()
            loaded = Bag.from_tytx(data, transport="json")
            self._fill_from_bag(loaded)

        elif format == "msgpack":
            with open(path, "rb") as f:
                data_bytes = f.read()
            loaded = Bag.from_tytx(data_bytes, transport="msgpack")
            self._fill_from_bag(loaded)

        elif format == "xml":
            with open(path, encoding="utf-8") as f:
                data = f.read()
            loaded = Bag.from_xml(data)
            self._fill_from_bag(loaded)

    def _fill_from_bag(self, other: Bag) -> None:
        """Copy nodes from another Bag.

        Clears current contents and copies all nodes from the source Bag.

        Args:
            other: Source Bag to copy from.
        """
        self.clear()
        for node in other:
            # Deep copy the value if it's a Bag
            value = node.value
            if isinstance(value, Bag):
                value = value.deepcopy()
            self.set_item(node.label, value, **dict(node.attr))

    def _fill_from_dict(self, data: dict[str, Any]) -> None:
        """Populate bag from a dictionary.

        Clears current contents and creates nodes from dict items.
        Nested dicts are converted to nested Bags.

        Args:
            data: Dict where keys become labels and values become node values.
        """
        self.clear()
        for key, value in data.items():
            if isinstance(value, dict):
                value = Bag(value)
            self.set_item(key, value)

    # -------------------- class methods --------------------------------

    @classmethod
    def from_url(cls, url: str, timeout: int = 30) -> Bag:
        """Load Bag from URL (classmethod, sync/async capable).

        Fetches content from URL and parses based on HTTP content-type header.
        Uses UrlResolver internally for DRY implementation.

        Args:
            url: HTTP/HTTPS URL to fetch.
            timeout: Request timeout in seconds. Default 30.

        Returns:
            Bag: Parsed content as Bag. Format auto-detected from content-type:
                - application/json, text/json → from_json
                - application/xml, text/xml → from_xml

        Raises:
            httpx.HTTPError: If HTTP request fails.
            ValueError: If content-type is not supported.

        Example:
            >>> # Sync context
            >>> bag = Bag.from_url('https://example.com/data.xml')
            >>>
            >>> # Async context
            >>> bag = await Bag.from_url('https://example.com/data.xml')
        """
        from genro_bag.resolvers import UrlResolver

        resolver = UrlResolver(url, timeout=timeout, as_bag=True)
        return cast("Bag", resolver())

    # -------------------- properties --------------------------------

    @property
    def parent(self) -> Bag | None:
        """Parent Bag in backref mode.

        Returns the parent Bag if this Bag is nested inside another and backref
        mode is enabled. Returns None for root Bags or when backref is disabled.
        """
        return self._parent

    @parent.setter
    def parent(self, value: Bag | None) -> None:
        self._parent = value

    @property
    def parent_node(self) -> BagNode | None:
        """The BagNode that contains this Bag.

        Returns the BagNode whose value is this Bag, or None if this is a
        standalone Bag not contained in any node.
        """
        return self._parent_node

    @parent_node.setter
    def parent_node(self, value: BagNode | None) -> None:
        self._parent_node = value

    @property
    def backref(self) -> bool:
        """Whether backref mode is enabled.

        In backref mode, Bags maintain references to their parent Bag and
        parent node, enabling tree traversal and event propagation up the
        hierarchy.
        """
        return bool(self._backref)

    @property
    def fullpath(self) -> str | None:
        """Full path from root Bag to this Bag.

        Returns the dot-separated path from the root of the hierarchy to this
        Bag. Returns None if backref mode is not enabled or if this is the root.
        """
        if self.parent is not None and self.parent_node is not None:
            parent_fullpath = self.parent.fullpath
            if parent_fullpath:
                return f"{parent_fullpath}.{self.parent_node.label}"
            else:
                return self.parent_node.label
        return None

    @property
    def root(self) -> Bag:
        """Get the root Bag of the hierarchy.

        Traverses parent chain until reaching a Bag with no parent.
        Returns self if this is already the root.
        """
        curr = self
        while curr.parent is not None:
            curr = curr.parent
        return curr

    @property
    def in_async_context(self) -> bool:
        """Whether we are currently running inside an async context."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    @property
    def attributes(self) -> dict[str, Any]:
        """Attributes of the parent node containing this Bag.

        Returns the attributes dict of the BagNode that contains this Bag.
        Returns an empty dict if this is a standalone Bag with no parent node.
        """
        if self.parent_node is not None:
            return cast(dict[str, Any], self.parent_node.get_attr())
        return {}

    @property
    def root_attributes(self) -> dict | None:
        """Attributes for the root Bag."""
        return self._root_attributes

    @root_attributes.setter
    def root_attributes(self, attrs: dict) -> None:
        self._root_attributes = dict(attrs)

    @property
    def builder(self):
        """Get the builder associated with this Bag.

        Returns:
            The BagBuilderBase instance, or None if no builder is set.
        """
        return self._builder

    @builder.setter
    def builder(self, value):
        """Set the builder for this Bag.

        Args:
            value: A BagBuilderBase instance or None.
        """
        self._builder = value

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to builder if present.

        When a builder is set, unknown attributes are looked up on the builder.
        This enables fluent APIs like bag.div(id='main').p(value='Hello').

        Args:
            name: Attribute name to look up.

        Returns:
            A callable that creates a child node with that tag.

        Raises:
            AttributeError: If no builder is set or builder doesn't have the tag.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        if self._builder is not None:
            # Delegate to builder - let it raise specific error for unknown elements
            handler = getattr(self._builder, name)

            # Return callable bound to this Bag
            # API: bag.foo('John') -> node_value='John', node_label=auto, tag='foo'
            #      bag.foo('John', node_label='x') -> explicit label
            #      bag.foo('John', node_position='<first') -> insertion position
            # NOTE: First positional arg maps to node_value (node content), passed as keyword
            return lambda node_value=None, node_label=None, node_position=None, **attr: handler(
                self,
                _tag=name,
                node_value=node_value,
                node_label=node_label,
                node_position=node_position,
                **attr,
            )

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # -------------------- _htraverse helpers --------------------------------

    def _htraverse_before(self, path: str | list) -> tuple[Bag | None, list[str]]:
        """Parse path and handle #parent navigation.

        First phase of path traversal: converts path to list, handles '../' alias,
        and processes any leading #parent segments.

        Args:
            path: Dot-separated path like 'a.b.c' or list ['a', 'b', 'c'].

        Returns:
            Tuple of (curr, pathlist) where:
                - curr: Starting Bag (may have moved up via #parent), or None
                - pathlist: Remaining path segments to process
        """
        curr: Bag | None = self

        if isinstance(path, str):
            path = path.replace("../", "#parent.")
            pathlist = [x for x in smartsplit(path, ".") if x]
        else:
            pathlist = list(path)

        # handle parent reference #parent at the beginning
        while pathlist and pathlist[0] == "#parent" and curr is not None:
            pathlist.pop(0)
            curr = curr.parent

        return curr, pathlist

    # -------------------- _htraverse --------------------------------

    def _htraverse(
        self, path: str | list, write_mode: bool = False, static: bool = True
    ) -> tuple[Any, str | None]:
        """Traverse a hierarchical path - unified sync/async version.

        Single method that handles both sync and async contexts:
        - In sync context: returns tuple directly
        - In async context with static=False: may return coroutine

        Args:
            path: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            write_mode: If True, create intermediate Bags for missing segments.
                        Forces static=True (no resolver triggers during write).
            static: If True, don't trigger resolvers during traversal.

        Returns:
            Tuple of (container, label) OR coroutine that resolves to tuple.
        """
        if write_mode:
            static = True
        curr, pathlist = self._htraverse_before(path)
        if curr is None:
            return None, None
        if not pathlist:
            return curr, ""

        def finalize(result: tuple[Bag, list[str]]) -> tuple[Any, str | None]:
            """Finalize traversal: handle empty path or create intermediate nodes."""
            curr, pathlist = result
            if not write_mode:
                if len(pathlist) > 1:
                    return None, None
                return curr, pathlist[0]
            # Write mode: create intermediate nodes
            while len(pathlist) > 1:
                label = pathlist.pop(0)
                if label.startswith("#"):
                    raise BagException("Not existing index in #n syntax")
                new_bag = curr.__class__()
                curr._nodes.set(label, new_bag, parent_bag=curr)
                curr = new_bag
            return curr, pathlist[0]

        result = self._traverse_inner(curr, pathlist, write_mode, static)
        return smartcontinuation(result, finalize)  # type: ignore[no-any-return]

    def _is_coroutine(self, value: Any) -> bool:
        """Check if value is a coroutine (only possible in async context)."""
        return self.in_async_context and asyncio.iscoroutine(value)

    def _get_new_curr(self, node: BagNode, value: Any, write_mode: bool) -> Bag | None:
        """Get next curr for traversal, creating Bag if needed in write_mode."""
        if isinstance(value, Bag):
            return value
        if write_mode:
            new_bag = self.__class__()
            node.set_value(new_bag)
            return new_bag
        return None

    def _traverse_inner(
        self, curr: Bag, pathlist: list, write_mode: bool, static: bool
    ) -> tuple[Bag, list]:
        """Traverse path segments - unified sync/async version.

        Args:
            curr: Starting Bag position.
            pathlist: Path segments to traverse.
            write_mode: If True, replace non-Bag values with Bags during traversal.
            static: If True, don't trigger resolvers.

        Returns:
            Tuple of (container, remaining_path) OR coroutine.
        """
        while len(pathlist) > 1 and isinstance(curr, Bag):
            segment = pathlist[0]  # read without removing
            node = curr._nodes[segment]
            if not node:
                break

            value = node.get_value(static=static)

            if not self._is_coroutine(value):
                new_curr = self._get_new_curr(node, value, write_mode)
                if new_curr is None:
                    break
                pathlist.pop(0)  # traversal succeeded, now remove
                curr = new_curr
                continue

            # coroutine case
            pathlist.pop(0)  # remove before creating continuation
            remaining = pathlist[:]

            async def cont(
                value=value,
                node=node,
                curr=curr,
                segment=segment,
                remaining=remaining,
            ):
                resolved = await value
                new_curr = self._get_new_curr(node, resolved, write_mode)
                if new_curr is None:
                    return (curr, [segment] + remaining)
                return await smartawait(
                    self._traverse_inner(new_curr, remaining, write_mode, static)
                )

            return cont()  # type: ignore[no-any-return]

        return (curr, pathlist)

    # -------------------- get (single level) --------------------------------

    def get(self, label: str, default: Any = None, static: bool = True) -> Any:
        """Get value at a single level (no path traversal).

        Unlike get_item/`__getitem__`, this method only looks at direct children
        of this Bag. It does not traverse paths with dots.

        Args:
            label: Node label to look up. Can be a string label or '#n' index.
                Supports '?attr' suffix to get a node attribute instead of value.
            default: Value to return if label not found.
            static: If True, don't trigger resolvers. Default True.

        Returns:
            The node's value if found, otherwise default.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag.get('a')
            1
            >>> bag.get('missing', 'default')
            'default'
            >>> bag.set_item('x', 42, _attributes={'type': 'int'})
            >>> bag.get('x?type')  # get attribute
            'int'
        """
        if not label:
            return self
        if label == "#parent":
            return self.parent
        attrname = None
        if "?" in label:
            label, attrname = label.split("?")
        node = self._nodes.get(label)
        if not node:
            return default
        return node.get_attr(attrname) if attrname else node.get_value(static=static)

    # -------------------- get_item --------------------------------

    def get_item(self, path: str, default: Any = None, static: bool = True) -> Any:
        """Get value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path and returns
        the value at the final location.

        By default does NOT trigger resolvers (static=True).
        Use static=False to trigger resolvers during traversal.

        Args:
            path: Hierarchical path like 'a.b.c'. Empty path returns self.
                Supports '?attr' suffix to get attribute instead of value.
            default: Value to return if path not found.
            static: If False, trigger resolvers during traversal. Default True.

        Returns:
            The value at the path if found, otherwise default.

        Example:
            >>> bag = Bag()
            >>> bag['config.db.host'] = 'localhost'
            >>> bag.get_item('config.db.host')
            'localhost'
            >>> bag['config.db.host']  # static=True, no resolver trigger
            'localhost'
            >>> # With resolver (static=False), in async context use smartawait:
            >>> from genro_toolbox import smartawait
            >>> result = await smartawait(bag.get_item('path.with.resolver', static=False))
        """
        if not path:
            return self

        path = _normalize_path(path)

        result = self._htraverse(path, static=static)

        def finalize(obj_label):
            obj, label = obj_label
            if isinstance(obj, Bag):
                return obj.get(label, default, static=static)
            return default

        return smartcontinuation(result, finalize)

    def __getitem__(self, path: str) -> Any:
        """Get value at path (no resolver trigger).

        Delegates to get_item with static=True (default).
        Use bag.get_item(path, static=False) to trigger resolvers.
        """
        return self.get_item(path)

    # -------------------- set_item --------------------------------

    def set_item(
        self,
        path: str,
        value: Any,
        _attributes: dict | None = None,
        node_position: str | int | None = None,
        _updattr: bool = False,
        _remove_null_attributes: bool = True,
        _reason: str | None = None,
        _fired: bool = False,
        do_trigger: bool = True,
        resolver=None,
        **kwargs,
    ) -> BagNode:
        """Set value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path, creating
        intermediate Bags as needed, and sets the value at the final location.
        This is the method behind `bag[path] = value`.

        This method is synchronous and never triggers resolvers during traversal.

        If the path already exists, the value is updated. If it doesn't exist,
        a new node is created at the specified position.

        Resolver handling (Issue #5):
            If the target node has a resolver and the `resolver` parameter is not
            explicitly provided, a BagNodeException is raised. To modify a node
            with a resolver, you must explicitly handle the resolver:
            - resolver=False: Remove resolver and set value
            - resolver=NewResolver: Replace resolver with a new one

        Args:
            path: Hierarchical path like 'a.b.c'. Empty path is ignored.
                Supports '?attr' suffix to set a node attribute instead of value.
            value: Value to set at the path (or attribute value if ?attr syntax).
            _attributes: Optional dict of attributes to set on the node.
            node_position: Position for new nodes. Supports:
                - '>': Append at end (default)
                - '<': Insert at beginning
                - '#n': Insert at index n
                - '<label': Insert before label
                - '>label': Insert after label
            _updattr: If True, update attributes instead of replacing.
            _remove_null_attributes: If True, remove None attributes.
            _reason: Reason for the change (for events).
            _fired: If True, immediately reset value to None after setting.
                Used for event-like signals (like JavaScript fireItem).
            do_trigger: If True (default), fire events on change.
                Set to False to suppress ins/upd events.
            resolver: Resolver handling for existing nodes with resolvers:
                - None (default): Raise error if node has resolver
                - False: Remove existing resolver and set value
                - BagResolver instance: Replace resolver with new one
            **kwargs: Additional attributes to set on the node.

        Returns:
            The created or updated BagNode.

        Raises:
            BagNodeException: If target node has a resolver and resolver param not provided.

        Example:
            >>> bag = Bag()
            >>> node = bag.set_item('a.b.c', 42)
            >>> node.value
            42
            >>> bag.set_item('a.b.d', 'hello', _attributes={'type': 'greeting'})
            >>> # Set a single attribute using ?attr syntax
            >>> bag.set_item('a.b.c?myattr', 'attr_value')
            >>> bag.get('a.b.c?myattr')  # 'attr_value'
            >>> # Fire an event (set then immediately reset to None)
            >>> bag.set_item('event', 'click', _fired=True)
            >>> bag['event']  # None
            >>> # Handle nodes with resolvers
            >>> bag['data'] = BagCbResolver(lambda: 'computed')
            >>> bag.set_item('data', 'new', resolver=False)  # Remove resolver
        """
        # Parse ?attr suffix from path
        attrname = None
        if "?" in path:
            path, attrname = path.rsplit("?", 1)
        if kwargs:
            _attributes = dict(_attributes or {})
            _attributes.update(kwargs)

        # If value is a resolver, extract it (legacy compatibility)
        if safe_is_instance(value, "genro_bag.resolver.BagResolver"):
            resolver = value
            value = None

        # Handle resolver.attributes if present
        if resolver is not None and hasattr(resolver, "attributes") and resolver.attributes:
            _attributes = dict(_attributes or ())
            _attributes.update(resolver.attributes)

        path = _normalize_path(path)
        result, label = self._htraverse(path, write_mode=True)
        obj = cast("Bag", result)

        if label is None or label.startswith("#"):
            raise BagException("Cannot create new node with #n syntax")

        if attrname:
            # ?attr syntax: set attribute on node (create if needed)
            node = cast("BagNode | None", obj._nodes.get(label))
            if node is None:
                # Create the node first with None value
                node = obj._nodes.set(
                    label,
                    None,
                    node_position,
                    attr=_attributes,
                    parent_bag=obj,
                    _reason=_reason,
                    do_trigger=do_trigger,
                )
            node.set_attr({attrname: value}, trigger=do_trigger)
            return node

        node = obj._nodes.set(
            label,
            value,
            node_position,
            attr=_attributes,
            resolver=resolver,
            parent_bag=obj,
            _updattr=_updattr,
            _remove_null_attributes=_remove_null_attributes,
            _reason=_reason,
            do_trigger=do_trigger,
        )

        if _fired:
            # Reset to None without triggering (event was already fired with the value)
            obj._nodes.set(label, None, parent_bag=obj, _reason=_reason, do_trigger=False)

        return node

    def __setitem__(self, path: str, value: Any) -> None:
        """Set value at path using bracket notation."""
        self.set_item(path, value)

    # -------------------- _pop (single level) --------------------------------

    def _pop(self, label: str, _reason: str | None = None) -> BagNode | None:
        """Internal pop by label at current level.

        Args:
            label: Node label to remove.
            _reason: Reason for deletion (for events).

        Returns:
            The removed BagNode, or None if not found.
        """
        p = self._nodes.index(label)
        if p >= 0:
            node = cast(BagNode, self._nodes.pop(p))
            if self.backref:
                self._on_node_deleted(node, p, reason=_reason)
            return node
        return None

    # -------------------- pop --------------------------------

    def pop(self, path: str, default: Any = None, _reason: str | None = None) -> Any:
        """Remove a node and return its value.

        Traverses to the path, removes the node, and returns its value.
        This is the method behind `del bag[path]`.

        Args:
            path: Hierarchical path to the node to remove.
            default: Value to return if path not found.
            _reason: Reason for deletion (for events).

        Returns:
            The value of the removed node, or default if not found.

        Example:
            >>> bag = Bag()
            >>> bag['a.b'] = 42
            >>> bag.pop('a.b')
            42
            >>> bag.pop('a.b', 'gone')
            'gone'
        """
        result = default
        obj, label = self._htraverse(path, static=True)
        if obj:
            n = obj._pop(label, _reason=_reason)
            if n:
                result = n.value
        return result

    del_item = pop
    __delitem__ = pop

    # -------------------- pop_node --------------------------------

    def pop_node(self, path: str, _reason: str | None = None) -> BagNode | None:
        """Remove and return the BagNode at a path.

        Like pop(), but returns the entire BagNode instead of just its value.
        Useful when you need access to the node's attributes after removal.

        Args:
            path: Hierarchical path to the node to remove.
            _reason: Reason for deletion (for events).

        Returns:
            The removed BagNode, or None if not found.

        Example:
            >>> bag = Bag()
            >>> bag.set_item('a', 42, _attributes={'type': 'int'})
            >>> node = bag.pop_node('a')
            >>> node.value
            42
            >>> node.attr
            {'type': 'int'}
        """
        result, label = self._htraverse(path, static=True)
        if result and label:
            obj = cast("Bag", result)
            n = obj._pop(label, _reason=_reason)
            if n:
                return n
        return None

    # -------------------- clear --------------------------------

    def clear(self) -> None:
        """Remove all nodes from this Bag.

        Empties the Bag completely. In backref mode, triggers delete events
        for all removed nodes.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> len(bag)
            2
            >>> bag.clear()
            >>> len(bag)
            0
        """
        old_nodes = list(self._nodes)
        self._nodes.clear()
        if self.backref:
            self._on_node_deleted(old_nodes, -1)

    def move(self, what: int | list[int], position: int, trigger: bool = True) -> None:
        """Move element(s) to a new position.

        Follows the same semantics as JavaScript moveNode:
        - If what is a list, all nodes at those indices are moved together
        - Nodes are removed in reverse order to preserve indices
        - All removed nodes are inserted at the target position
        - Events (del/ins) are fired for each node if trigger=True

        Args:
            what: Index or list of indices to move.
            position: Target index position.
            trigger: If True, fire del/ins events (default True).

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> bag['c'] = 3
            >>> bag.move(0, 2)  # move 'a' to position 2
            >>> list(bag.keys())
            ['b', 'c', 'a']
            >>> bag.move([0, 2], 1)  # move indices 0 and 2 to position 1
        """
        self._nodes.move(what, position, trigger=trigger)

    def as_dict(self, ascii: bool = False, lower: bool = False) -> dict[str, Any]:
        """Convert Bag to dict (first level only).

        Args:
            ascii: If True, convert keys to ASCII.
            lower: If True, convert keys to lowercase.
        """
        result = {}
        for el in self._nodes:
            key = el.label
            if ascii:
                key = str(key)
            if lower:
                key = key.lower()
            result[key] = el.value
        return result

    def setdefault(self, path: str, default: Any = None) -> Any:
        """Return value at path, setting it to default if not present."""
        node = self.get_node(path)
        if not node:
            self[path] = default
            return default
        return node.value  # type: ignore[union-attr]

    @property
    def nodes(self) -> list[BagNode]:
        """Property alias for get_nodes()."""
        return self.get_nodes()

    def node(self, key: str | int) -> BagNode | None:
        """Get a first-level node by label or index.

        Sync method for quick access to direct child nodes.
        Does not traverse paths or trigger resolvers.

        Args:
            key: Node label (str) or index (int).

        Returns:
            The BagNode if found, None otherwise.

        Example:
            >>> bag = Bag({'a': 1, 'b': 2})
            >>> bag.node('a').value
            1
            >>> bag.node(0).label
            'a'
        """
        return cast("BagNode | None", self._nodes[key])

    def set_attr(
        self,
        path: str | None = None,
        _attributes: dict | None = None,
        _remove_null_attributes: bool = True,
        **kwargs,
    ) -> None:
        """Set attributes on a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            _attributes: Dict of attributes to set.
            _remove_null_attributes: If True, remove attributes with None value.
            **kwargs: Additional attributes to set.
        """
        self.get_node(path, autocreate=True).set_attr(  # type: ignore[union-attr]
            attr=_attributes, _remove_null_attributes=_remove_null_attributes, **kwargs
        )

    def get_attr(
        self, path: str | None = None, attr: str | None = None, default: Any = None
    ) -> Any:
        """Get an attribute from a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            attr: Attribute name to get.
            default: Default value if node or attribute not found.

        Returns:
            Attribute value or default.
        """
        node = self.get_node(path)
        if node:
            return node.get_attr(label=attr, default=default)  # type: ignore[union-attr]
        return default

    def del_attr(self, path: str | None = None, *attrs: str) -> None:
        """Delete attributes from a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            *attrs: Attribute names to delete.
        """
        node = self.get_node(path)
        if node:
            node.del_attr(*attrs)  # type: ignore[union-attr]

    def get_inherited_attributes(self) -> dict[str, Any]:
        """Get inherited attributes from parent chain.

        Returns:
            Dict of attributes inherited from parent nodes.
        """
        if self.parent_node:
            return self.parent_node.get_inherited_attributes()
        return {}

    # -------------------------------------------------------------------------
    # Resolver Methods
    # -------------------------------------------------------------------------

    def get_resolver(self, path: str):
        """Get the resolver at the given path.

        Args:
            path: Path to the node.

        Returns:
            The resolver, or None if path doesn't exist or has no resolver.
        """
        node = self.get_node(path)
        return node.resolver if node else None  # type: ignore[union-attr]

    def set_resolver(self, path: str, resolver) -> None:
        """Set a resolver at the given path.

        Creates the node if it doesn't exist, with value=None.

        Args:
            path: Path to the node.
            resolver: The resolver to set.
        """
        self.set_item(path, None, resolver=resolver)

    def set_callback_item(self, path: str, callback: Callable, **kwargs) -> None:
        """Set a callback resolver at the given path.

        Shortcut for creating a BagCbResolver and setting it on a node.

        Args:
            path: Path to the node.
            callback: Callable that returns the value. Can be sync or async.
            **kwargs: Arguments passed to BagCbResolver constructor.
                Common kwargs:
                - cache_time: Cache duration in seconds (default 0, no cache).
                - read_only: If True, value not saved in node (default False).

        Note:
            The resolver is passed directly to set_item, which handles it
            via the resolver parameter (not as value).
        """
        resolver = BagCbResolver(callback, **kwargs)
        self.set_item(path, resolver)

    # -------------------- __str__ --------------------------------

    def __str__(self, _visited: dict | None = None) -> str:
        """Return formatted representation of bag contents.

        Uses static=True to avoid triggering resolvers.
        Handles circular references by tracking visited nodes.

        Example:
            >>> bag = Bag()
            >>> bag['name'] = 'test'
            >>> bag.set_item('count', 42, dtype='int')
            >>> print(bag)
            0 - (str) name: test
            1 - (int) count: 42  <dtype='int'>
        """
        if _visited is None:
            _visited = {}

        lines = []
        for idx, node in enumerate(self._nodes):
            value = node.get_value(static=True)

            # Format attributes
            attr = "<" + " ".join(f"{k}='{v}'" for k, v in node.attr.items()) + ">"
            if attr == "<>":
                attr = ""

            if isinstance(value, Bag):
                node_id = id(node)
                backref = "(*)" if value.backref else ""
                lines.append(f"{idx} - ({value.__class__.__name__}) {node.label}{backref}: {attr}")
                if node_id in _visited:
                    lines.append(f"    visited at :{_visited[node_id]}")
                else:
                    _visited[node_id] = node.label
                    inner = value.__str__(_visited)
                    lines.extend(f"    {line}" for line in inner.split("\n"))
            else:
                # Format type name
                type_name = type(value).__name__
                if type_name == "NoneType":
                    type_name = "None"
                if "." in type_name:
                    type_name = type_name.split(".")[-1]
                # Handle bytes
                if isinstance(value, bytes):
                    value = value.decode("UTF-8", "ignore")
                lines.append(f"{idx} - ({type_name}) {node.label}: {value}  {attr}")

        return "\n".join(lines)

    # -------------------- __iter__, __len__, __contains__, __call__ --------------------------------

    def __iter__(self):
        """Iterate over BagNodes.

        Yields BagNode objects in order, not values.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> for node in bag:
            ...     print(node.label, node.value)
            a 1
        """
        return iter(self._nodes)

    def __len__(self) -> int:
        """Return number of direct child nodes.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b.c'] = 2  # nested, but 'b' is one child
            >>> len(bag)
            2
        """
        return len(self._nodes)

    def __call__(self, what: str | None = None) -> Any:
        """Call syntax for quick access.

        Called with no argument, returns list of keys.
        Called with a path, returns value at that path.

        Args:
            what: Optional path to retrieve.

        Returns:
            List of keys if what is None, otherwise value at path.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> bag()
            ['a', 'b']
            >>> bag('a')
            1
        """
        if not what:
            return list(self.keys())
        return self[what]

    def __contains__(self, what: str) -> bool:
        """Check if a path or node exists in the Bag.

        The "in" operator can be used to test the existence of a key in a
        bag. Also nested keys are allowed.

        Args:
            what: Path to check, or a BagNode to check if it's in this Bag.

        Returns:
            True if the path/node exists, False otherwise.

        Example:
            >>> bag = Bag()
            >>> bag['a.b'] = 1
            >>> 'a.b' in bag
            True
            >>> 'a.c' in bag
            False
        """
        if isinstance(what, str):
            return bool(self.get_node(what))
        elif isinstance(what, BagNode):
            return what in list(self._nodes)
        else:
            return False

    def __eq__(self, other: object) -> bool:
        """Check equality with another Bag.

        Two Bags are equal if they have the same nodes in the same order.
        This comparison delegates to BagNodeContainer.__eq__ which in turn
        compares BagNodes (label, attr, value/resolver).

        Args:
            other: Object to compare with.

        Returns:
            True if equal, False otherwise.
        """
        if not isinstance(other, Bag):
            return False
        return self._nodes == other._nodes

    def __ne__(self, other: object) -> bool:
        """Check inequality with another Bag."""
        return not self.__eq__(other)

    # -------------------- deepcopy --------------------------------

    def deepcopy(self) -> Bag:
        """Return a deep copy of this Bag.

        Creates a new Bag with copies of all nodes. Nested Bags are
        recursively deep copied. Values are copied by reference unless
        they are Bags. Node attributes are copied as a new dict.

        Returns:
            A new Bag with copied nodes.

        Example:
            >>> bag = Bag({'a': 1, 'b': Bag({'c': 2})})
            >>> copy = bag.deepcopy()
            >>> copy['b.c'] = 3
            >>> bag['b.c']  # Original unchanged
            2
        """
        result = Bag()
        for node in self:
            value = node.static_value
            if isinstance(value, Bag):
                value = value.deepcopy()
            result.set_item(node.label, value, _attributes=dict(node.attr))
        return result

    # -------------------- pickle support --------------------------------

    def __getstate__(self) -> dict:
        """Return state for pickling."""
        self._make_picklable()
        return self.__dict__

    def __setstate__(self, state: dict) -> None:
        """Restore state after unpickling."""
        self.__dict__.update(state)
        self._restore_from_picklable()

    def _make_picklable(self) -> None:
        """Prepare Bag for pickling (internal)."""
        if self._backref:
            self._backref = "x"
        self.parent = None
        self.parent_node = None
        for node in self:
            node._parent_bag = None
            value = node.static_value
            if isinstance(value, Bag):
                value._make_picklable()

    def _restore_from_picklable(self) -> None:
        """Restore Bag from its picklable form (internal)."""
        if self._backref == "x":
            self.set_backref()
        else:
            for node in self:
                node._parent_bag = None
                value = node.static_value
                if isinstance(value, Bag):
                    value._restore_from_picklable()

    # -------------------- update --------------------------------

    def update(self, source: Bag | dict, ignore_none: bool = False) -> None:
        """Update this Bag with nodes from source.

        Merges nodes from source into this Bag. For existing labels,
        updates the value and merges attributes. For new labels, adds
        the node.

        Args:
            source: A Bag or dict to merge from.
            ignore_none: If True, don't overwrite existing values with None.

        Example:
            >>> bag = Bag({'a': 1, 'b': 2})
            >>> bag.update({'a': 10, 'c': 3})
            >>> bag['a'], bag['b'], bag['c']
            (10, 2, 3)
        """
        # Normalize to list of (label, value, attr)
        items: list[tuple[Any, Any, dict[str, Any]]]
        if isinstance(source, dict):
            items = [(k, v, {}) for k, v in source.items()]
        else:
            items = list(source.query(what="#k,#v,#a"))

        for label, value, attr in items:
            if label in self._nodes:
                curr_node = self._nodes[label]
                curr_node.attr.update(attr)
                curr_value = curr_node.static_value
                if isinstance(value, Bag) and isinstance(curr_value, Bag):
                    curr_value.update(value, ignore_none=ignore_none)
                else:
                    if not ignore_none or value is not None:
                        curr_node.value = value
            else:
                self.set_item(label, value, _attributes=attr)

    # -------------------- _get_node (single level) --------------------------------

    def _get_node(
        self, label: str, autocreate: bool = False, default: Any = None
    ) -> BagNode | None:
        """Internal get node by label at current level.

        Args:
            label: Node label to find.
            autocreate: If True, create node if not found.
            default: Default value for autocreated node.

        Returns:
            The BagNode, or None if not found and not autocreate.
        """
        p = self._nodes.index(label)
        node: BagNode | None
        if p >= 0:
            node = cast(BagNode, self._nodes[p])
        elif autocreate:
            i = len(self._nodes)
            node = self._nodes.set(label, default, parent_bag=self)
            if self.backref:
                self._on_node_inserted(node, i)
        else:
            node = None
        return node

    # -------------------- get_node --------------------------------

    def get_node(
        self,
        path: str | None = None,
        as_tuple: bool = False,
        autocreate: bool = False,
        default: Any = None,
        static: bool = True,
    ) -> BagNode | tuple[Bag, BagNode | None] | None:
        """Get the BagNode at a path.

        Unlike get_item which returns the value, this returns the BagNode itself,
        giving access to attributes and other node properties.

        By default does NOT trigger resolvers (static=True).
        Use static=False to trigger resolvers during traversal.

        Args:
            path: Hierarchical path. If None or empty, returns the parent_node
                (the node containing this Bag). Can also be an integer index.
            as_tuple: If True, return (container_bag, node) tuple.
            autocreate: If True, create node if not found.
            default: Default value for autocreated node.
            static: If False, trigger resolvers during traversal. Default True.

        Returns:
            The BagNode at the path, or None if not found.
            If as_tuple is True, returns (Bag, BagNode) tuple.

        Example:
            >>> bag = Bag()
            >>> bag.set_item('a', 42, _attributes={'type': 'int'})
            >>> node = bag.get_node('a')
            >>> node.value
            42
            >>> node.attr['type']
            'int'
        """
        if not path:
            return self.parent_node

        if isinstance(path, int):
            return cast("BagNode | None", self._nodes[path])

        result = self._htraverse(path, write_mode=autocreate, static=static)

        def finalize(obj_label):
            obj, label = obj_label
            if isinstance(obj, Bag):
                node = obj._get_node(label, autocreate, default)
                if as_tuple:
                    return (obj, node)
                return node
            return None

        return smartcontinuation(result, finalize)  # type: ignore[no-any-return]

    # -------------------- backref management --------------------------------

    def set_backref(self, node: BagNode | None = None, parent: Bag | None = None) -> None:
        """Force a Bag to a more strict structure (tree-leaf model).

        Enables backref mode which maintains parent references and
        propagates events up the hierarchy.

        Args:
            node: The BagNode that contains this Bag.
            parent: The parent Bag.
        """
        if self._backref is not True:
            self._backref = True
            self.parent = parent
            self.parent_node = node
            self._nodes._parent_bag = self
            for node in self:
                node.parent_bag = self

    def del_parent_ref(self) -> None:
        """Set False in the parent Bag reference of the relative Bag."""
        self.parent = None
        self._backref = False

    def clear_backref(self) -> None:
        """Clear all the set_backref() assumption."""
        if self._backref:
            self._backref = False
            self.parent = None
            self.parent_node = None
            self._nodes._parent_bag = None
            for node in self:
                node.parent_bag = None
                value = node.get_value(static=True)
                if isinstance(value, Bag):
                    value.clear_backref()

    # -------------------- event triggers --------------------------------

    def _on_node_changed(
        self,
        node: BagNode,
        pathlist: list,
        evt: str,
        oldvalue: Any = None,
        reason: str | None = None,
    ) -> None:
        """Trigger for node change events."""
        for s in list(self._upd_subscribers.values()):
            s(node=node, pathlist=pathlist, oldvalue=oldvalue, evt=evt, reason=reason)
        if self.parent and self.parent_node:
            self.parent._on_node_changed(
                node, [self.parent_node.label] + pathlist, evt, oldvalue, reason=reason
            )

    def _on_node_inserted(
        self, node: BagNode, ind: int, pathlist: list | None = None, reason: str | None = None
    ) -> None:
        """Trigger for node insert events."""
        parent = node.parent_bag
        if parent is not None and parent.backref and hasattr(node.value, "_htraverse"):
            node.value.set_backref(node=node, parent=parent)

        if pathlist is None:
            pathlist = []
        for s in list(self._ins_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt="ins", reason=reason)
        if self.parent and self.parent_node:
            self.parent._on_node_inserted(
                node, ind, [self.parent_node.label] + pathlist, reason=reason
            )

    def _on_node_deleted(
        self, node: Any, ind: int, pathlist: list | None = None, reason: str | None = None
    ) -> None:
        """Trigger for node delete events."""
        for s in list(self._del_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt="del", reason=reason)
        if self.parent and self.parent_node:
            if pathlist is None:
                pathlist = []
            self.parent._on_node_deleted(
                node, ind, [self.parent_node.label] + pathlist, reason=reason
            )

    # -------------------- subscription --------------------------------

    def _subscribe(self, subscriber_id: str, subscribers_dict: dict, callback: Any) -> None:
        """Internal subscribe helper."""
        if callback is not None:
            subscribers_dict[subscriber_id] = callback

    def subscribe(
        self,
        subscriber_id: str,
        update: Any = None,
        insert: Any = None,
        delete: Any = None,
        any: Any = None,
    ) -> None:
        """Provide a subscribing of a function to an event.

        Args:
            subscriber_id: Unique identifier for this subscription.
            update: Callback for update events.
            insert: Callback for insert events.
            delete: Callback for delete events.
            any: Callback for all events (update, insert, delete).
        """
        if not self.backref:
            self.set_backref()

        self._subscribe(subscriber_id, self._upd_subscribers, update or any)
        self._subscribe(subscriber_id, self._ins_subscribers, insert or any)
        self._subscribe(subscriber_id, self._del_subscribers, delete or any)

    def unsubscribe(
        self,
        subscriber_id: str,
        update: bool = False,
        insert: bool = False,
        delete: bool = False,
        any: bool = False,
    ) -> None:
        """Delete a subscription of an event.

        Args:
            subscriber_id: The subscription identifier to remove.
            update: Remove update subscription.
            insert: Remove insert subscription.
            delete: Remove delete subscription.
            any: Remove all subscriptions.
        """
        if update or any:
            self._upd_subscribers.pop(subscriber_id, None)
        if insert or any:
            self._ins_subscribers.pop(subscriber_id, None)
        if delete or any:
            self._del_subscribers.pop(subscriber_id, None)


class BagException(Exception):
    """Exception raised for Bag-specific errors.

    Raised when operations on a Bag fail due to invalid paths,
    illegal operations, or constraint violations.

    Example:
        - Attempting to autocreate with '#n' syntax for non-existent index
    """

    pass
