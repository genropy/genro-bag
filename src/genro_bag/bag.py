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

from typing import TYPE_CHECKING, Any

from genro_toolbox import smartsplit

from .node_container import NodeContainer

if TYPE_CHECKING:
    from .bag_node import BagNode


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
        _nodes: NodeContainer holding the BagNodes.
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
        self._nodes: NodeContainer = NodeContainer()
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

    # -------------------- _htraverse --------------------------------

    def _htraverse(self, pathlist: str | list, autocreate: bool = False,
                   return_last_match: bool = False) -> tuple[Any, str]:
        """Traverse a hierarchical path and return the container and final label.

        This is the core navigation method. Given a path like 'a.b.c', it traverses
        the Bag hierarchy and returns the Bag containing 'c' along with the label 'c'.

        Path syntax:
            - 'a.b.c': Navigate through nested Bags
            - '#0', '#1': Access by numeric index
            - '../': Go to parent (converted to '#^')
            - '#^': Parent reference

        Args:
            pathlist: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            autocreate: If True, create intermediate Bags for missing path segments.
            return_last_match: If True, on partial match return the deepest found
                node and the remaining path instead of (None, None).

        Returns:
            Tuple of (container, label) where:
                - container: The Bag containing the final element, or None if not found
                - label: The final path segment, or remaining path if return_last_match

        Raises:
            BagException: If autocreate is True and path uses '#n' syntax for
                non-existent index.

        Example:
            >>> bag = Bag()
            >>> bag['a.b.c'] = 1
            >>> container, label = bag._htraverse('a.b.c')
            >>> container['c']  # same as bag['a.b']['c']
            1
        """
        from .bag_node import BagNode

        curr = self
        if isinstance(pathlist, str):
            pathlist = pathlist.replace('../', '#parent.')
            pathlist = [x for x in smartsplit(pathlist, '.') if x]
        else:
            pathlist = list(pathlist)

        if not pathlist:
            return curr, ''

        label = pathlist.pop(0)

        # handle parent reference #parent
        while label == '#parent' and pathlist:
            curr = curr.parent
            label = pathlist.pop(0)

        if not pathlist:
            return curr, label

        # find node at current level using index
        i = curr._nodes.index(label)

        if i < 0:
            if autocreate:
                if label.startswith('#'):
                    raise BagException('Not existing index in #n syntax')
                i = len(curr._nodes)
                new_node = BagNode(curr, label=label, value=curr.__class__())
                curr._nodes.set(label, new_node)
                if self.backref:
                    self._on_node_inserted(new_node, i, reason='autocreate')
            elif return_last_match:
                return self._parent_node, '.'.join([label] + pathlist)
            else:
                return None, None

        new_curr_node = curr._nodes[i]
        new_curr = new_curr_node.value
        is_bag = hasattr(new_curr, '_htraverse')

        if autocreate and not is_bag:
            new_curr = curr.__class__()
            new_curr_node.value = new_curr
            is_bag = True

        if is_bag:
            return new_curr._htraverse(pathlist, autocreate=autocreate,
                                        return_last_match=return_last_match)
        else:
            if return_last_match:
                return new_curr_node, '.'.join(pathlist)
            return new_curr, '.'.join(pathlist)

    # -------------------- get (single level) --------------------------------

    def get(self, label: str, default: Any = None, mode: str | None = None) -> Any:
        """Get value at a single level (no path traversal).

        Unlike get_item/`__getitem__`, this method only looks at direct children
        of this Bag. It does not traverse paths with dots.

        Args:
            label: Node label to look up. Can be a string label or '#n' index.
                Supports '?attr' suffix to get a node attribute instead of value.
            default: Value to return if label not found.
            mode: Optional mode for result transformation:
                - None: Return the value directly
                - 'attrname': Return the specified attribute
                - 'k:': Return list of keys (if value is Bag)
                - 'd:what' or 'digest:what': Return digest of value

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
        result = None
        currnode = None
        currvalue = None
        attrname = None

        if not label:
            currnode = self.parent_node
            currvalue = self
        elif label == '#parent':
            currnode = self.parent.parent_node
        else:
            if '?' in label:
                label, attrname = label.split('?')
            i = self._nodes.index(label)
            if i < 0:
                return default
            else:
                currnode = self._nodes[i]

        if currnode:
            currvalue = currnode.get_attr(attrname) if attrname else currnode.get_value()

        if not mode:
            result = currvalue
        else:
            cmd = mode.lower()
            if ':' not in cmd:
                result = currnode.get_attr(mode)
            else:
                if cmd == 'k:':
                    result = list(currvalue.keys())
                elif cmd.startswith('d:') or cmd.startswith('digest:'):
                    result = currvalue.digest(mode.split(':')[1])

        return result

    # -------------------- get_item --------------------------------

    def get_item(self, path: str, default: Any = None, mode: str | None = None) -> Any:
        """Get value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path and returns
        the value at the final location. This is the method behind `bag[path]`.

        Args:
            path: Hierarchical path like 'a.b.c'. Empty path returns self.
                Supports '?mode' suffix to specify mode (e.g., 'a.b?k' for keys).
            default: Value to return if path not found.
            mode: Optional mode for result transformation (see get() for details).

        Returns:
            The value at the path if found, otherwise default.

        Example:
            >>> bag = Bag()
            >>> bag['config.db.host'] = 'localhost'
            >>> bag.get_item('config.db.host')
            'localhost'
            >>> bag['config.db.host']  # same thing
            'localhost'
            >>> bag.get_item('missing.path', 'default')
            'default'
        """
        if not path:
            return self

        path = _normalize_path(path)

        if isinstance(path, str):
            if '?' in path:
                path, mode = path.split('?')
                if mode == '':
                    mode = 'k'

        obj, label = self._htraverse(path)

        if isinstance(obj, Bag):
            return obj.get(label, default, mode=mode)

        if hasattr(obj, 'get'):
            value = obj.get(label, default)
            return value
        else:
            return default

    __getitem__ = get_item

    # -------------------- _set (single level) --------------------------------

    def _set(self, label: str, value: Any, _attributes: dict | None = None,
             _position: str | None = None, _duplicate: bool = False,
             _updattr: bool = False, _remove_null_attributes: bool = True,
             _reason: str | None = None) -> None:
        """Set value at a single level (no path traversal).

        Internal method that handles the actual node creation/update logic.
        Called by set_item() after path traversal.

        Args:
            label: Node label.
            value: Value to set.
            _attributes: Optional dict of attributes.
            _position: Position for new nodes.
            _duplicate: If True, always create new node (for addItem).
            _updattr: If True, update attributes instead of replacing.
            _remove_null_attributes: If True, remove None attributes.
            _reason: Reason for the change (for events).
        """
        from .bag_node import BagNode
        from .resolver import BagResolver

        resolver = None
        if isinstance(value, BagResolver):
            resolver = value
            value = None
            if resolver.attributes:
                _attributes = dict(_attributes or ())
                _attributes.update(resolver.attributes)

        i = -1 if _duplicate else self._nodes.index(label)

        if i < 0:
            if label.startswith('#'):
                raise BagException('Not existing index in #n syntax')
            else:
                bagnode = BagNode(self, label=label, value=value, attr=_attributes,
                                  resolver=resolver,
                                  _remove_null_attributes=_remove_null_attributes)
                self._insert_node(bagnode, _position, _reason=_reason)
        else:
            node = self._nodes[i]
            if resolver is not None:
                node.resolver = resolver
            node.set_value(value, _attributes=_attributes, _updattr=_updattr,
                           _remove_null_attributes=_remove_null_attributes, _reason=_reason)

    # -------------------- _insert_node --------------------------------

    def _insert_node(self, node: BagNode, position: str | int | None,
                     _reason: str | None = None) -> int:
        """Insert a node at the specified position.

        Handles position parsing and node insertion logic.

        Args:
            node: The BagNode to insert.
            position: Position specification:
                - int: Insert at index
                - None or '>': Append at end
                - '<': Insert at beginning
                - '#n': Insert at index n
                - '<label': Insert before label
                - '>label': Insert after label
            _reason: Reason for insertion (for events).

        Returns:
            The index where the node was inserted.
        """
        if isinstance(position, int):
            n = position
        elif not position or position == '>':
            n = -1
        elif position == '<':
            n = 0
        elif position[0] == '#':
            n = int(position[1:])
        else:
            if position[0] in '<>':
                pos_char, label = position[0], position[1:]
            else:
                pos_char, label = '<', position
            if label[0] == '#':
                n = int(label[1:])
            else:
                n = self._nodes.index(label)
            if pos_char == '>' and n >= 0:
                n = n + 1

        if n < 0:
            n = len(self._nodes)

        self._nodes.insert(n, node)
        node.parent_bag = self

        if self.backref:
            self._on_node_inserted(node, n, reason=_reason)

        return n

    # -------------------- set_item --------------------------------

    def set_item(self, path: str, value: Any, _attributes: dict | None = None,
                 _position: str | None = None, _duplicate: bool = False,
                 _updattr: bool = False, _remove_null_attributes: bool = True,
                 _reason: str | None = None, **kwargs) -> None:
        """Set value at a hierarchical path.

        Traverses the Bag hierarchy following the dot-separated path, creating
        intermediate Bags as needed, and sets the value at the final location.
        This is the method behind `bag[path] = value`.

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

        Example:
            >>> bag = Bag()
            >>> bag.set_item('a.b.c', 42)
            >>> bag['a.b.c']
            42
            >>> bag.set_item('a.b.d', 'hello', _attributes={'type': 'greeting'})
        """
        from .resolver import BagResolver

        if kwargs:
            _attributes = dict(_attributes or {})
            _attributes.update(kwargs)

        if path == '' or path is True:
            if isinstance(value, BagResolver):
                value = value()
            if isinstance(value, Bag):
                for el in value:
                    self.set_item(el.label, el.value, _attributes=el.attr, _updattr=_updattr)
            elif hasattr(value, 'items'):
                for key, v in list(value.items()):
                    self.set_item(key, v)
            return self
        else:
            path = _normalize_path(path)
            obj, label = self._htraverse(path, autocreate=True)
            obj._set(label, value, _attributes=_attributes, _position=_position,
                     _duplicate=_duplicate, _updattr=_updattr,
                     _remove_null_attributes=_remove_null_attributes, _reason=_reason)

    __setitem__ = lambda self, path, value: self.set_item(path, value)

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
        """Return list of node labels in order.

        Returns:
            List of string labels for all direct child nodes.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> bag.keys()
            ['a', 'b']
        """
        return [node.label for node in self._nodes]

    def values(self) -> list[Any]:
        """Return list of node values in order.

        Returns:
            List of values for all direct child nodes.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> bag.values()
            [1, 2]
        """
        return [node.value for node in self._nodes]

    def items(self) -> list[tuple[str, Any]]:
        """Return list of (label, value) tuples in order.

        Returns:
            List of (label, value) tuples for all direct child nodes.

        Example:
            >>> bag = Bag()
            >>> bag['a'] = 1
            >>> bag['b'] = 2
            >>> bag.items()
            [('a', 1), ('b', 2)]
        """
        return [(node.label, node.value) for node in self._nodes]

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
        from .bag_node import BagNode

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
        from .bag_node import BagNode

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

    def get_node(self, path: str | None = None, as_tuple: bool = False,
                 autocreate: bool = False, default: Any = None) -> BagNode | None:
        """Get the BagNode at a path.

        Unlike get_item which returns the value, this returns the BagNode itself,
        giving access to attributes and other node properties.

        Args:
            path: Hierarchical path. If None or empty, returns the parent_node
                (the node containing this Bag). Can also be an integer index.
            as_tuple: If True, return (container_bag, node) tuple.
            autocreate: If True, create node if not found.
            default: Default value for autocreated node.

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

        obj, label = self._htraverse(path, autocreate=autocreate)

        if isinstance(obj, Bag):
            node = obj._get_node(label, autocreate, default)
            if as_tuple:
                return (obj, node)
            return node

        return None

    # -------------------- trigger stubs --------------------------------

    def _on_node_inserted(self, node: BagNode, ind: int, pathlist: list | None = None,
                          reason: str | None = None) -> None:
        """Internal trigger called when a node is inserted.

        In backref mode, this propagates insert events up the hierarchy and
        notifies subscribers. Currently a stub - will be implemented with
        the subscription system.

        Args:
            node: The inserted BagNode.
            ind: Index where the node was inserted.
            pathlist: Path components leading to this location.
            reason: Reason for insertion (e.g., 'autocreate').
        """
        pass

    def _on_node_deleted(self, node: Any, ind: int, pathlist: list | None = None,
                         reason: str | None = None) -> None:
        """Internal trigger called when a node is deleted.

        In backref mode, this propagates delete events up the hierarchy and
        notifies subscribers. Currently a stub - will be implemented with
        the subscription system.

        Args:
            node: The deleted BagNode (or list of nodes for clear()).
            ind: Index where the node was located (-1 for clear).
            pathlist: Path components leading to this location.
            reason: Reason for deletion.
        """
        pass


class BagException(Exception):
    """Exception raised for Bag-specific errors.

    Raised when operations on a Bag fail due to invalid paths,
    illegal operations, or constraint violations.

    Example:
        - Attempting to autocreate with '#n' syntax for non-existent index
    """
    pass
