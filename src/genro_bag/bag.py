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

    def fill_from(self, source: dict[str, Any]) -> None:
        """Fill bag from a source.

        Populates the bag with data from a dict. Existing nodes are cleared first.

        Args:
            source: Dict where keys become labels and values become node values.
                Nested dicts are converted to nested Bags.

        Example:
            >>> bag = Bag()
            >>> bag.fill_from({'x': 1, 'y': {'z': 2}})
            >>> bag['y.z']
            2
        """
        # TODO: implement
        pass

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
        while len(pathlist) > 1:
            label = pathlist.pop(0)
            if label.startswith('#'):
                raise BagException('Not existing index in #n syntax')
            new_bag = curr.__class__()
            new_node = curr._nodes.set(label, new_bag, parent_bag=curr)
            if self.backref:
                self._on_node_inserted(new_node, len(curr._nodes) - 1, reason='autocreate')
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
                 _reason: str | None = None, **kwargs) -> None:
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

        resolver = None
        if safe_is_instance(value, "genro_bag.resolver.BagResolver"):
            resolver = value
            value = None
            if resolver.attributes:
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

    def keys(self) -> list[str]:
        """Return list of node labels in order."""
        return self._nodes.keys()

    def values(self) -> list[Any]:
        """Return list of node values in order."""
        return self._nodes.values()

    def items(self) -> list[tuple[str, Any]]:
        """Return list of (label, value) tuples in order."""
        return self._nodes.items()

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
        if not self._backref:
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
        if self._parent:
            self._parent._on_node_changed(node, [self._parent_node.label] + pathlist,
                                          evt, oldvalue, reason=reason)

    def _on_node_inserted(self, node: BagNode, ind: int, pathlist: list | None = None,
                          reason: str | None = None) -> None:
        """Trigger for node insert events."""
        parent = node.parent_bag
        if parent is not None and parent.backref and hasattr(node._value, '_htraverse'):
            node._value.set_backref(node=node, parent=parent)

        if pathlist is None:
            pathlist = []
        for s in list(self._ins_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='ins', reason=reason)
        if self._parent:
            self._parent._on_node_inserted(node, ind, [self._parent_node.label] + pathlist,
                                           reason=reason)

    def _on_node_deleted(self, node: Any, ind: int, pathlist: list | None = None,
                         reason: str | None = None) -> None:
        """Trigger for node delete events."""
        for s in list(self._del_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='del', reason=reason)
        if self._parent:
            if pathlist is None:
                pathlist = []
            self._parent._on_node_deleted(node, ind, [self._parent_node.label] + pathlist,
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
        if not self._backref:
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
