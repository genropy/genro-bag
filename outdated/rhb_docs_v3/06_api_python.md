# Python API Sketch

This document provides a concrete Python‑style interface for the RHB system.  
It is **illustrative**, not a final implementation.

```python
from collections import OrderedDict
import time

class TriggerEntry:
    def __init__(self, trigger_id, callback, event_types):
        self.trigger_id = trigger_id
        self.callback = callback
        self.event_types = set(event_types)

class TriggerList:
    def __init__(self):
        self._entries = []

    def add(self, callback, event_types):
        trigger_id = f"t{len(self._entries)+1}"
        entry = TriggerEntry(trigger_id, callback, event_types)
        self._entries.append(entry)
        return trigger_id

    def remove(self, trigger_id):
        self._entries = [e for e in self._entries if e.trigger_id != trigger_id]

    def fire(self, event_type, **kwargs):
        for entry in self._entries:
            if event_type in entry.event_types:
                entry.callback(**kwargs)

class Resolver:
    def __init__(self, fn, cachetime=0):
        self.fn = fn
        self.cachetime = cachetime
        self.last_value = None
        self.expires_at = None

    def invalidate_cache(self):
        self.expires_at = None
        self.last_value = None

    def resolve(self, node):
        now = time.time()
        if self.cachetime != 0 and self.expires_at is not None and now < self.expires_at:
            return self.last_value

        result = self.fn(node)
        if isinstance(result, tuple):
            value, attrs = result
        else:
            value, attrs = result, None

        if self.cachetime != 0:
            self.last_value = (value, attrs)
            self.expires_at = None if self.cachetime == -1 else now + self.cachetime

        return value, attrs

class BagNode:
    def __init__(self, label, value=None, attributes=None, parent_bag=None):
        self.label = label
        self.value = value
        self.attributes = attributes or {}
        self.parent_bag = parent_bag
        self.resolver = None
        self.triggers = TriggerList()

    def setValue(self, value, reason=None):
        old_value = self.value
        if old_value is value:
            return
        self.value = value
        info = {"value_changed": True, "attributes_changed": False}
        # fire node-local triggers
        self.triggers.fire(
            "update",
            node=self,
            old_value=old_value,
            old_attributes=None,
            info=info,
            reason=reason,
            level=0,
        )
        # propagate to bags
        if self.parent_bag is not None:
            self.parent_bag._propagate_update(self, old_value, None, info, reason, level=0)

    def setAttr(self, name, value, reason=None):
        old_attributes = dict(self.attributes)
        if value is None:
            self.attributes.pop(name, None)
        else:
            self.attributes[name] = value

        info = {"value_changed": False, "attributes_changed": True}
        self.triggers.fire(
            "update",
            node=self,
            old_value=None,
            old_attributes=old_attributes,
            info=info,
            reason=reason,
            level=0,
        )
        if self.parent_bag is not None:
            self.parent_bag._propagate_update(self, None, old_attributes, info, reason, level=0)

class Bag:
    def __init__(self, attributes=None, parent_node=None):
        self.attributes = attributes or {}
        self.children = OrderedDict()
        self.parent_node = parent_node
        self.triggers = TriggerList()

    def __getitem__(self, path_default):
        # support both bag["path"] and bag["path", default]
        if isinstance(path_default, tuple):
            path, default = path_default
        else:
            path, default = path_default, None
        return self.getitem(path, default)

    def getitem(self, path, default=None):
        node, attr_name = self._resolve_path_to_node(path)
        if node is None:
            return default
        if attr_name is not None:
            return node.attributes.get(attr_name, default)
        return node.value

    def getNode(self, path, default=None):
        node, attr_name = self._resolve_path_to_node(path)
        if node is None or attr_name is not None:
            return default
        return node

    def setItem(self, path, value, _attrs=None, **attrs):
        # simplified: final segment must be a label
        _attrs = _attrs or {}
        merged_attrs = {**_attrs, **attrs}
        parent_bag, label = self._resolve_path_to_parent_bag(path)
        if parent_bag is None or label is None:
            raise ValueError("Invalid path for setItem")
        node = parent_bag.children.get(label)
        if node is None:
            node = BagNode(label, value=value, attributes=merged_attrs, parent_bag=parent_bag)
            position = len(parent_bag.children)
            parent_bag.children[label] = node
            parent_bag._fire_insert(node, position, reason="setItem-new", level=0)
        else:
            old_value = node.value
            old_attrs = dict(node.attributes)
            node.value = value
            node.attributes.update(merged_attrs)
            info = {"value_changed": old_value != value, "attributes_changed": old_attrs != node.attributes}
            parent_bag._propagate_update(node, old_value, old_attrs, info, reason="setItem-update", level=0)

    def popNode(self, path):
        parent_bag, label = self._resolve_path_to_parent_bag(path)
        if parent_bag is None or label not in parent_bag.children:
            return None
        # find position
        labels = list(parent_bag.children.keys())
        position = labels.index(label)
        node = parent_bag.children.pop(label)
        parent_bag._fire_delete(node, position, reason="popNode", level=0)
        return node

    # internal helpers (_resolve_path_to_node, _resolve_path_to_parent_bag, _fire_insert, _fire_delete, _propagate_update)
    # would follow the path syntax rules described elsewhere.
```

This sketch demonstrates how the semantics specified in the documents can be implemented in Python.
