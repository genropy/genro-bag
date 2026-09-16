# Deprecations

## Unreleased

### Legacy child-building helpers

These are deprecated compatibility helpers, not native Bag APIs. They remain
callable through the relevant mixins; this is a deprecation, not a removal.

- Python names mixin: `child` and `rowchild` emulate the Python legacy **Bag**
  implementations, not `GnrStructData` overrides. Calls emit DeprecationWarning.
- GenroJS mixin: `rowchild` emulates legacy JS Bag behavior, warning once per
  constructor. JS legacy Bag has no `child`, so none is introduced.

Python `rowchild` generates labels using `R_#` (eight-digit row count), supplies
`_pkey`, stores attributes with a None value and returns None. JS `rowchild`
uses `#attribute` to select a label or generates `tag_<time36Id>`, stores a null
value and attributes, and returns undefined; it does not generate `_pkey`.

Python `child` retains its tag/name templates, dotted path creation, parent
restriction lookup, content creation, existing-child handling and legacy return
value. These conventions are not promoted into the new native API. Struct
classes and struct node APIs are separate and are not deprecated here.

For migration, use `set_item` / `setItem` with an explicit label, value and
attributes. Construct a Bag explicitly when a nested collection is needed;
manage generated labels, `_pkey`, tags and parent restrictions at the caller.
Do not mechanically replace struct `child` calls with Bag operations.


### Implicit resolver delegation to resolved Bag contents

Resolve a value explicitly before using Bag/container operations:
`resolver().keys()` in Python or `resolver.resolve().keys()` in JavaScript.
These calls may execute the resolver; cache policy remains unchanged.

Python's existing `__getitem__`, `__iter__`, `_htraverse`, `get_node`, `keys`,
`items` and `values` delegations now reside in `BagResolverNamesMixin`, alongside
`getNode` and `digest`. They emit DeprecationWarning. They remain inherited for
compatibility; they are no longer methods implemented in the resolver core.
This does not introduce additional Python container protocols such as `__len__`.

The GenroJS resolver mixin retains deprecated legacy `keys`, `items`, `values`,
`digest`, `sum`, `len`, `contains` and `htraverse` delegation, warning once per
constructor. The standalone JS resolver does not implement these methods.
Legacy arguments are retained, including `contains()` not forwarding its
arguments and `htraverse` forwarding the legacy argument shape. Migration must
call an actual supported operation on the resolved value; no new Bag methods
are implied by these compatibility wrappers.

This concerns BagResolver and its compatibility mixins, not struct APIs or
resolver serialization. Deprecated wrappers do not promise that every resolver
returns a Bag: the resolved value must support the operation being requested.
