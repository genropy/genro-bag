# Public node removal

`pop_node()` (Python) and `popNode()` (JavaScript) remove and return the same node, preserving its attributes and resolver without resolving its value. `pop()` uses the same removal path and returns the value, with normal resolver evaluation.

Deletion subscribers observe the old parent during notification. After notification, the removed node is detached, even when a subscriber raises; the exception propagates. A subscriber that reinserts or transfers that node retains the new ownership. A nested Bag becomes an independent tree with its internal references and local subscriptions intact.

The compatibility mixins inherit this contract. No legacy orphaning override is required for the tested paths. JavaScript integration tests must use a browser bundle built from the updated library; the previously vendored bundle does not provide this contract.

This contract concerns public removal, not `clear()` or private `_pop()` behavior.
