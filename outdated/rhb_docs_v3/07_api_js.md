# JavaScript API Sketch

This document shows a possible JavaScript‑style API for the RHB system.  
It mirrors the Python semantics.

```javascript
import { encode, decode } from "@msgpack/msgpack";

class TriggerEntry {
  constructor(id, callback, eventTypes) {
    this.id = id;
    this.callback = callback;
    this.eventTypes = new Set(eventTypes);
  }
}

class TriggerList {
  constructor() {
    this.entries = [];
  }

  add(callback, eventTypes) {
    const id = "t" + (this.entries.length + 1);
    this.entries.push(new TriggerEntry(id, callback, eventTypes));
    return id;
  }

  remove(id) {
    this.entries = this.entries.filter(e => e.id !== id);
  }

  fire(eventType, payload) {
    for (const entry of this.entries) {
      if (entry.eventTypes.has(eventType)) {
        entry.callback(payload);
      }
    }
  }
}

class Resolver {
  constructor(fn, cachetime = 0) {
    this.fn = fn;
    this.cachetime = cachetime;
    this.lastValue = null;
    this.expiresAt = null;
  }

  invalidateCache() {
    this.lastValue = null;
    this.expiresAt = null;
  }

  resolve(node) {
    const now = Date.now() / 1000;
    if (this.cachetime !== 0 && this.expiresAt !== null && now < this.expiresAt) {
      return this.lastValue;
    }
    const result = this.fn(node);
    let value, attrs;
    if (Array.isArray(result) && result.length === 2 && typeof result[1] === "object") {
      [value, attrs] = result;
    } else {
      value = result;
      attrs = null;
    }
    if (this.cachetime !== 0) {
      this.lastValue = [value, attrs];
      this.expiresAt = this.cachetime === -1 ? null : now + this.cachetime;
    }
    return [value, attrs];
  }
}

class BagNode {
  constructor(label, value = null, attributes = {}, parentBag = null) {
    this.label = label;
    this.value = value;
    this.attributes = { ...attributes };
    this.parentBag = parentBag;
    this.resolver = null;
    this.triggers = new TriggerList();
  }

  setValue(value, reason = null) {
    const oldValue = this.value;
    if (oldValue === value) return;
    this.value = value;
    const info = { value_changed: true, attributes_changed: false };
    this.triggers.fire("update", {
      node: this,
      old_value: oldValue,
      old_attributes: null,
      info,
      reason,
      level: 0,
    });
    if (this.parentBag) {
      this.parentBag._propagateUpdate(this, oldValue, null, info, reason, 0);
    }
  }

  setAttr(name, value, reason = null) {
    const oldAttributes = { ...this.attributes };
    if (value === null || value === undefined) {
      delete this.attributes[name];
    } else {
      this.attributes[name] = value;
    }
    const info = { value_changed: false, attributes_changed: true };
    this.triggers.fire("update", {
      node: this,
      old_value: null,
      old_attributes: oldAttributes,
      info,
      reason,
      level: 0,
    });
    if (this.parentBag) {
      this.parentBag._propagateUpdate(this, null, oldAttributes, info, reason, 0);
    }
  }
}

class Bag {
  constructor(attributes = {}, parentNode = null) {
    this.attributes = { ...attributes };
    this.children = []; // array of [label, BagNode]
    this.parentNode = parentNode;
    this.triggers = new TriggerList();
  }

  // A real implementation would use a proper path parser.
  getitem(path, defaultValue = null) {
    // For brevity, assume simple "label.label" only here.
    const parts = path.split(".");
    let bag = this;
    let node = null;
    for (let i = 0; i < parts.length; i++) {
      const label = parts[i];
      node = (bag.children.find(([lbl]) => lbl === label) || [null, null])[1];
      if (!node) return defaultValue;
      if (i < parts.length - 1) {
        if (!(node.value instanceof Bag)) return defaultValue;
        bag = node.value;
      }
    }
    return node ? node.value : defaultValue;
  }

  setItem(path, value, attrs = {}) {
    const parts = path.split(".");
    const label = parts.pop();
    // Find parent bag...
    // Implementation omitted for brevity: same semantics as described in spec.
  }

  _propagateUpdate(node, oldValue, oldAttrs, info, reason, level) {
    this.triggers.fire("update", {
      node,
      old_value: oldValue,
      old_attributes: oldAttrs,
      info,
      reason,
      level,
    });
    if (this.parentNode && this.parentNode.parentBag) {
      this.parentNode.parentBag._propagateUpdate(node, oldValue, oldAttrs, info, reason, level - 1);
    }
  }
}
```

This sketch shows how the same semantics can be mapped into JavaScript.  
A production implementation would add a full path parser that respects `#N`, `/parent` and `?attr`.
