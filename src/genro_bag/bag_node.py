# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagNode module - individual nodes in the Bag hierarchy.

This module provides the BagNode class, which represents a single node
in a Bag hierarchy. Each node has a label (unique key within its parent),
attributes, a value, and optional resolver for lazy loading.

Key Features:
    - Dual relationship: node.parent_bag → Bag, Bag.parent_node → node
    - Optional tag for builder-based validation
    - Resolver support for lazy/dynamic value computation
    - Per-node subscriptions for change notifications
    - Validation state tracking via _invalid_reasons
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from genro_toolbox import safe_is_instance

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
        _invalid_reasons: List of validation error messages (empty if valid).
    """

    __slots__ = (
        'label',
        '_value',
        '_attr',
        '_parent_bag',
        '_resolver',
        '_node_subscribers',
        'tag',
        '_invalid_reasons',
    )

    def __init__(
        self,
        parent_bag: Bag | None,
        label: str,
        value: Any = None,
        attr: dict[str, Any] | None = None,
        resolver: BagResolver | None = None,
        tag: str | None = None,
        _remove_null_attributes: bool = True,
    ) -> None:
        """Initialize a BagNode.

        Args:
            parent_bag: The parent Bag containing this node.
            label: The node's key/name within the parent Bag.
            value: The node's value (can be scalar or Bag).
            attr: Dict of attributes to set via set_attr() (with processing).
            resolver: A BagResolver for lazy/dynamic value loading.
            tag: Optional type/tag for the node (used by builders).
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
        self._invalid_reasons: list[str] = []

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
        """One BagNode is equal to another if its attr and value/resolver match."""
        try:
            if isinstance(other, BagNode) and (self._attr == other._attr):
                if self._resolver is None:
                    return self._value == other._value
                else:
                    return self._resolver == other._resolver
            return False
        except Exception:
            return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f'BagNode : {self.label}'

    def __repr__(self) -> str:
        return f'BagNode : {self.label} at {id(self)}'

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
            if hasattr(self._value, '_htraverse') and parent_bag.backref:
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
            if static:
                return self._value
            else:
                if self._resolver.read_only:
                    return self._resolver()
                if self._resolver.expired:
                    self.value = self._resolver()
                return self._value
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
        elif safe_is_instance(value, "genro_bag.bag_node.BagNode"):
            _attributes = _attributes or {}
            _attributes.update(value._attr)
            value = value._value

        # Handle objects with rootattributes
        if hasattr(value, 'rootattributes'):
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
        evt = 'upd_value'

        if _attributes is not None:
            evt = 'upd_value_attr'
            # Call set_attr with trigger=False: node subscribers receive only
            # 'upd_value' from here, not a separate 'upd_attrs' event
            self.set_attr(_attributes, trigger=False, _updattr=_updattr,
                          _remove_null_attributes=_remove_null_attributes)

        # Node subscribers always receive 'upd_value' (not 'upd_value_attr')
        # They don't need to know if attributes also changed
        if trigger:
            for subscriber in self._node_subscribers.values():
                subscriber(node=self, info=oldvalue, evt='upd_value')

        if self._parent_bag is not None and self._parent_bag.backref:
            if hasattr(value, '_htraverse'):
                value.set_backref(node=self, parent=self._parent_bag)
            if trigger:
                self._parent_bag._on_node_changed(
                    self, [self.label], oldvalue=oldvalue, evt=evt, reason=_reason
                )

    @property
    def static_value(self) -> Any:
        """Get node's value in static mode (bypassing resolver)."""
        return self.get_value('static')

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
        if not label or label == '#':
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
                    subscriber(node=self, info=upd_attrs, evt='upd_attrs')

            if self._parent_bag is not None and self._parent_bag.backref:
                self._parent_bag._on_node_changed(
                    self, [self.label], evt='upd_attrs', reason=trigger
                )

    def del_attr(self, *attrs_to_delete: str) -> None:
        """Remove attributes from the node.

        Args:
            *attrs_to_delete: Attribute labels to remove. Each can be a single
                label or a comma-separated string of labels (e.g., 'a,b,c').
        """
        for attr in attrs_to_delete:
            if isinstance(attr, str) and ',' in attr:
                # Handle comma-separated string
                for a in attr.split(','):
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
            return self._attr[label] == value
        return True

    # -------------------------------------------------------------------------
    # Navigation Properties
    # -------------------------------------------------------------------------

    @property
    def position(self) -> int | None:
        """Get this node's index in parent's nodes list."""
        if self.parent_bag is None:
            return None
        return self.parent_bag.nodes.keys().index(self.label)

    @property
    def fullpath(self) -> str | None:
        """Get dot-separated path from root to this node."""
        if self.parent_bag is not None:
            fullpath = self.parent_bag.fullpath
            if fullpath is not None:
                return f'{fullpath}.{self.label}'
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
    # Validation (from TreeStore)
    # -------------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """True if this node has no validation errors."""
        return len(self._invalid_reasons) == 0

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
            return f'Other label: {other.label}'
        if self._attr != other._attr:
            return f'attributes self:{self._attr} --- other:{other._attr}'
        if self._value != other._value:
            if hasattr(self._value, 'diff'):
                return f'value:{self._value.diff(other._value)}'
            else:
                return f'value self:{self._value} --- other:{other._value}'
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
        if hasattr(value, 'to_json'):
            value = value.to_json(typed=typed, nested=True)
        return {"label": self.label, "value": value, "attr": self._attr}
