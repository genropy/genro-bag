# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataChange layer — know what changed in a Bag since it was last drained.

Attach a collector to a Bag and every write is captured as a *change*::

    from genro_bag import Bag
    from genro_bag.datachange import DataChangeCollector

    bag = Bag()
    collector = DataChangeCollector(bag)
    bag['user.name'] = 'Ada'
    collector.pending          # 1

A **change is a plain dict**, never a class — so it travels on the wire
through the generic type registry with no datachange-specific encoder.
One boundary comes with that: signing cannot reach a Bag inside a plain
value, so with ``sign_key`` a change whose ``value`` is a Bag carrying a
resolver is refused by ``to_tytx``/``to_json`` (``BagSerializationError``)
rather than sent unsigned. The change shape::

    {
        "key": {"path": str, "reason": str | None, "fired": bool},
        "value": Any,
        "attributes": dict | None,
        "delete": bool,
        "change_ts": datetime,
        "change_idx": int,
    }

``key`` holds exactly the three fields that decide identity: two changes
coalesce when ``new["key"] == old["key"]`` — the dict's own equality, no
custom ``__eq__`` anywhere. ``delete`` stays outside the key because a
delete must coalesce over a previous set on the same path. ``attributes``
stays outside because merging fuses it: if it discriminated, two writes to
the same path carrying different attributes would never coalesce and there
would be nothing left to fuse.

``fired`` marks a one-shot event change. The plain rail cannot observe it:
``set_item(..., _fired=True)`` resets the node value with ``trigger=False``
after the write, so the callback sees an ordinary set. Locally captured
changes therefore always carry ``fired=False``; a consumer forwarding a
fire event supplies ``fired=True`` on the change it appends.

``delete=True`` means *the node is gone*. A consumer applying the change to
a replica must delete the node, not set its value to None — the two are
different states and only the first is what happened.

``value`` is the node's **static** value: resolvers are never triggered by
capture. ``attributes`` is the node's full attribute dict at capture time
(not the diff), so a change is directly applicable to a replica; it is
None when the node carries no attributes. ``change_ts`` is a
**timezone-aware UTC** datetime: the wire (genro-tytx) transmits datetimes
as UTC, so a naive local timestamp would come back shifted.

The collector subscribes with ``update=``/``insert=``/``delete=`` rather
than ``any=``, so the three callbacks stay separately readable, and its
callbacks **never return False**: a subscriber returning False stops
propagation to every other subscriber of that Bag, which would make dict
iteration order decide who sees what.

The subscriber id is derived from ``id(self)``, so several collectors
coexist on one Bag, each with its own pending list.

Paths are filtered by prefix, matched on segment boundaries: the prefix
``'a.b'`` captures ``'a.b'`` and ``'a.b.c'``, never ``'a.bc'``.
``paths=None`` (the default) captures every write. ``subscribe_path`` and
``unsubscribe_path`` widen and narrow the prefix set at runtime; removing
the last prefix leaves an empty set, which captures nothing — only
``paths=None`` means everything.

Capture happens on **two rails**, because a write inside
``Bag.transaction()`` never reaches the plain one: the three triggers
append the mutation to the transaction list and return, with no dispatch
and no parent bubble. So the collector also subscribes ``transaction=``,
and walks the mutations in order. They arrive as positional tuples whose
shape depends on the kind — ``("upd", node, pathlist, evt, oldvalue,
attrs_diff, reason)`` with 7 elements, ``("ins", node, pathlist, ind,
reason)`` and ``("del", ...)`` with 5 — so dispatch is on element 0. Every
mutation is deposited through the same change constructor the plain rail
uses: transaction-born and plain-rail changes are indistinguishable
downstream.

The mutation ``pathlist`` is **local to the bag whose trigger fired**, not
absolute: inside a transaction nothing bubbles, so no parent ever prepends
its label. The path is therefore rebuilt by walking the node's backref
chain up to the observed Bag, which yields exactly the path the plain rail
would have reported for the same write.

