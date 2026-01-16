# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagNode module - individual nodes and container for the Bag hierarchy.

This module provides:
    - BagNode: represents a single node in a Bag hierarchy
    - BagNodeContainer: ordered container for BagNodes with positional insert
    - BagNodeException: exception for node operations

Key Features:
    - Dual relationship: node.parent_bag → Bag, Bag.parent_node → node
    - Optional tag for builder-based validation
    - Resolver support for lazy/dynamic value computation
    - Per-node subscriptions for change notifications
    - Validation state tracking via _invalid_reasons
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from genro_toolbox import safe_is_instance, smartsplit

if TYPE_CHECKING:
    from .bag import Bag
    from .resolver import BagResolver

# Type alias for node subscriber callbacks
NodeSubscriberCallback = Callable[..., None]


class BagNodeException(Exception):
    """Exception raised by BagNode operations."""

    pass


class BagNode:
    """BagNode is the element type which a Bag is composed of.

    A BagNode gathers within itself three main things:
    - *label*: can be only a string
    - *value*: can be anything, even a Bag for hierarchical structure
    - *attributes*: dictionary that contains node's metadata

    Attributes:
        label: The node's unique name/key within its parent.
        tag: Optional type/tag for the node (used by builders).

    Internal Attributes (via __slots__):
        _value: The node's actual value storage.
        _attr: Dictionary of node attributes/metadata.
        _parent_bag: Reference to the parent Bag containing this node.
        _resolver: Optional BagResolver for lazy/dynamic value computation.
        _node_subscribers: Dict mapping subscriber_id to callback for change notifications.
        tag: Semantic type for builder validation.
        xml_tag: Original XML tag name for serialization.
        _invalid_reasons: List of validation error messages. Empty list means valid.
            This attribute is reserved for external validation systems (e.g., TreeStore
            builders) to populate. The BagNode itself does not set validation errors.
        _compiled: Dict for compilation data. Reserved for builders to store compiled
            objects, references, or any compilation-related data. Initialized lazily
            on first access via the `compiled` property.
    """

    __slots__ = (
        "label",
        "_value",
        "_attr",
        "_parent_bag",
        "_resolver",
        "_node_subscribers",
        "tag",
        "xml_tag",
        "_invalid_reasons",
        "_compiled",
    )

    def __init__(
        self,
        parent_bag: Bag | None,
        label: str,
        value: Any = None,
        attr: dict[str, Any] | None = None,
        resolver: BagResolver | None = None,
        tag: str | None = None,
        xml_tag: str | None = None,
        _remove_null_attributes: bool = True,
    ) -> None:
        """Initialize a BagNode.

        Args:
            parent_bag: The parent Bag containing this node.
            label: The node's key/name within the parent Bag.
            value: The node's value (can be scalar or Bag).
            attr: Dict of attributes to set via set_attr() (with processing).
            resolver: A BagResolver for lazy/dynamic value loading.
            tag: Optional type/tag for the node (used by builders for validation).
            xml_tag: Original XML tag name (used for XML serialization).
            _remove_null_attributes: If True, remove None values from attributes.
        """
        # Basic node identity
        self.label = label
        self._value: Any = None
        self._parent_bag: Bag | None = None
        self._resolver: BagResolver | None = None
        self._node_subscribers: dict[str, NodeSubscriberCallback] = {}
        self._attr: dict[str, Any] = {}
        self.tag = tag
        self.xml_tag = xml_tag
        self._invalid_reasons: list[str] = []
        self._compiled: dict[str, Any] | None = None

        # Set parent (uses property setter)
        self.parent_bag = parent_bag

        # Set resolver if provided (uses property setter for bidirectional link)
        if resolver is not None:
            self.resolver = resolver

        # Process attributes via set_attr
        if attr:
            self.set_attr(attr, trigger=False, _remove_null_attributes=_remove_null_attributes)

        # Process value via set_value
        if value is not None:
            self.set_value(value, trigger=False)

    def __eq__(self, other: object) -> bool:
        """One BagNode is equal to another if label, attr and value/resolver match."""
        try:
            if (
                isinstance(other, BagNode)
                and (self.label == other.label)
                and (self._attr == other._attr)
            ):
                if self._resolver is None:
                    return self._value == other._value  # type: ignore[no-any-return]
                else:
                    return self._resolver == other._resolver  # type: ignore[no-any-return]
            return False
        except Exception:
            return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f"BagNode : {self.label}"

    def __repr__(self) -> str:
        return f"BagNode : {self.label} at {id(self)}"

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to builder if available.

        When a builder is attached to the parent Bag, this allows calling
        builder methods directly on nodes to add children:

            node = bag.div()  # returns BagNode
            node.span()       # delegates to builder._command_on_node()

        The Bag is created lazily when the first child is added.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        # Get builder from parent Bag
        builder = self._parent_bag._builder if self._parent_bag is not None else None

        if builder is not None:
            return lambda node_value=None, node_position=None, **attrs: builder._command_on_node(
                self, name, node_position=node_position, node_value=node_value, **attrs
            )

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # -------------------------------------------------------------------------
    # Parent Bag Property
    # -------------------------------------------------------------------------

    @property
    def parent_bag(self) -> Bag | None:
        """Get the parent Bag containing this node."""
        return self._parent_bag

    @parent_bag.setter
    def parent_bag(self, parent_bag: Bag | None) -> None:
        """Set the parent Bag, handling backref setup if needed.

        If the node's value is a Bag and the parent has backref=True,
        establishes the bidirectional parent-child relationship via set_backref().
        """
        self._parent_bag = None
        if parent_bag is not None:
            self._parent_bag = parent_bag
            if hasattr(self._value, "_htraverse") and parent_bag.backref:
                self._value.set_backref(node=self, parent=parent_bag)

    @property
    def _(self) -> Bag:
        """Return parent Bag for navigation/chaining.

        Example:
            >>> node._.set_item('sibling', 'value')  # add sibling
        """
        if self._parent_bag is None:
            raise ValueError("Node has no parent")
        return self._parent_bag

    # -------------------------------------------------------------------------
    # Value Property and Methods
    # -------------------------------------------------------------------------

    @property
    def value(self) -> Any:
        """Get the node's value, resolving if a resolver is set."""
        return self.get_value()

    @value.setter
    def value(self, value: Any) -> None:
        """Set the node's value."""
        self.set_value(value)

    def get_value(self, static: bool = False) -> Any:
        """Return the value of the BagNode.

        Args:
            static: If True, return raw value without triggering resolver.

        Returns:
            The node's value, possibly resolved via resolver.
        """
        if self._resolver is not None:
            return self._resolver(static=static)
        return self._value

    def set_value(
        self,
        value: Any,
        trigger: bool = True,
        _attributes: dict[str, Any] | None = None,
        _updattr: bool | None = None,
        _remove_null_attributes: bool = True,
        _reason: str | None = None,
    ) -> None:
        """Set the node's value.

        Args:
            value: The value to set.
            trigger: If True, notify subscribers of the change.
            _attributes: Optional attributes to set along with value.
            _updattr: If False, clear existing attributes first.
            _remove_null_attributes: If True, remove None values from attributes.
            _reason: Optional reason string for the trigger.

        Special value handling:
            - BagResolver: Assigned to self.resolver, value set to None.
            - BagNode: Extracts value and merges attributes from the node.
            - Objects with rootattributes: Merges rootattributes into _attributes.

        Note:
            Parameters prefixed with '_' are for internal/advanced use.
            The prefix avoids conflicts with user-defined node attributes.
        """
        # Handle BagResolver passed as value (use safe_is_instance to avoid circular import)
        if safe_is_instance(value, "genro_bag.resolver.BagResolver"):
            self.resolver = value
            value = None
        # Handle BagNode passed as value - extract its value and attrs
        elif safe_is_instance(value, "genro_bag.bagnode.BagNode"):
            _attributes = _attributes or {}
            _attributes.update(value._attr)
            value = value._value

        # Handle objects with rootattributes
        if hasattr(value, "rootattributes"):
            rootattributes = value.rootattributes
            if rootattributes:
                _attributes = dict(_attributes or {})
                _attributes.update(rootattributes)

        oldvalue = self._value
        self._value = value

        changed = oldvalue != self._value
        if not changed and _attributes:
            for attr_k, attr_v in _attributes.items():
                if self._attr.get(attr_k) != attr_v:
                    changed = True
                    break

        trigger = trigger and changed

        # Event type: 'upd_value' for value-only, 'upd_value_attr' for combined
        # Note: evt is used ONLY for parent notification, not for node subscribers
        evt = "upd_value"

        if _attributes is not None:
            evt = "upd_value_attr"
            # Call set_attr with trigger=False: node subscribers receive only
            # 'upd_value' from here, not a separate 'upd_attrs' event
            self.set_attr(
                _attributes,
                trigger=False,
                _updattr=_updattr,
                _remove_null_attributes=_remove_null_attributes,
            )

        # Node subscribers always receive 'upd_value' (not 'upd_value_attr')
        # They don't need to know if attributes also changed
        if trigger:
            for subscriber in self._node_subscribers.values():
                subscriber(node=self, info=oldvalue, evt="upd_value")

        if self._parent_bag is not None and self._parent_bag.backref:
            if hasattr(value, "_htraverse"):
                value.set_backref(node=self, parent=self._parent_bag)
            if trigger:
                self._parent_bag._on_node_changed(
                    self, [self.label], oldvalue=oldvalue, evt=evt, reason=_reason
                )

    @property
    def static_value(self) -> Any:
        """Get node's raw _value (bypassing resolver)."""
        return self._value

    @static_value.setter
    def static_value(self, value: Any) -> None:
        """Set node's _value directly, bypassing set_value processing and triggers.

        Note: This does NOT remove or affect the resolver. It only sets _value.
        """
        self._value = value

    # -------------------------------------------------------------------------
    # Resolver Property
    # -------------------------------------------------------------------------

    @property
    def resolver(self) -> BagResolver | None:
        """Get the node's resolver."""
        return self._resolver

    @resolver.setter
    def resolver(self, resolver: BagResolver | None) -> None:
        """Set the node's resolver, establishing bidirectional link."""
        if resolver is not None:
            resolver.parent_node = self  # snake_case per Decision #9
        self._resolver = resolver

    def reset_resolver(self) -> None:
        """Reset the resolver and clear the value."""
        if self._resolver is not None:
            self._resolver.reset()
        self.set_value(None)

    # -------------------------------------------------------------------------
    # Compiled Property
    # -------------------------------------------------------------------------

    @property
    def compiled(self) -> dict[str, Any]:
        """Get compilation data dict (lazy initialization).

        Returns a dict that builders can use to store compiled objects,
        references, or any compilation-related data. The dict is created
        on first access.
        """
        if self._compiled is None:
            self._compiled = {}
        return self._compiled

    # -------------------------------------------------------------------------
    # Attribute Methods
    # -------------------------------------------------------------------------

    @property
    def attr(self) -> dict[str, Any]:
        """Get all attributes as a dictionary."""
        return self._attr

    def get_attr(self, label: str | None = None, default: Any = None) -> Any:
        """Get attribute value or all attributes.

        Args:
            label: The attribute's label. If None or '#', returns all attributes.
            default: Default value if attribute not found.

        Returns:
            Attribute value, default, or dict of all attributes.
        """
        if not label or label == "#":
            return self._attr
        return self._attr.get(label, default)

    def set_attr(
        self,
        attr: dict[str, Any] | None = None,
        trigger: bool = True,
        _updattr: bool | None = True,
        _remove_null_attributes: bool = True,
        **kwargs: Any,
    ) -> None:
        """Set attributes on the node.

        Args:
            attr: Dictionary of attributes to set.
            trigger: If True, notify subscribers of the change.
            _updattr: If False, clear existing attributes first.
            _remove_null_attributes: If True, remove None values from attributes.
            **kwargs: Additional attributes as keyword arguments.

        Note:
            Parameters prefixed with '_' are for internal/advanced use.
            The prefix avoids conflicts with user-defined node attributes.
        """
        new_attr = (attr or {}) | kwargs

        # Save old state BEFORE any modification (only if needed for subscribers)
        oldattr = dict(self._attr) if (trigger and self._node_subscribers) else None

        if _updattr:
            self._attr.update(new_attr)
        else:
            self._attr = new_attr

        if _remove_null_attributes:
            self._attr = {k: v for k, v in self._attr.items() if v is not None}

        if trigger:
            if oldattr is not None:
                upd_attrs = [k for k, _ in self._attr.items() - oldattr.items()]
                for subscriber in self._node_subscribers.values():
                    subscriber(node=self, info=upd_attrs, evt="upd_attrs")

            if self._parent_bag is not None and self._parent_bag.backref:
                reason = str(trigger) if trigger is True else trigger
                self._parent_bag._on_node_changed(
                    self, [self.label], evt="upd_attrs", reason=reason
                )

    def del_attr(self, *attrs_to_delete: str) -> None:
        """Remove attributes from the node.

        Args:
            *attrs_to_delete: Attribute labels to remove. Each can be a single
                label or a comma-separated string of labels (e.g., 'a,b,c').
        """
        for attr in attrs_to_delete:
            if isinstance(attr, str) and "," in attr:
                # Handle comma-separated string
                for a in attr.split(","):
                    self._attr.pop(a.strip(), None)
            else:
                self._attr.pop(attr, None)

    def has_attr(self, label: str, value: Any = None) -> bool:
        """Check if a node has the given attribute.

        Args:
            label: Attribute label to check.
            value: If provided, also check if attribute has this value.

        Returns:
            True if attribute exists (and matches value if provided).
        """
        if label not in self._attr:
            return False
        if value is not None:
            return self._attr[label] == value  # type: ignore[no-any-return]
        return True

    # -------------------------------------------------------------------------
    # Navigation Properties
    # -------------------------------------------------------------------------

    @property
    def position(self) -> int | None:
        """Get this node's index position within parent Bag.

        Returns:
            The 0-based index of this node in the parent's node list,
            or None if this node has no parent.
        """
        if self.parent_bag is None:
            return None
        return self.parent_bag._nodes.index(self.label)

    @property
    def fullpath(self) -> str | None:
        """Get dot-separated path from root to this node."""
        if self.parent_bag is not None:
            fullpath = self.parent_bag.fullpath
            if fullpath is not None:
                return f"{fullpath}.{self.label}"
        return None

    @property
    def parent_node(self) -> BagNode | None:
        """Get the node that contains this node's parent Bag.

        In the hierarchy: grandparent_bag contains parent_node, whose value
        is parent_bag, which contains this node.
        """
        if self.parent_bag:
            return self.parent_bag.parent_node
        return None

    def get_inherited_attributes(self) -> dict[str, Any]:
        """Get attributes inherited from ancestors.

        Returns:
            Dict with all inherited attributes merged with this node's attributes.
        """
        inherited: dict[str, Any] = {}
        if self.parent_bag and self.parent_bag.parent_node:
            inherited = self.parent_bag.parent_node.get_inherited_attributes()
        inherited.update(self._attr)
        return inherited

    def attribute_owner_node(
        self,
        attrname: str,
        attrvalue: Any = None,
    ) -> BagNode | None:
        """Find the ancestor node that owns a given attribute.

        Args:
            attrname: Attribute name to search for.
            attrvalue: If provided, also match this value.

        Returns:
            The node that owns the attribute, or None.
        """
        curr: BagNode | None = self
        if attrvalue is None:
            while curr and (attrname not in curr._attr):
                curr = curr.parent_node
        else:
            while curr and curr._attr.get(attrname) != attrvalue:
                curr = curr.parent_node
        return curr

    # -------------------------------------------------------------------------
    # Subscription Methods
    # -------------------------------------------------------------------------

    def subscribe(self, subscriber_id: str, callback: NodeSubscriberCallback) -> None:
        """Subscribe to changes on this specific node.

        Args:
            subscriber_id: Unique identifier for this subscription.
            callback: Function to call on changes.

        Callback signature:
            callback(node, info, evt)
            - node: This BagNode
            - info: oldvalue (for 'upd_value') or list of changed attrs
            - evt: Event type ('upd_value' or 'upd_attrs')
        """
        self._node_subscribers[subscriber_id] = callback

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from changes on this node.

        Args:
            subscriber_id: The subscription identifier to remove.
        """
        self._node_subscribers.pop(subscriber_id, None)

    # -------------------------------------------------------------------------
    # Validation (for external validation systems)
    # -------------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """Check if this node has no validation errors.

        The _invalid_reasons list is populated by external validation systems
        (e.g., TreeStore builders). BagNode provides the storage and this
        property for checking validity, but does not perform validation itself.

        Returns:
            True if _invalid_reasons is empty, False otherwise.
        """
        return len(self._invalid_reasons) == 0

    @property
    def is_branch(self) -> bool:
        """Check if this node's value is a Bag (branch node).

        Returns:
            True if the node's value is a Bag, False otherwise.
        """
        # Import here to avoid circular import
        from .bag import Bag

        return isinstance(self._value, Bag)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def diff(self, other: BagNode) -> str | None:
        """Compare this node with another and return differences.

        Args:
            other: Another BagNode to compare with.

        Returns:
            Description of differences, or None if equal.
        """
        if self.label != other.label:
            return f"Other label: {other.label}"
        if self._attr != other._attr:
            return f"attributes self:{self._attr} --- other:{other._attr}"
        if self._value != other._value:
            return f"value self:{self._value} --- other:{other._value}"
        return None

    def as_tuple(self) -> tuple[str, Any, dict[str, Any], BagResolver | None]:
        """Return node data as a tuple.

        Returns:
            Tuple of (label, value, attr, resolver).
        """
        return (self.label, self.value, self._attr, self._resolver)

    def to_json(self, typed: bool = True) -> dict[str, Any]:
        """Convert node to JSON-serializable dict.

        Args:
            typed: If True, include type information.

        Returns:
            Dict with keys 'label', 'value', and 'attr'.
        """
        value = self.value
        if hasattr(value, "to_json"):
            value = value.to_json(typed=typed, nested=True)
        return {"label": self.label, "value": value, "attr": self._attr}


class BagNodeContainer:
    """Ordered container for BagNodes with positional insert and reordering.

    BagNodeContainer combines dict-like access with list-like ordering. Elements can be
    accessed by label, numeric index, or '#n' string index. Supports positional
    insertion and element reordering without removal.

    This class creates and manages BagNode instances directly.

    Internal structure:
        _dict: maps label -> BagNode (for O(1) lookup by label)
        _list: contains BagNodes in order (for O(1) access by index)
        _parent_bag: optional reference to parent Bag (set via set_backref)
    """

    def __init__(self):
        """Create an empty BagNodeContainer."""
        self._dict: dict[str, Any] = {}
        self._list: list[Any] = []
        self._parent_bag: Bag | None = None

    def index(self, label: str) -> int:
        """Return the index of a label in this container.

        Args:
            label: The label or special syntax to look up. Supported formats:
                - 'label': exact label match
                - '#n': numeric index (e.g., '#0', '#1')
                - '#attr=value': find by attribute value (e.g., '#id=34')
                - '#=value': find by node value (e.g., '#=target')

        Returns:
            Index position (0-based), or -1 if not found.
        """
        if label in self._dict:
            return next((i for i, node in enumerate(self._list) if node.label == label), -1)
        if m := re.match(r"^#(\d+)$", label):
            idx = int(m.group(1))
            return idx if idx < len(self._list) else -1
        if m := re.match(r"^#(\w*)=(.*)$", label):
            attr, value = m.groups()
            if attr:
                return next(
                    (i for i, node in enumerate(self._list) if node.attr.get(attr) == value), -1
                )
            else:
                return next((i for i, node in enumerate(self._list) if node._value == value), -1)
        return -1

    def _parse_position(self, position: str | int | None) -> int:
        """Parse position syntax and return insertion index.

        Args:
            position: Position specification. Supported formats:
                - None or '>': append at end
                - '<': insert at beginning
                - int: insert at this index (clamped to valid range)
                - '#n': insert at index n
                - '<label': insert before label
                - '>label': insert after label
                - '<#n': insert before index n
                - '>#n': insert after index n

        Returns:
            Index where to insert (always valid for list.insert).
        """
        if position is None or position == ">":
            return len(self._list)

        if isinstance(position, int):
            return max(0, min(position, len(self._list)))

        if position == "<":
            return 0

        if position.startswith("#"):
            try:
                return max(0, min(int(position[1:]), len(self._list)))
            except ValueError:
                return len(self._list)

        if position.startswith("<"):
            ref = position[1:]
            if ref.startswith("#"):
                try:
                    return max(0, min(int(ref[1:]), len(self._list)))
                except ValueError:
                    return len(self._list)
            idx = self.index(ref)
            return idx if idx >= 0 else len(self._list)

        if position.startswith(">"):
            ref = position[1:]
            if ref.startswith("#"):
                try:
                    return max(0, min(int(ref[1:]) + 1, len(self._list)))
                except ValueError:
                    return len(self._list)
            idx = self.index(ref)
            return idx + 1 if idx >= 0 else len(self._list)

        return len(self._list)

    def __getitem__(self, key: str | int) -> Any:
        """Get item by label or index."""
        if isinstance(key, int):
            return self._list[key] if 0 <= key < len(self._list) else None
        return self._dict.get(key)

    def get(self, key: str | int) -> Any:
        """Get node by label, index, or #n syntax.

        Args:
            key: Label string, integer index, or '#n' syntax.

        Returns:
            The BagNode if found, None otherwise.
        """
        if isinstance(key, int):
            return self._list[key] if 0 <= key < len(self._list) else None
        if key.startswith("#"):
            try:
                idx = int(key[1:])
                return self._list[idx] if 0 <= idx < len(self._list) else None
            except ValueError:
                return None
        return self._dict.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item. For positional insert, use set()."""
        if key in self._dict:
            idx = next((i for i, node in enumerate(self._list) if node.label == key), -1)
            self._list[idx] = value
        else:
            self._list.append(value)
        self._dict[key] = value

    def __delitem__(self, key: str | int) -> None:
        """Delete item by label, index, or '#n'."""
        if isinstance(key, int):
            idx_to_delete = [key]
        else:
            idx_to_delete = [self.index(block) for block in smartsplit(key, ",")]

        for idx in sorted(idx_to_delete, reverse=True):
            if 0 <= idx < len(self._list):
                v = self._list.pop(idx)
                self._dict.pop(v.label)

    def __contains__(self, key: str) -> bool:
        """Check if label exists."""
        return key in self._dict

    def __len__(self) -> int:
        """Return number of elements."""
        return len(self._list)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over nodes in order."""
        return iter(self._list)

    def set(
        self,
        label: str,
        value: Any,
        node_position: str | int | None = ">",
        attr: dict | None = None,
        resolver: Any = None,
        parent_bag: Bag | None = None,
        _updattr: bool = False,
        _remove_null_attributes: bool = True,
        _reason: str | None = None,
        do_trigger: bool = True,
    ) -> BagNode:
        """Set or create a BagNode with optional position.

        If label exists, updates the existing node's value.
        If label doesn't exist, creates a new BagNode and inserts it.

        Resolver handling (Issue #5):
            If the existing node has a resolver and the `resolver` parameter is not
            explicitly provided, a BagException is raised. To modify a node with a
            resolver, you must explicitly handle the resolver:
            - resolver=False: Remove resolver and set value
            - resolver=NewResolver: Replace resolver with a new one

        Args:
            label: The node label.
            value: The value to set.
            node_position: Position specification (>, <, #n, <label, >label, etc.)
            attr: Optional dict of attributes for new nodes.
            resolver: Optional resolver for new nodes. Use False to explicitly
                remove an existing resolver.
            parent_bag: Parent Bag reference for new nodes.
            _updattr: If True, update attributes instead of replacing.
            _remove_null_attributes: If True, remove None attributes.
            _reason: Reason for the change (for events).
            do_trigger: If True (default), fire events on change.

        Returns:
            The created or updated BagNode.

        Raises:
            BagNodeException: If node has a resolver and resolver parameter not provided.
        """
        if label in self._dict:
            node = self._dict[label]
            # Issue #5: handle resolver on existing node
            if node.resolver is not None and resolver is None:
                raise BagNodeException(
                    f"Cannot set value on node '{label}' with resolver. "
                    "Use resolver=False to remove resolver, or resolver=NewResolver to replace it."
                )
            # resolver=False means explicitly remove the resolver
            if resolver is False:
                node._resolver = None
                resolver = None
            node.set_value(
                resolver if value is None else value,
                _attributes=attr,
                _updattr=_updattr,
                _remove_null_attributes=_remove_null_attributes,
                _reason=_reason,
                trigger=do_trigger,
            )
        else:
            node = BagNode(
                parent_bag,
                label=label,
                value=value,
                attr=attr,
                resolver=resolver,
                _remove_null_attributes=_remove_null_attributes,
            )
            idx = self._parse_position(node_position)
            self._dict[label] = node
            self._list.insert(idx, node)
            if do_trigger and parent_bag is not None and parent_bag.backref:
                parent_bag._on_node_inserted(node, idx, reason=_reason)
        return node  # type: ignore[no-any-return]

    def pop(self, key: str | int) -> Any:
        """Remove and return item.

        Args:
            key: Label, index, or '#n'.

        Returns:
            The removed BagNode, or None if not found.
        """
        value = self[key]

        if value is not None:
            del self._dict[value.label]
            self._list.remove(value)
            return value

        return None

    def move(self, what: int | list[int], position: int, trigger: bool = True) -> None:
        """Move element(s) to a new position.

        Follows the same semantics as JavaScript moveNode:
        - If what is a list, nodes are removed in reverse order (highest index first)
          to preserve indices during removal
        - All removed nodes are then inserted at the target position
        - Events (del/ins) are fired for each node if trigger=True

        Args:
            what: Index or list of indices to move.
            position: Target index position.
            trigger: If True, fire del/ins events (default True).
        """
        if position < 0:
            return

        # Normalize to list
        indices = what if isinstance(what, list) else [what]
        if not indices:
            return

        # Get destination label BEFORE any removal (like JS does)
        if position >= len(self._list):
            return
        dest_label = self._list[position].label

        if len(indices) > 1:
            # Multi-node move (like JS)
            indices = sorted(indices)
            delta = 1 if indices[0] < position else 0

            # Pop nodes in reverse order (highest index first)
            popped = []
            for idx in reversed(indices):
                if 0 <= idx < len(self._list):
                    node = self._list[idx]
                    self._list.pop(idx)
                    popped.append(node)
                    if trigger and self._parent_bag is not None and self._parent_bag.backref:
                        self._parent_bag._on_node_deleted(node, idx)

            # Find new position based on dest_label + delta
            new_pos = self.index(dest_label)
            if new_pos < 0:
                new_pos = len(self._list)
            new_pos += delta

            # Insert all popped nodes at new position
            for node in popped:
                self._list.insert(new_pos, node)
                if trigger and self._parent_bag is not None and self._parent_bag.backref:
                    self._parent_bag._on_node_inserted(node, new_pos)
        else:
            # Single node move
            from_idx = indices[0]
            if from_idx == position:
                return
            if from_idx < 0 or from_idx >= len(self._list):
                return

            node = self._list[from_idx]
            self._list.pop(from_idx)

            if trigger and self._parent_bag is not None and self._parent_bag.backref:
                self._parent_bag._on_node_deleted(node, from_idx)

            self._list.insert(position, node)

            if trigger and self._parent_bag is not None and self._parent_bag.backref:
                self._parent_bag._on_node_inserted(node, position)

    def clear(self) -> None:
        """Remove all elements."""
        self._dict.clear()
        self._list.clear()

    def keys(self, iter: bool = False) -> list[str] | Iterator[str]:
        """Return node labels in order."""
        if iter:
            return (node.label for node in self._list)
        return [node.label for node in self._list]

    def values(self, iter: bool = False) -> list | Iterator:
        """Return node values in order."""
        if iter:
            return (node.get_value() for node in self._list)
        return [node.get_value() for node in self._list]

    def items(self, iter: bool = False) -> list[tuple[str, Any]] | Iterator[tuple[str, Any]]:
        """Return (label, value) tuples in order."""
        if iter:
            return ((node.label, node.get_value()) for node in self._list)
        return [(node.label, node.get_value()) for node in self._list]

    def __eq__(self, other: object) -> bool:
        """Two containers are equal if they have the same nodes in the same order."""
        if not isinstance(other, BagNodeContainer):
            return False
        return self._list == other._list
