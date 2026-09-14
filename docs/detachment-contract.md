# Subtree detachment

Replacing a node's Bag value detaches the old value before change subscribers run. The identity check prevents detaching a value assigned to itself. Detachment only applies while the old value still identifies that node as its owner.

Removing nodes with pop or clear clears their containing-Bag reference and detaches their Bag values. The detached subtree keeps its internal parent links and subscriptions, but its root has no parent or parent node. It can be reattached and propagate events through its new parent. Explicit delParentRef also clears both upward links.

Python nested clear retains its existing change-event snapshot: removed nodes belong to an independent snapshot Bag, and nested children are reparented to that snapshot. Silent clear detaches individual removed nodes.

This deliberately differs from legacy JavaScript's recursive backref disablement: detachment preserves the usable internal tree. Explicit clearBackref still disables backrefs recursively.

Regression coverage includes replacement with a scalar, null/None, pop, clear, silent Python clear, nested Python clear snapshots, identical-value assignment, event callback state, isolated child changes and reattachment.