A consumer reads the pending changes with ``drain()``, which returns them
ordered by ``change_idx`` and empties the list; ``drain(reset=False)``
peeks without consuming. ``reset()`` empties without reading, and
``drop(prefix)`` discards only the pending changes under one prefix —
matched on segment boundaries, like capture. ``pending`` counts the
changes waiting to be drained. ``detach()`` stops capture and leaves the
pending list untouched; it unsubscribes with ``any=True`` **and**
``transaction=True``, because ``any=`` alone does not remove the
transaction subscription.

``append(change, replace=False)`` deposits a change that was not born from
a local write, e.g. one forwarded from another collector. The collector
deposits a shallow copy and assigns ``change_idx`` to that copy only —
the caller's dict is never mutated, so one change can be forwarded to any
number of collectors, each keeping its own monotonic counter. With
``replace=True`` the pending change carrying an equal ``key`` is removed
first, so repeated writes to one path survive as a single change. The
coalesced change gets a **new** ``change_idx`` and goes to the tail: drain
order reflects when the last write happened. Since ``delete`` sits outside
the key, a forwarded delete coalesces over a previous set on the same path
and only the removal survives.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from genro_bag.bag import Bag
    from genro_bag.bagnode import BagNode


class DataChangeCollector:
    """Capture the changes made to a Bag, ready to be drained by a consumer."""

    def __init__(self, bag: Bag, paths: set[str] | list[str] | None = None) -> None:
        """Attach a collector to a Bag.

        Args:
            bag: The Bag to observe.
            paths: Prefixes to capture. None captures every write.
        """
        self.bag = bag
        self.paths = None if paths is None else set(paths)
        self.changes: list[dict[str, Any]] = []
        self.subscriber_id = f"datachange_{id(self)}"
        self._change_idx = 0
        bag.subscribe(
            self.subscriber_id,
            update=self._on_update,
            insert=self._on_insert,
            delete=self._on_delete,
            transaction=self._on_transaction,
        )

    # -------------------- capture --------------------------------

    def _on_update(self, **kwargs: Any) -> None:
        """Capture an update event. Never returns False."""
        node = kwargs["node"]
        path = self._join(kwargs["pathlist"])
        self._deposit_node(path, node, kwargs.get("reason"), delete=False)

    def _on_insert(self, **kwargs: Any) -> None:
        """Capture an insert event. Never returns False."""
        node = kwargs["node"]
        path = self._join(list(kwargs["pathlist"] or []) + [node.label])
        self._deposit_node(path, node, kwargs.get("reason"), delete=False)

    def _on_delete(self, **kwargs: Any) -> None:
        """Capture a delete event. Never returns False.

        The delete trigger may pass ``pathlist=None`` at the originating level.
        """
        node = kwargs["node"]
        path = self._join(list(kwargs["pathlist"] or []) + [node.label])
        self._deposit_node(path, node, kwargs.get("reason"), delete=True)

    def _on_transaction(self, **kwargs: Any) -> None:
        """Capture every mutation batched by a transaction, in order.

        Mutations are positional tuples whose shape depends on the kind, so
        the kind in element 0 decides where the reason sits.
        """
        for mutation in kwargs["mutations"]:
            kind, node = mutation[0], mutation[1]
            reason = mutation[6] if kind == "upd" else mutation[4]
            self._deposit_node(
                self._node_path(node), node, reason, delete=(kind == "del")
            )

    # -------------------- change construction --------------------------------

    def _node_path(self, node: BagNode) -> str:
        """Build the path of a node relative to the observed Bag.

        Walks the backref chain upwards, since a transaction mutation
        carries only the pathlist local to the bag that fired the trigger.
        """
        labels = [node.label]
        bag = node.parent_bag
        while bag is not None and bag is not self.bag:
            parent_node = bag.parent_node
            if parent_node is None:
                break
            labels.append(parent_node.label)
            bag = parent_node.parent_bag
        return ".".join(reversed(labels))

    def _join(self, pathlist: list | None) -> str:
        """Build a dotted path from an event pathlist."""
        return ".".join(pathlist or [])

    def _under(self, path: str, prefix: str) -> bool:
        """Tell whether path is the prefix or sits below it, on a segment boundary."""
        return path == prefix or path.startswith(f"{prefix}.")

    def _captures(self, path: str) -> bool:
        """Tell whether path falls under one of the subscribed prefixes."""
        if self.paths is None:
            return True
        return any(self._under(path, p) for p in self.paths)

    def _build_change(
        self,
        path: str,
        value: Any,
        attributes: dict[str, Any] | None,
        reason: str | None,
        delete: bool,
        fired: bool = False,
    ) -> dict[str, Any]:
        """Build a change dict. The only place the shape is written."""
        return {
            "key": {"path": path, "reason": reason, "fired": fired},
            "value": value,
            "attributes": attributes,
            "delete": delete,
            "change_ts": datetime.now(UTC),
            "change_idx": 0,
        }

    def _deposit_node(
        self, path: str, node: BagNode, reason: str | None, delete: bool
    ) -> None:
        """Build and deposit the change describing a node event."""
        if not self._captures(path):
            return
        value = None if delete else node.static_value
        attributes = dict(node.attr) or None
        self._deposit(self._build_change(path, value, attributes, reason, delete))

    def _deposit(self, change: dict[str, Any]) -> None:
        """Assign the next change_idx and append the change to the pending list."""
        self._change_idx += 1
        change["change_idx"] = self._change_idx
        self.changes.append(change)

    # -------------------- consumption --------------------------------

    def drain(self, reset: bool = True) -> list[dict[str, Any]]:
        """Return the pending changes ordered by change_idx.

        Args:
            reset: True empties the pending list, False leaves it intact.
        """
        changes = sorted(self.changes, key=lambda change: change["change_idx"])
        if reset:
            self.changes = []
        return changes

    def append(self, change: dict[str, Any], replace: bool = False) -> None:
        """Deposit a change that was not born from a local write.

        The collector deposits a shallow copy and assigns ``change_idx`` to
        that copy only: the caller's dict is never mutated, so one change can
        be forwarded to any number of collectors.

        Args:
            change: The change dict, forwarded from elsewhere.
            replace: True removes the pending change with an equal ``key``
                first, so the two coalesce into the appended one.
        """
        if replace:
            self.changes = [c for c in self.changes if c["key"] != change["key"]]
        self._deposit(dict(change))

    def drop(self, prefix: str) -> None:
        """Discard the pending changes whose path falls under a prefix."""
        self.changes = [
            c for c in self.changes if not self._under(c["key"]["path"], prefix)
        ]

    def reset(self) -> None:
        """Empty the pending list without reading it."""
        self.changes = []

    # -------------------- prefix set --------------------------------

    def subscribe_path(self, prefix: str) -> None:
        """Add a prefix to the captured set.

        On a collector capturing everything (``paths=None``) this starts
        restricting capture to the given prefix.
        """
        if self.paths is None:
            self.paths = set()
        self.paths.add(prefix)

    def unsubscribe_path(self, prefix: str) -> None:
        """Remove a prefix from the captured set.

        Removing the last prefix leaves an empty set, which captures
        nothing: it does not restore the capture-everything state that
        only ``paths=None`` means.
        """
        if self.paths is not None:
            self.paths.discard(prefix)

    # -------------------- lifecycle --------------------------------

    @property
    def pending(self) -> int:
        """Number of changes waiting to be drained."""
        return len(self.changes)

    def detach(self) -> None:
        """Stop capturing. Pending changes are left untouched."""
        self.bag.unsubscribe(self.subscriber_id, any=True, transaction=True)
