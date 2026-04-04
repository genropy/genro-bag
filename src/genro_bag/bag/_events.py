# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagEvents mixin - subscription and event propagation for Bag.

Provides the event subscription system (subscribe/unsubscribe) and
internal event triggers (_on_node_changed, _on_node_inserted, etc.)
that propagate changes up the parent hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_toolbox import cancel_timer, set_interval

if TYPE_CHECKING:
    from genro_bag.bagnode import BagNode


class BagEvents:
    """Mixin providing event subscription and propagation for Bag.

    Assumes the presence of:
        _upd_subscribers, _ins_subscribers, _del_subscribers, _tmr_subscribers: dict
        parent, parent_node: properties
        backref: property
        set_backref: method
    """

    _upd_subscribers: dict
    _ins_subscribers: dict
    _del_subscribers: dict
    _tmr_subscribers: dict

    # -------------------- event triggers --------------------------------

    def _on_node_changed(
        self,
        node: BagNode,
        pathlist: list,
        evt: str,
        oldvalue: Any = None,
        reason: str | None = None,
    ) -> None:
        """Trigger for node change events.

        Propagates to parent unless a subscriber returns False.
        """
        for s in list(self._upd_subscribers.values()):
            if s(node=node, pathlist=pathlist, oldvalue=oldvalue, evt=evt, reason=reason) is False:
                return
        if self.parent and self.parent_node:  # type: ignore[attr-defined]
            self.parent._on_node_changed(  # type: ignore[attr-defined]
                node, [self.parent_node.label] + pathlist, evt, oldvalue, reason=reason  # type: ignore[attr-defined]
            )

    def _on_node_inserted(
        self, node: BagNode, ind: int, pathlist: list | None = None, reason: str | None = None
    ) -> None:
        """Trigger for node insert events.

        Propagates to parent unless a subscriber returns False.
        """
        parent = node.parent_bag
        value = node._value
        if parent is not None and parent.backref and hasattr(value, "_htraverse"):
            value.set_backref(node=node, parent=parent)

        if pathlist is None:
            pathlist = []
        for s in list(self._ins_subscribers.values()):
            if s(node=node, pathlist=pathlist, ind=ind, evt="ins", reason=reason) is False:
                return
        if self.parent and self.parent_node:  # type: ignore[attr-defined]
            self.parent._on_node_inserted(  # type: ignore[attr-defined]
                node, ind, [self.parent_node.label] + pathlist, reason=reason  # type: ignore[attr-defined]
            )

    def _on_node_deleted(
        self, node: Any, ind: int, pathlist: list | None = None, reason: str | None = None
    ) -> None:
        """Trigger for node delete events.

        Propagates to parent unless a subscriber returns False.
        """
        for s in list(self._del_subscribers.values()):
            if s(node=node, pathlist=pathlist, ind=ind, evt="del", reason=reason) is False:
                return
        if self.parent and self.parent_node:  # type: ignore[attr-defined]
            if pathlist is None:
                pathlist = []
            self.parent._on_node_deleted(  # type: ignore[attr-defined]
                node, ind, [self.parent_node.label] + pathlist, reason=reason  # type: ignore[attr-defined]
            )

    def _on_timer_tick(self, subscriber_id: str) -> None:
        """Trigger for timer events.

        Propagates to parent unless the subscriber callback returns False.
        """
        entry = self._tmr_subscribers.get(subscriber_id)
        if entry and entry["callback"](bag=self, evt="tmr", subscriber_id=subscriber_id) is False:
            return
        if self.parent and self.parent_node:  # type: ignore[attr-defined]
            self.parent._on_timer_tick_propagate([self.parent_node.label])  # type: ignore[attr-defined]

    def _on_timer_tick_propagate(self, pathlist: list) -> None:
        """Propagate timer tick to parent subscribers.

        Propagates to parent unless a subscriber callback returns False.
        """
        for s in list(self._tmr_subscribers.values()):
            if s["callback"](bag=self, evt="tmr", subscriber_id=None, pathlist=pathlist) is False:
                return
        if self.parent and self.parent_node:  # type: ignore[attr-defined]
            self.parent._on_timer_tick_propagate([self.parent_node.label] + pathlist)  # type: ignore[attr-defined]

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
        timer: Any = None,
        interval: float | None = None,
        any: Any = None,
    ) -> None:
        """Subscribe a callback to bag events.

        Args:
            subscriber_id: Unique identifier for this subscription.
            update: Callback for update events.
            insert: Callback for insert events.
            delete: Callback for delete events.
            timer: Callback for timer events (requires interval).
            interval: Seconds between timer ticks (required if timer is set).
            any: Callback for update, insert, and delete events (not timer).

        Raises:
            ValueError: If timer is set without interval.
        """
        if not self.backref:  # type: ignore[attr-defined]
            self.set_backref()  # type: ignore[attr-defined]

        self._subscribe(subscriber_id, self._upd_subscribers, update or any)
        self._subscribe(subscriber_id, self._ins_subscribers, insert or any)
        self._subscribe(subscriber_id, self._del_subscribers, delete or any)

        if timer is not None:
            if interval is None:
                raise ValueError("interval is required when timer is set")
            timer_id = set_interval(interval, self._on_timer_tick, subscriber_id)
            self._tmr_subscribers[subscriber_id] = {
                "timer_id": timer_id,
                "callback": timer,
                "interval": interval,
            }

    def unsubscribe(
        self,
        subscriber_id: str,
        update: bool = False,
        insert: bool = False,
        delete: bool = False,
        timer: bool = False,
        any: bool = False,
    ) -> None:
        """Remove a subscription.

        Args:
            subscriber_id: The subscription identifier to remove.
            update: Remove update subscription.
            insert: Remove insert subscription.
            delete: Remove delete subscription.
            timer: Remove timer subscription.
            any: Remove all subscriptions (including timer).
        """
        if update or any:
            self._upd_subscribers.pop(subscriber_id, None)
        if insert or any:
            self._ins_subscribers.pop(subscriber_id, None)
        if delete or any:
            self._del_subscribers.pop(subscriber_id, None)
        if timer or any:
            entry = self._tmr_subscribers.pop(subscriber_id, None)
            if entry:
                cancel_timer(entry["timer_id"])
