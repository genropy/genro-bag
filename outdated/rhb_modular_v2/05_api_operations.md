
# 05 — API Operations (Complete)

## Bag API

### getitem(path, default=None)
Safe navigation:
- never raises
- returns value or Bag or default

### getNode(path, default=None)
Returns node object or default.

### popNode(path)
- removes node
- returns node
- fires delete triggers

### setItem(path, value, _attrs=None, **attrs)
Creates or updates node value and attributes.
Final segment must be a label.

## Node API

### setValue(value, reason=None)
Updates value + triggers.

### setAttr(name, value, reason=None)
Updates/removes attribute + triggers.

