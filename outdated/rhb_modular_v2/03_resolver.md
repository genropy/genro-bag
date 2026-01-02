
# 03 — Resolver Specification (Complete)

## 1. Overview
Resolvers compute node values:
- synchronously (returning immediately)
- asynchronously (writing into a Bag path)

## 2. Resolver Return Forms

### 2.1 Value only
```
return value
```

### 2.2 Value + attributes
```
return (value, attrs)
```
Both produce update triggers.

## 3. Cache Rules

- `cachetime = 0` → no cache (sync only)
- `cachetime = -1` → infinite cache
- `cachetime = N` → cache valid N seconds

## 4. Resolver Invocation Rules

### 4.1 If cache valid → return cached value.
### 4.2 If cache invalid:
- sync → compute now, update node, fire triggers
- async → launch computation; resolver writes result into Bag path

## 5. Cache Invalidation
External code may call:
```
node.invalidateCache()
```

## 6. Triggering
At resolver completion:
- local node triggers fire
- containing Bag triggers fire (level 0)
- parent Bag triggers fire (levels -1, -2...)
