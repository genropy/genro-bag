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
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from genro_toolbox import smartasync, smartawait, smartsplit
from genro_toolbox.typeutils import safe_is_instance

from .bag_node import BagNode
from .bagnode_container import BagNodeContainer


def _normalize_path(path: str | list | Any) -> str | list:
    """Normalize a path for Bag access.

    If path is already a string or list, return it unchanged.
    Otherwise convert to string and replace '.' with '_'.
    """
    if isinstance(path, (str, list)):
        return path
    return str(path).replace('.', '_')


class Bag:
    """Hierarchical data container with path-based access.

    A Bag is an ordered container of BagNodes, accessible by label, numeric index,
    or hierarchical path. Nested elements can be accessed with dot-separated paths
    like 'a.b.c'.

    Unlike the original gnrbag, this implementation does NOT support duplicate labels.
    Each label at a given level must be unique.

    Attributes:
        _nodes: BagNodeContainer holding the BagNodes.
        _backref: If True, enables strict tree mode with parent references.
        _parent: Reference to parent Bag (only in backref mode).
        _parent_node: Reference to the BagNode containing this Bag.
        _upd_subscribers: Callbacks for update events.
        _ins_subscribers: Callbacks for insert events.
        _del_subscribers: Callbacks for delete events.
        _modified: Tracks modification state.
        _root_attributes: Attributes for the root bag.
    """

    def __init__(self, source: dict[str, Any] | None = None):
        """Create a new Bag.

        Args:
            source: Optional dict to initialize from. Keys become labels,
                values become node values.

        Example:
            >>> bag = Bag({'a': 1, 'b': 2})
            >>> bag['a']
            1
        """
        self._nodes: BagNodeContainer = BagNodeContainer()
        self._backref: bool = False
        self._parent: Bag | None = None
        self._parent_node: BagNode | None = None
        self._upd_subscribers: dict = {}
        self._ins_subscribers: dict = {}
        self._del_subscribers: dict = {}
        self._modified: bool | None = None
        self._root_attributes: dict | None = None

        if source:
            self.fill_from(source)

    def fill_from(self, source: dict[str, Any] | str | Bag) -> None:
        """Fill bag from a source.

        Populates the bag with data from various sources:
        - dict: Keys become labels, values become node values
        - str (file path): Load from file based on extension:
            - .xml: Parse as XML
            - .bag.json: Parse as TYTX JSON
            - .bag.mp: Parse as TYTX MessagePack
        - Bag: Copy nodes from another Bag

        Existing nodes are cleared first.

        Args:
            source: Data source (dict, file path, or Bag).

        Example:
            >>> bag = Bag()
            >>> bag.fill_from({'x': 1, 'y': {'z': 2}})
            >>> bag['y.z']
            2
            >>>
            >>> bag2 = Bag()
            >>> bag2.fill_from('/path/to/data.bag.json')
        """
        if isinstance(source, str):
            self._fill_from_file(source)
        elif isinstance(source, Bag):
            self._fill_from_bag(source)
        elif isinstance(source, dict):
            self._fill_from_dict(source)

    def _fill_from_file(self, path: str) -> None:
        """Load bag contents from a file.

        Detects format from file extension:
        - .bag.json: TYTX JSON format
        - .bag.mp: TYTX MessagePack format
        - .xml: XML format (with auto-detect for legacy GenRoBag)

        Args:
            path: Path to the file to load.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file extension is not recognized.
        """
        import os

        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        # Detect format from extension
        if path.endswith('.bag.json'):
            with open(path, encoding='utf-8') as f:
                data = f.read()
            from .serialization import from_tytx
            loaded = from_tytx(data, transport='json')
            self._fill_from_bag(loaded)

        elif path.endswith('.bag.mp'):
            with open(path, 'rb') as f:
                data = f.read()
            from .serialization import from_tytx
            loaded = from_tytx(data, transport='msgpack')
            self._fill_from_bag(loaded)

        elif path.endswith('.xml'):
            with open(path, encoding='utf-8') as f:
                data = f.read()
            from .bag_xml import BagXmlParser
            loaded = BagXmlParser.parse(data)
            self._fill_from_bag(loaded)

        else:
            raise ValueError(
                f"Unrecognized file extension: {path}. "
                "Supported: .bag.json, .bag.mp, .xml"
            )

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
    @smartasync
    async def from_url(cls, url: str, timeout: int = 30) -> Bag:
        """Load Bag from URL (async-capable).

        Fetches content from URL and parses based on content type or URL extension.
        Works in both sync and async contexts via @smartasync.

        Args:
            url: HTTP/HTTPS URL to fetch.
            timeout: Request timeout in seconds. Default 30.

        Returns:
            Bag: Parsed content as Bag.

        Raises:
            httpx.HTTPError: If request fails.
            ValueError: If content format is not recognized.

        Example:
            >>> # Sync context
            >>> bag = Bag.from_url('https://example.com/data.xml')
            >>>
            >>> # Async context
            >>> bag = await Bag.from_url('https://example.com/data.xml')
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()
            content = response.content

        return cls._parse_content(content, url)

    @classmethod
    def _parse_content(cls, content: bytes, source_hint: str) -> Bag:
        """Parse content bytes into a Bag based on format detection.

        Args:
            content: Raw bytes to parse.
            source_hint: URL or filename for format detection.

        Returns:
            Bag: Parsed content.

        Raises:
            ValueError: If format cannot be detected or parsed.
        """
        source_lower = source_hint.lower().split('?')[0]  # Remove query string

        # Try based on extension/hint
        if source_lower.endswith('.xml') or content.strip().startswith(b'<?xml') or content.strip().startswith(b'<'):
            from .bag_xml import BagXmlParser
            return BagXmlParser.parse(content)

        if source_lower.endswith('.json') or source_lower.endswith('.bag.json'):
            from .serialization import from_tytx
            return from_tytx(content, transport='json')

        if source_lower.endswith('.bag.mp'):
            from .serialization import from_tytx
            return from_tytx(content, transport='msgpack')

        # Auto-detect from content
        try:
            from .bag_xml import BagXmlParser
            return BagXmlParser.parse(content)
        except Exception:
            pass

        try:
            from .serialization import from_tytx
            return from_tytx(content, transport='json')
        except Exception:
            pass

        raise ValueError(f"Cannot parse content from {source_hint}. Unknown format.")

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
        return self._backref

    @property
    def fullpath(self) -> str | None:
        """Full path from root Bag to this Bag.

        Returns the dot-separated path from the root of the hierarchy to this
        Bag. Returns None if backref mode is not enabled or if this is the root.
        """
        if self.parent is not None:
            parent_fullpath = self.parent.fullpath
            if parent_fullpath:
                return f'{parent_fullpath}.{self.parent_node.label}'
            else:
                return self.parent_node.label
        return None

    @property
    def attributes(self) -> dict:
        """Attributes of the parent node containing this Bag.

        Returns the attributes dict of the BagNode that contains this Bag.
        Returns an empty dict if this is a standalone Bag with no parent node.
        """
        if self.parent_node is not None:
            return self.parent_node.get_attr()
        return {}

    @property
    def root_attributes(self) -> dict | None:
        """Attributes for the root Bag."""
        return self._root_attributes

    @root_attributes.setter
    def root_attributes(self, attrs: dict) -> None:
        self._root_attributes = dict(attrs)

    @property
    def modified(self) -> bool | None:
        """Modification tracking flag (None=disabled, False=clean, True=modified)."""
        return self._modified

    @modified.setter
    def modified(self, value: bool | None) -> None:
        if value is None:
            self._modified = None
            self.unsubscribe('_modified_tracker_', any=True)
        else:
            if self._modified is None:
                self.subscribe('_modified_tracker_', any=self._on_modified)
            self._modified = value

    def _on_modified(self, **kwargs) -> None:
        self._modified = True

    # -------------------- _htraverse helpers --------------------------------

    def _htraverse_before(self, path: str | list) -> tuple[Bag, list]:
        """Parse path and handle #parent navigation.

        First phase of path traversal: converts path to list, handles '../' alias,
        and processes any leading #parent segments.

        Args:
            path: Dot-separated path like 'a.b.c' or list ['a', 'b', 'c'].

        Returns:
            Tuple of (curr, pathlist) where:
                - curr: Starting Bag (may have moved up via #parent)
                - pathlist: Remaining path segments to process
        """
        curr = self

        if isinstance(path, str):
            path = path.replace('../', '#parent.')
            pathlist = [x for x in smartsplit(path, '.') if x]
        else:
            pathlist = list(path)

        # handle parent reference #parent at the beginning
        while pathlist and pathlist[0] == '#parent':
            pathlist.pop(0)
            curr = curr.parent

        return curr, pathlist

    def _htraverse_after(self, curr: Bag, pathlist: list,
                         write_mode: bool = False) -> tuple[Any, str]:
        """Finalize traversal and handle write_mode autocreate.

        Final phase of path traversal: handles empty paths, checks for
        incomplete paths in read mode, and creates intermediate nodes in write mode.

        Args:
            curr: Current Bag position after traversal.
            pathlist: Remaining path segments.
            write_mode: If True, create intermediate Bags for missing segments.

        Returns:
            Tuple of (container, label) where:
                - container: The Bag containing the final element, or None
                - label: The final path segment

        Raises:
            BagException: If write_mode and path uses '#n' for non-existent index.
        """
        if not pathlist:
            return curr, ''

        # In read mode, if we have more than one segment left, path doesn't exist
        if not write_mode:
            if len(pathlist) > 1:
                return None, None
            return curr, pathlist[0]

        # Write mode: create intermediate nodes
        # Note: _nodes.set handles _on_node_inserted when parent_bag.backref is True
        while len(pathlist) > 1:
            label = pathlist.pop(0)
            if label.startswith('#'):
                raise BagException('Not existing index in #n syntax')
            new_bag = curr.__class__()
            curr._nodes.set(label, new_bag, parent_bag=curr)
            curr = new_bag

        return curr, pathlist[0]

    # -------------------- _traverse_until (sync) --------------------------------

    def _traverse_until(self, curr: Bag, pathlist: list) -> tuple[Bag, list]:
        """Traverse path segments synchronously (static mode, no resolver trigger).

        Walks the path as far as possible without triggering resolvers.
        Used by sync methods that always use static=True.

        Args:
            curr: Starting Bag position.
            pathlist: Path segments to traverse.

        Returns:
            Tuple of (container, remaining_path) where:
                - container: The last valid Bag reached
                - remaining_path: List of path segments not yet traversed
        """
        while len(pathlist) > 1 and isinstance(curr, Bag):
            node = curr._nodes[pathlist[0]]
            if node:
                pathlist.pop(0)
                curr = node.get_value(static=True)
            else:
                break

        return (curr, pathlist)

    # -------------------- _async_traverse_until --------------------------------

    @smartasync
    async def _async_traverse_until(self, curr: Bag, pathlist: list,
                                    static: bool = False) -> tuple[Bag, list]:
        """Traverse path segments with async support (may trigger resolvers).

        Walks the path as far as possible. When static=False, may trigger
        async resolvers during traversal.

        Args:
            curr: Starting Bag position.
            pathlist: Path segments to traverse.
            static: If True, don't trigger resolvers.

        Returns:
            Tuple of (container, remaining_path) where:
                - container: The last valid Bag reached
                - remaining_path: List of path segments not yet traversed
        """
        while len(pathlist) > 1 and isinstance(curr, Bag):
            node = curr._nodes[pathlist[0]]
            if node:
                pathlist.pop(0)
                curr = await smartawait(node.get_value(static=static))
            else:
                break

        return (curr, pathlist)

    # -------------------- _htraverse (sync) --------------------------------

    def _htraverse(self, path: str | list, write_mode: bool = False) -> tuple[Any, str]:
        """Traverse a hierarchical path synchronously (static mode).

        Sync version that never triggers resolvers. Used by set_item, pop, etc.

        Args:
            path: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            write_mode: If True, create intermediate Bags for missing segments.

        Returns:
            Tuple of (container, label) where:
                - container: The Bag containing the final element, or None
                - label: The final path segment
        """
        curr, pathlist = self._htraverse_before(path)
        if not pathlist:
            return curr, ''
        curr, pathlist = self._traverse_until(curr, pathlist)
        return self._htraverse_after(curr, pathlist, write_mode)

    # -------------------- _async_htraverse --------------------------------

    @smartasync
    async def _async_htraverse(self, path: str | list, write_mode: bool = False,
                               static: bool = False) -> tuple[Any, str]:
        """Traverse a hierarchical path with async support.

        Async version that may trigger resolvers when static=False.
        Used by get_item, get_node when resolver triggering is needed.

        Args:
            path: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            write_mode: If True, create intermediate Bags for missing segments.
            static: If True, don't trigger resolvers during traversal.

        Returns:
            Tuple of (container, label) where:
                - container: The Bag containing the final element, or None
                - label: The final path segment
        """
        curr, pathlist = self._htraverse_before(path)
        if not pathlist:
            return curr, ''
        curr, pathlist = await smartawait(self._async_traverse_until(curr, pathlist, static=static))
        return self._htraverse_after(curr, pathlist, write_mode)

    # -------------------- get (single level) --------------------------------

    def get(self, label: str, default: Any = None) -> Any:
        """Get value at a single level (no path traversal).

        Unlike get_item/`__getitem__`, this method only looks at direct children
        of this Bag. It does not traverse paths with dots.

        Args:
            label: Node label to look up. Can be a string label or '#n' index.
                Supports '?attr' suffix to get a node attribute instead of value.
            default: Value to return if label not found.

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
        if label == '#parent':
            return self.parent
        attrname = None
        if '?' in label:
            label, attrname = label.split('?')
        node = self._nodes.get(label)
        if not node:
            return default
        return node.get_attr(attrname) if attrname else node.get_value()

    # -------------------- get_item --------------------------------

    @smartasync
    async def get_item(self, path: str, default: Any = None,
                       static: bool = False) -> Any:
        """Get value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path and returns
        the value at the final location.

        Decorated with @smartasync: can be called from sync or async context.
        In async context with async resolvers, use `await bag.get_item(path)`.

        Args:
            path: Hierarchical path like 'a.b.c'. Empty path returns self.
                Supports '?attr' suffix to get attribute instead of value.
            default: Value to return if path not found.
            static: If True, don't trigger resolvers during traversal.

        Returns:
            The value at the path if found, otherwise default.

        Example:
            >>> bag = Bag()
            >>> bag['config.db.host'] = 'localhost'
            >>> bag.get_item('config.db.host')
            'localhost'
            >>> bag['config.db.host']  # static=True, no resolver trigger
            'localhost'
            >>> await bag.get_item('path.with.resolver')  # triggers resolver
        """
        if not path:
            return self

        path = _normalize_path(path)

        obj, label = await smartawait(self._async_htraverse(path, static=static))

        if isinstance(obj, Bag):
            return obj.get(label, default)

        if hasattr(obj, 'get'):
            return obj.get(label, default)
        else:
            return default

    def __getitem__(self, path: str) -> Any:
        """Get value at path using sync _htraverse (no resolver trigger).

        Use bag.get_item(path) or await bag.get_item(path) to trigger resolvers.
        """
        path = _normalize_path(path)
        obj, label = self._htraverse(path)
        if isinstance(obj, Bag):
            return obj.get(label)
        if hasattr(obj, 'get'):
            return obj.get(label)
        return None

    # -------------------- set_item --------------------------------

    def set_item(self, path: str, value: Any, _attributes: dict | None = None,
                 _position: str | None = None,
                 _updattr: bool = False, _remove_null_attributes: bool = True,
                 _reason: str | None = None, resolver=None, **kwargs) -> None:
        """Set value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path, creating
        intermediate Bags as needed, and sets the value at the final location.
        This is the method behind `bag[path] = value`.

        This method is synchronous and never triggers resolvers during traversal.

        If the path already exists, the value is updated. If it doesn't exist,
        a new node is created at the specified position.

        Args:
            path: Hierarchical path like 'a.b.c'. Empty path is ignored.
            value: Value to set at the path.
            _attributes: Optional dict of attributes to set on the node.
            _position: Position for new nodes. Supports:
                - '>': Append at end (default)
                - '<': Insert at beginning
                - '#n': Insert at index n
                - '<label': Insert before label
                - '>label': Insert after label
            _updattr: If True, update attributes instead of replacing.
            _remove_null_attributes: If True, remove None attributes.
            _reason: Reason for the change (for events).
            **kwargs: Additional attributes to set on the node.

        Example:
            >>> bag = Bag()
            >>> bag.set_item('a.b.c', 42)
            >>> bag['a.b.c']
            42
            >>> bag.set_item('a.b.d', 'hello', _attributes={'type': 'greeting'})
        """
        if kwargs:
            _attributes = dict(_attributes or {})
            _attributes.update(kwargs)

        # Se value è un resolver, estrailo (legacy compatibility)
        if safe_is_instance(value, "genro_bag.resolver.BagResolver"):
            resolver = value
            value = None

        # Gestisci resolver.attributes se presente
        if resolver is not None and hasattr(resolver, 'attributes') and resolver.attributes:
            _attributes = dict(_attributes or ())
            _attributes.update(resolver.attributes)

        path = _normalize_path(path)
        obj, label = self._htraverse(path, write_mode=True)

        if label.startswith('#'):
            raise BagException('Cannot create new node with #n syntax')

        obj._nodes.set(label, value, _position,
                      attr=_attributes, resolver=resolver,
                      parent_bag=obj,
                      _updattr=_updattr,
                      _remove_null_attributes=_remove_null_attributes,
                      _reason=_reason)

    def __setitem__(self, path: str, value: Any) -> None:
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
            node = self._nodes.pop(p)
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
        obj, label = self._htraverse(path)
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
        obj, label = self._htraverse(path)
        if obj:
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

    # -------------------- keys, values, items --------------------------------

    def keys(self, iter: bool = False) -> list[str]:
        """Return node labels in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iterkeys() from Python 2 - use keys(iter=True) instead.
        """
        return self._nodes.keys(iter=iter)

    def values(self, iter: bool = False) -> list[Any]:
        """Return node values in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces itervalues() from Python 2 - use values(iter=True) instead.
        """
        return self._nodes.values(iter=iter)

    def items(self, iter: bool = False) -> list[tuple[str, Any]]:
        """Return (label, value) tuples in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iteritems() from Python 2 - use items(iter=True) instead.
        """
        return self._nodes.items(iter=iter)

    def setdefault(self, path: str, default: Any = None) -> Any:
        """Return value at path, setting it to default if not present."""
        node = self.get_node(path)
        if not node:
            self[path] = default
            return default
        return node.value

    # -------------------- get_nodes, digest --------------------------------

    def get_nodes(self, condition: Any = None) -> list[BagNode]:
        """Get the actual list of nodes contained in the Bag.

        The get_nodes method works as the filter of a list.

        Args:
            condition: Optional callable that takes a BagNode and returns bool.

        Returns:
            List of BagNodes, optionally filtered by condition.
        """
        if not condition:
            return list(self._nodes)
        else:
            return [n for n in self._nodes if condition(n)]

    @property
    def nodes(self) -> list[BagNode]:
        """Property alias for get_nodes()."""
        return self.get_nodes()

    def get_node_by_attr(self, attr: str, value: Any) -> BagNode | None:
        """Return the first BagNode with the requested attribute value.

        Searches recursively through the Bag hierarchy (breadth-first at each level).

        Args:
            attr: Attribute name to search.
            value: Attribute value to match.

        Returns:
            BagNode if found, None otherwise.
        """
        sub_bags = []
        for node in self._nodes:
            if node.has_attr(attr, value):
                return node
            if isinstance(node.value, Bag):
                sub_bags.append(node)

        for node in sub_bags:
            found = node.value.get_node_by_attr(attr, value)
            if found:
                return found

        return None

    def get_node_by_value(self, key: str, value: Any) -> BagNode | None:
        """Return the first BagNode whose value contains key=value.

        Searches only direct children (not recursive).
        The node's value must be dict-like (Bag or dict).

        Args:
            key: Key to look for in node.value.
            value: Value to match.

        Returns:
            BagNode if found, None otherwise.
        """
        for node in self._nodes:
            node_value = node.value
            if node_value and node_value[key] == value:
                return node
        return None

    def set_attr(self, path: str | None = None, _attributes: dict | None = None,
                 _remove_null_attributes: bool = True, **kwargs) -> None:
        """Set attributes on a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            _attributes: Dict of attributes to set.
            _remove_null_attributes: If True, remove attributes with None value.
            **kwargs: Additional attributes to set.
        """
        self.get_node(path, autocreate=True, static=True).set_attr(
            attr=_attributes, _remove_null_attributes=_remove_null_attributes, **kwargs
        )

    def get_attr(self, path: str | None = None, attr: str | None = None,
                 default: Any = None) -> Any:
        """Get an attribute from a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            attr: Attribute name to get.
            default: Default value if node or attribute not found.

        Returns:
            Attribute value or default.
        """
        node = self.get_node(path, static=True)
        if node:
            return node.get_attr(label=attr, default=default)
        return default

    def del_attr(self, path: str | None = None, *attrs: str) -> None:
        """Delete attributes from a node at the given path.

        Args:
            path: Path to the node. If None, uses parent_node.
            *attrs: Attribute names to delete.
        """
        node = self.get_node(path, static=True)
        if node:
            node.del_attr(*attrs)

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
        node = self.get_node(path, static=True)
        return node.resolver if node else None

    def set_resolver(self, path: str, resolver) -> None:
        """Set a resolver at the given path.

        Creates the node if it doesn't exist, with value=None.

        Args:
            path: Path to the node.
            resolver: The resolver to set.
        """
        self.set_item(path, None, resolver=resolver)

    def sort(self, key: str | Callable = '#k:a') -> Bag:
        """Sort nodes in place.

        Args:
            key: Sort specification string or callable.
                If callable, used directly as key function for sort.
                If string, format is 'criterion:mode' or multiple 'c1:m1,c2:m2'.

                Criteria:
                - '#k': sort by label
                - '#v': sort by value
                - '#a.attrname': sort by attribute
                - 'fieldname': sort by field in value (if value is dict/Bag)

                Modes:
                - 'a': ascending, case-insensitive (default)
                - 'A': ascending, case-sensitive
                - 'd': descending, case-insensitive
                - 'D': descending, case-sensitive

        Returns:
            Self (for chaining).

        Examples:
            >>> bag.sort('#k')           # by label ascending
            >>> bag.sort('#k:d')         # by label descending
            >>> bag.sort('#v:A')         # by value ascending, case-sensitive
            >>> bag.sort('#a.name:a')    # by attribute 'name'
            >>> bag.sort('field:d')      # by field in value
            >>> bag.sort('#k:a,#v:d')    # multi-level sort
            >>> bag.sort(lambda n: n.value)  # custom key function
        """
        def sort_key(value: Any, case_insensitive: bool) -> tuple:
            """Create sort key handling None and case sensitivity."""
            if value is None:
                return (1, '')  # None values sort last
            if case_insensitive and isinstance(value, str):
                return (0, value.lower())
            return (0, value)

        if callable(key):
            self._nodes.sort(key=key)
        else:
            levels = key.split(',')
            levels.reverse()  # process in reverse for stable multi-level sort
            for level in levels:
                if ':' in level:
                    what, mode = level.split(':', 1)
                else:
                    what = level
                    mode = 'a'
                what = what.strip()
                mode = mode.strip()

                reverse = mode in ('d', 'D')
                case_insensitive = mode in ('a', 'd')

                if what.lower() == '#k':
                    self._nodes.sort(
                        key=lambda n: sort_key(n.label, case_insensitive),
                        reverse=reverse
                    )
                elif what.lower() == '#v':
                    self._nodes.sort(
                        key=lambda n: sort_key(n.value, case_insensitive),
                        reverse=reverse
                    )
                elif what.lower().startswith('#a.'):
                    attrname = what[3:]
                    self._nodes.sort(
                        key=lambda n, attr=attrname: sort_key(
                            n.get_attr(attr), case_insensitive
                        ),
                        reverse=reverse
                    )
                else:
                    # Sort by field in value
                    self._nodes.sort(
                        key=lambda n, field=what: sort_key(
                            n.value[field] if n.value else None, case_insensitive
                        ),
                        reverse=reverse
                    )
        return self

    def sum(self, what: str = '#v', condition: Callable[[BagNode], bool] | None = None
            ) -> float | list[float]:
        """Sum values or attributes.

        Args:
            what: What to sum (same syntax as digest).
                - '#v': sum values
                - '#a.attrname': sum attribute
                - '#v,#a.price': multiple sums (returns list)
            condition: Optional callable filter (receives BagNode, returns bool).

        Returns:
            Sum as float, or list of floats if multiple what specs.

        Examples:
            >>> bag.sum()                    # sum all values
            >>> bag.sum('#a.price')          # sum 'price' attribute
            >>> bag.sum('#v,#a.qty')         # [sum_values, sum_qty]
            >>> bag.sum('#v', lambda n: n.get_attr('active'))  # filtered sum
        """
        if ',' in what:
            return [
                sum(v or 0 for v in self.digest(w.strip(), condition))
                for w in what.split(',')
            ]
        return sum(v or 0 for v in self.digest(what, condition))

    def digest(self, what: str | list | None = None, condition: Any = None,
               as_columns: bool = False) -> list:
        """Return a list of tuples with keys/values/attributes of Bag elements.

        Args:
            what: String of special keys separated by comma, or list of keys.
                Special keys:
                - '#k': label of each item
                - '#v': value of each item
                - '#v.path': inner values of each item
                - '#__v': static value (bypassing resolver)
                - '#a': all attributes of each item
                - '#a.attrname': specific attribute for each item
                - callable: custom function applied to each node
            condition: Optional callable filter (receives BagNode, returns bool).
            as_columns: If True, return list of lists. If False, return list of tuples.

        Returns:
            List of tuples (or list of lists if as_columns=True).

        Example:
            >>> bag.digest('#k,#a.createdOn,#a.createdBy')
            [('letter_to_mark', '10-7-2003', 'Jack'), ...]
        """
        if not what:
            what = '#k,#v,#a'
        if isinstance(what, str):
            if ':' in what:
                where, what = what.split(':')
                obj = self[where]
            else:
                obj = self
            whatsplit = [x.strip() for x in what.split(',')]
        else:
            whatsplit = what
            obj = self
        result = []
        nodes = obj.get_nodes(condition)
        for w in whatsplit:
            if w == '#k':
                result.append([x.label for x in nodes])
            elif callable(w):
                result.append([w(x) for x in nodes])
            elif w == '#v':
                result.append([x.value for x in nodes])
            elif w.startswith('#v.'):
                w, path = w.split('.', 1)
                result.append([x.value[path] for x in nodes if hasattr(x.value, 'get_item')])
            elif w == '#__v':
                result.append([x.static_value for x in nodes])
            elif w.startswith('#a'):
                attr = None
                if '.' in w:
                    w, attr = w.split('.', 1)
                if w == '#a':
                    result.append([x.get_attr(attr) for x in nodes])
            else:
                result.append([x.value[w] for x in nodes])
        if as_columns:
            return result
        if len(result) == 1:
            return result.pop()
        return list(zip(*result, strict=False))

    def columns(self, cols: str | list, attr_mode: bool = False) -> list:
        """Return digest result as columns.

        Args:
            cols: Column names as comma-separated string or list.
            attr_mode: If True, prefix columns with '#a.' for attribute access.

        Returns:
            List of lists (columns).
        """
        if isinstance(cols, str):
            cols = cols.split(',')
        mode = ''
        if attr_mode:
            mode = '#a.'
        what = ','.join([f'{mode}{col}' for col in cols])
        return self.digest(what, as_columns=True)

    # -------------------- walk --------------------------------

    def walk(self, callback: Callable[[BagNode], Any] | None = None,
             _mode: str = 'static', **kwargs) -> Iterator[tuple[str, BagNode]] | Any:
        """Walk the tree depth-first.

        Two modes of operation:

        1. **Generator mode** (no callback): Returns a generator yielding
           (path, node) tuples for all nodes in the tree.

        2. **Legacy callback mode**: Calls callback(node, **kwargs) for each
           node. Supports early exit (if callback returns truthy value),
           _pathlist and _indexlist kwargs for path tracking.

        Args:
            callback: If None, return generator of (path, node) tuples.
                If provided, call callback(node, **kwargs) for each node.
            _mode: For callback mode only. 'static' (default) doesn't trigger
                resolvers, other values ('deep', '') trigger resolvers.
            **kwargs: Passed to callback. Special keys:
                - _pathlist: list of labels from root (auto-updated)
                - _indexlist: list of indices from root (auto-updated)

        Returns:
            Generator of (path, node) if callback is None.
            If callback provided: value returned by callback if truthy, else None.

        Examples:
            >>> # Generator mode (modern)
            >>> for path, node in bag.walk():
            ...     print(f"{path}: {node.value}")

            >>> # Early exit with generator
            >>> for path, node in bag.walk():
            ...     if node.get_attr('id') == 'target':
            ...         found = node
            ...         break

            >>> # Legacy callback mode
            >>> bag.walk(my_callback, _pathlist=[])
        """
        if callback is not None:
            # Legacy callback mode
            for idx, node in enumerate(self._nodes):
                kw = dict(kwargs)
                if '_pathlist' in kwargs:
                    kw['_pathlist'] = kwargs['_pathlist'] + [node.label]
                if '_indexlist' in kwargs:
                    kw['_indexlist'] = kwargs['_indexlist'] + [idx]

                result = callback(node, **kw)
                if result:
                    return result

                value = node.get_value(static=(_mode == 'static'))
                if isinstance(value, Bag):
                    result = value.walk(callback, _mode=_mode, **kw)
                    if result:
                        return result
            return None

        # Generator mode
        def _walk_gen(bag: Bag, prefix: str) -> Iterator[tuple[str, BagNode]]:
            for node in bag._nodes:
                path = f"{prefix}.{node.label}" if prefix else node.label
                yield path, node
                if isinstance(node.value, Bag):
                    yield from _walk_gen(node.value, path)

        return _walk_gen(self, "")

    # -------------------- serialization --------------------------------

    def to_tytx(
        self,
        transport: str = "json",
        filename: str | None = None,
        compact: bool = False,
    ) -> str | bytes | None:
        """Serialize to TYTX format.

        Args:
            transport: 'json' (.jbag), 'xml' (.xbag), or 'msgpack' (.mpbag).
            filename: If provided, write to file (extension added automatically).
                If None, return serialized data.
            compact: Use numeric parent codes instead of path strings.

        Returns:
            Serialized data if filename is None, else None.

        See serialization.to_tytx() for full documentation.
        """
        from .serialization import to_tytx
        return to_tytx(self, transport=transport, filename=filename, compact=compact)

    @classmethod
    def from_tytx(
        cls,
        data: str | bytes,
        transport: str = "json",
    ) -> Bag:
        """Deserialize from TYTX format.

        Args:
            data: Serialized data from to_tytx().
            transport: Format matching serialization ('json', 'xml', 'msgpack').

        Returns:
            Reconstructed Bag.

        See serialization.from_tytx() for full documentation.
        """
        from .serialization import from_tytx
        return from_tytx(data, transport=transport)

    def to_xml(
        self,
        filename: str | None = None,
        encoding: str = 'UTF-8',
        doc_header: bool | str | None = None,
        pretty: bool = False,
        self_closed_tags: list[str] | None = None,
    ) -> str | None:
        """Serialize to XML format.

        All values are converted to strings without type information.
        For type-preserving serialization, use to_tytx() instead.

        Args:
            filename: If provided, write to file. If None, return XML string.
            encoding: XML encoding (default 'UTF-8').
            doc_header: XML declaration (True for auto, False/None for none, str for custom).
            pretty: If True, format with indentation.
            self_closed_tags: List of tags to self-close when empty.

        Returns:
            XML string if filename is None, else None.

        Example:
            >>> bag = Bag()
            >>> bag['name'] = 'test'
            >>> bag['count'] = 42
            >>> bag.to_xml()
            '<name>test</name><count>42</count>'
        """
        from .bag_xml import BagXmlSerializer

        return BagXmlSerializer.serialize(
            self,
            filename=filename,
            encoding=encoding,
            doc_header=doc_header,
            pretty=pretty,
            self_closed_tags=self_closed_tags,
        )

    @classmethod
    def from_xml(
        cls,
        source: str | bytes,
        empty: Callable[[], Any] | None = None,
    ) -> Bag:
        """Deserialize from XML format.

        Automatically detects and handles legacy GenRoBag format:
        - Decodes `_T` attribute for value types
        - Decodes `::TYPE` suffix in attribute values (TYTX encoding)
        - Handles `<GenRoBag>` root wrapper element

        For plain XML without type markers, values remain as strings.

        Args:
            source: XML string or bytes to parse.
            empty: Factory function for empty element values.

        Returns:
            Reconstructed Bag.

        Example:
            >>> # Plain XML
            >>> bag = Bag.from_xml('<root><name>test</name></root>')
            >>> bag['root']['name']
            'test'

            >>> # Legacy GenRoBag format (auto-detected)
            >>> bag = Bag.from_xml('<GenRoBag><count _T="L">42</count></GenRoBag>')
            >>> bag['count']
            42
        """
        from .bag_xml import BagXmlParser

        return BagXmlParser.parse(source, empty=empty)

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
            attr = '<' + ' '.join(f"{k}='{v}'" for k, v in node.attr.items()) + '>'
            if attr == '<>':
                attr = ''

            if isinstance(value, Bag):
                node_id = id(node)
                backref = '(*)' if value.backref else ''
                lines.append(f"{idx} - ({value.__class__.__name__}) {node.label}{backref}: {attr}")
                if node_id in _visited:
                    lines.append(f"    visited at :{_visited[node_id]}")
                else:
                    _visited[node_id] = node.label
                    inner = value.__str__(_visited)
                    lines.extend(f"    {line}" for line in inner.split('\n'))
            else:
                # Format type name
                type_name = type(value).__name__
                if type_name == 'NoneType':
                    type_name = 'None'
                if '.' in type_name:
                    type_name = type_name.split('.')[-1]
                # Handle bytes
                if isinstance(value, bytes):
                    value = value.decode('UTF-8', 'ignore')
                lines.append(f"{idx} - ({type_name}) {node.label}: {value}  {attr}")

        return '\n'.join(lines)

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
        they are Bags.

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
            result.set_item(node.label, value, attr=dict(node.attr))
        return result

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
        if isinstance(source, dict):
            items = [(k, v, {}) for k, v in source.items()]
        else:
            keys, values, attrs = source.digest('#k', '#v', '#a')
            items = list(zip(keys, values, attrs, strict=True))

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
                self.set_item(label, value, attr=attr)

    # -------------------- _get_node (single level) --------------------------------

    def _get_node(self, label: str, autocreate: bool = False,
                  default: Any = None) -> BagNode | None:
        """Internal get node by label at current level.

        Args:
            label: Node label to find.
            autocreate: If True, create node if not found.
            default: Default value for autocreated node.

        Returns:
            The BagNode, or None if not found and not autocreate.
        """
        p = self._nodes.index(label)
        if p >= 0:
            node = self._nodes[p]
        elif autocreate:
            node = BagNode(self, label=label, value=default)
            i = len(self._nodes)
            self._nodes.set(label, node)
            node.parent_bag = self
            if self.backref:
                self._on_node_inserted(node, i)
        else:
            node = None
        return node

    # -------------------- get_node --------------------------------

    @smartasync
    async def get_node(self, path: str | None = None, as_tuple: bool = False,
                       autocreate: bool = False, default: Any = None,
                       static: bool = False) -> BagNode | None:
        """Get the BagNode at a path.

        Unlike get_item which returns the value, this returns the BagNode itself,
        giving access to attributes and other node properties.

        Args:
            path: Hierarchical path. If None or empty, returns the parent_node
                (the node containing this Bag). Can also be an integer index.
            as_tuple: If True, return (container_bag, node) tuple.
            autocreate: If True, create node if not found.
            default: Default value for autocreated node.
            static: If True, don't trigger resolvers during traversal.

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
            return self._parent_node

        if isinstance(path, int):
            return self._nodes[path]

        obj, label = await smartawait(self._async_htraverse(path, write_mode=autocreate, static=static))

        if isinstance(obj, Bag):
            node = obj._get_node(label, autocreate, default)
            if as_tuple:
                return (obj, node)
            return node

        return None

    # -------------------- backref management --------------------------------

    def set_backref(self, node: BagNode | None = None,
                    parent: Bag | None = None) -> None:
        """Force a Bag to a more strict structure (tree-leaf model).

        Enables backref mode which maintains parent references and
        propagates events up the hierarchy.

        Args:
            node: The BagNode that contains this Bag.
            parent: The parent Bag.
        """
        if not self.backref:
            self._backref = True
            self._parent = parent
            self._parent_node = node
            for node in self:
                node.parent_bag = self

    def del_parent_ref(self) -> None:
        """Set False in the parent Bag reference of the relative Bag."""
        self._parent = None
        self._backref = False

    def clear_backref(self) -> None:
        """Clear all the set_backref() assumption."""
        if self._backref:
            self._backref = False
            self._parent = None
            self._parent_node = None
            for node in self:
                node.parent_bag = None
                value = node.get_value(static=True)
                if isinstance(value, Bag):
                    value.clear_backref()

    # -------------------- event triggers --------------------------------

    def _on_node_changed(self, node: BagNode, pathlist: list, evt: str,
                         oldvalue: Any = None, reason: str | None = None) -> None:
        """Trigger for node change events."""
        for s in list(self._upd_subscribers.values()):
            s(node=node, pathlist=pathlist, oldvalue=oldvalue, evt=evt, reason=reason)
        if self.parent:
            self.parent._on_node_changed(node, [self.parent_node.label] + pathlist,
                                          evt, oldvalue, reason=reason)

    def _on_node_inserted(self, node: BagNode, ind: int, pathlist: list | None = None,
                          reason: str | None = None) -> None:
        """Trigger for node insert events."""
        parent = node.parent_bag
        if parent is not None and parent.backref and hasattr(node.value, '_htraverse'):
            node.value.set_backref(node=node, parent=parent)

        if pathlist is None:
            pathlist = []
        for s in list(self._ins_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='ins', reason=reason)
        if self.parent:
            self.parent._on_node_inserted(node, ind, [self.parent_node.label] + pathlist,
                                           reason=reason)

    def _on_node_deleted(self, node: Any, ind: int, pathlist: list | None = None,
                         reason: str | None = None) -> None:
        """Trigger for node delete events."""
        for s in list(self._del_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='del', reason=reason)
        if self.parent:
            if pathlist is None:
                pathlist = []
            self.parent._on_node_deleted(node, ind, [self.parent_node.label] + pathlist,
                                          reason=reason)

    # -------------------- subscription --------------------------------

    def _subscribe(self, subscriber_id: str, subscribers_dict: dict,
                   callback: Any) -> None:
        """Internal subscribe helper."""
        if callback is not None:
            subscribers_dict[subscriber_id] = callback

    def subscribe(self, subscriber_id: str, update: Any = None, insert: Any = None,
                  delete: Any = None, any: Any = None) -> None:
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

    def unsubscribe(self, subscriber_id: str, update: bool = False,
                    insert: bool = False, delete: bool = False,
                    any: bool = False) -> None:
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
