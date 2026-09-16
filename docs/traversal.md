# Traversal APIs

Python uses `bag.for_each(callback, static=True, deep=False, **kwargs)`.
JavaScript uses `bag.forEach(callback, {static: true, deep: false, kwargs: {}})`.

The default visits only direct nodes. `deep` enables depth-first recursion,
visiting each parent before its children. `static` prevents resolver activation
by the visitor; callbacks may still explicitly resolve a value themselves.

A callback returning None (Python), null or undefined (JavaScript) continues
into children when deep is enabled. A falsey non-null result (including false,
zero and the empty string) skips the children and continues with siblings.
A truthy result ends the entire visit and is returned. With no match the visitor
returns None/null. Exceptions propagate. Python callbacks receive `(node, **kwargs)`;
JavaScript callbacks receive `(node, kwargs, siblingIndex)`.
`_pathlist` and `_indexlist`, when supplied, are extended to include the current
node without mutating the caller's lists. Native JS kwargs are shallow copied.

`traverse()` yields original nodes, not path/node tuples, recursively in
parent-first order without resolving values. It follows the Python legacy API.

`walk` is no longer a standalone Bag API. GenroPy compatibility bridges provide
callback-only `walk` with a deprecation warning. The Python bridge retains
ancestor-only tracking lists and skips children on falsey non-None results.
The JS bridge retains null/undefined continuation, `__continue__` subtree skips,
and stops on all other results, including false, zero and empty strings. Legacy
JS `forEach(callback, mode, kw)` remains first-level and ignores mode, just as
before; modern options objects select the native contract.

Internal serialization uses a private streaming path/node iterator; it does not
materialize a deep index, depend on backrefs, or resolve lazy values.
