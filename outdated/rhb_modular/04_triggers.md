
# RHB Specification — 04 Triggers

Trigger types:
- insert(where, pos, node, reason, level)
- delete(where, pos, node, reason, level)
- update(node, old_value, old_attrs, info, reason, level)

Propagation:
- node triggers
- bag triggers level 0
- parent bags level -1, -2 ...

Triggers have ID and order of registration.
