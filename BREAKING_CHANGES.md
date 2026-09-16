# Breaking changes

## Unreleased

### Resolver cache durations are numeric

Both libraries use the same expiration contract: zero reloads on access,
positive values are TTL seconds, and every negative value means infinite
cache until invalidation/reset. Negative values never schedule background work.
Boolean durations are rejected, including assignment through compatibility setters.
Python callers using `cache_time=False` must use a negative number such as `-1`.
UUID and OpenAPI resolver defaults have been migrated to `-1`; legacy negative
values are preserved by the Python mixin without semantic translation.
Existing serialized Python resolver descriptions containing a boolean cache
duration must also be migrated before deserialization.

### Legacy resolverDescription is no longer supported

`BagResolver.resolverDescription()` is not provided by the new Python resolver
or restored by its compatibility mixin. The legacy base method returned
`repr(self)` and was also called by `__str__`. The new base does not preserve
that custom description dispatch; an application subclass may define its own
explicit diagnostic representation if needed.

This is not resolver serialization; the serialization APIs are unaffected.
Sourcerer found no direct application callers in the indexed repositories.
The `StructObjResolver` override returning `tree` belongs to that subclass
and is not evidence of a required base Bag/resolver contract. No subclass
implementation is removed by this change.


### Bag formulas and validation are no longer supported

The legacy Bag formula subsystem (`defineSymbol`, `defineFormula`, `formula`,
`BagFormula` / `GnrBagFormula`) and Bag/node validation subsystem are no longer
supported. Neither is restored by compatibility mixins. A future design may
reintroduce these capabilities; no replacement API is promised today.

Node validation state (`is_valid` / `isValid`, `_invalid_reasons` /
`_invalidReasons`) has been removed from the new libraries. Legacy validation
classes, including `BagValidationError`, are not exported by the native Python
integration. Supplying `_validators` to Python compatibility item methods now
raises instead of warning and silently ignoring the requested validation;
None remains an unused positional placeholder to avoid shifting other options.

This concerns Bag formulas and Bag validation only. Input-format checks,
resolver parameter checks, and application/widget validation are unaffected.
The flag-off legacy implementation remains available for comparison.

### Legacy Bag modification flag is not supported

The legacy Python `Bag.modified` tracking property is not provided by the new
Bag or its compatibility mixin. Previously, assigning False enabled event-based
tracking, subsequent Bag events set the flag to True, and assigning None
disabled tracking. Assigning a plain `modified` attribute on the new Bag does
not enable this mechanism.

Applications needing this state should explicitly subscribe to Bag events and
manage their own flag. A Sourcerer search across the indexed repositories found
no application usage of the legacy Python property; this is not a guarantee
about unindexed applications. No compatibility implementation is being added.


### Explicit replacement and deprecated mixed-source filling

`Bag.replace(Bag)` and `BagNode.replace(BagNode)` are new APIs, with matching
contracts in Python and JavaScript; see [Replacing contents](docs/replacing-contents.md).
`fillFrom` is now a deprecated compatibility method (Python also `fill_from`).
Migrate by decoding/constructing the source Bag explicitly, then calling
`destination.replace(sourceBag)`. Constructors do not warn.
JavaScript callers of the standalone `fillFrom` must migrate or use the
GenroJS compatibility mixin; the standalone class no longer exposes it.
Python retains both names through its compatibility mixin.

### Removed get_node tuple option

`get_node` no longer accepts `as_tuple`. It returns only a node or None.
Its remaining options (`autocreate`, `default`, `static`) are keyword-only so
old positional tuple flags cannot silently become autocreation requests.
The camel-case compatibility method `getNode` no longer accepts `asTuple`.
Its second positional slot is reserved: None/False are accepted solely to
preserve existing positional autocreate/default calls; other values raise.
Use `get_node(path, autocreate=True, default=value)` for new code.

`BagNode.as_tuple()` / `asTuple()` is a separate API and remains available,
returning label, value, attributes and resolver.

### Leaf path/value collection

`get_leaves()` is now a base method; `getLeaves()` is its camel-case alias.
It returns relative path/value pairs for non-Bag leaves and resolves each node
once per occurrence. Unlike the previous static-query adapter, uncached resolver
branches are expanded rather than emitted as null leaves. Unlike legacy Python,
nested intermediate Bags are never included. Empty Bags produce no entries;
None, false, zero and empty strings remain valid leaf values. Shared subtrees
are reported under each path. The return value is a list, not an iterator.

### Compatibility index paths

`getIndexList(asText=False)` now derives its paths from `getIndex()`, matching
legacy Python. Unlike the previous static-query adaptation, it resolves lazy
branches and follows the same shared-subtree/cycle policy as `getIndex()`.
Callers must account for resolver execution and the additional resolved paths.
`asText=True` joins those paths with newlines; an empty Bag returns `[]` or `''`.

### Callback and iterator traversal

`walk` is removed from the standalone API. Use `for_each` (Python) / `forEach`
(JS), with `deep=True/true` for recursive callbacks, or `traverse()` to iterate
nodes. Falsey non-null callback results now skip children; truthy results stop
and are returned. JS `forEach` now takes an options object; its old positional
signature is confined to the GenroPy compatibility mixin. See
[traversal contracts](docs/traversal.md) for migration and legacy semantics.

Potential application impacts:

- `bag.walk(callback)` becomes `bag.for_each(callback, deep=True)`. Omitting
  `deep=True` visits only direct nodes. Replace legacy `_mode` with `static`;
  use `static=False` when traversal must resolve lazy branches.
- `for path, node in bag.walk()` cannot be replaced by the same unpacking over
  `traverse()`: it yields nodes only. When paths are required, use a callback
  with `_pathlist=[]` and join the supplied labels. Traversal paths do not
  require backrefs; substituting node fullpaths is not generally equivalent.
- In the former native callback API, falsey returns still descended into child
  Bags. The new visitor skips those children. Return `None` to continue into
  them; return `False` to skip them. A truthy return stops the entire visit.
- Native `_pathlist` and `_indexlist` include the current node. The GenroPy
  `walk` bridge preserves legacy ancestor-only lists, so callbacks migrated
  from that bridge must not append the current label/index again.
- Callback-only `walk` survives only when GenroPy compatibility is activated,
  and emits `DeprecationWarning`. It does not restore iterator-mode `walk()`.
  Applications treating deprecations as errors must migrate these calls.


### Legacy node traversal

`traverse()` is a base Bag iterator yielding original nodes (not path/node
pairs), depth-first with parents before children, without resolving lazy
values. As in legacy Python, a shared subtree is visited at each occurrence;
the previous compatibility helper silently skipped repeated subtree objects.

These are intentional contract changes. Review application assumptions before upgrading.

### Node fullpath

A node attached directly to a root Bag now returns its label (`cliente`), not
`None`/`null`. Deeper nodes return paths such as `cliente.nome`. A detached node
still returns `None`/`null`. The root **Bag** itself keeps its previous empty-path
representation (`None`/`null`). Paths depend on the available parent links; enable
backrefs for a complete nested hierarchy.

Migration: do not use a null node path to detect first-level membership; inspect
the parent instead. In a detached subtree, paths are relative to its new root.

### Null ordering

String-based sort criteria put null values first ascending and last descending,
reversing the previous standalone-library behavior and restoring the shared
legacy Python/JS convention. Zero and empty strings remain non-null values.
Callable sort keys retain their own ordering behavior.

### Public removal callbacks

Public node removal now completes detachment even when a delete subscriber
raises; the error still propagates. Callback reinsertion or transfer of the node
is respected. Applications must not rely on dangling references after a failed
callback. Extracted Bag values remain independent trees with local backrefs,
unlike legacy JS orphaning which disabled backrefs recursively.

### Canonical case modes versus legacy APIs

The standalone modes remain unchanged: `a`/`d` ignore case and `A`/`D` preserve
case, for all string criteria. This differs from legacy conventions. Applications
migrating from legacy code must select case-sensitive modes explicitly where
needed. Star-suffix compatibility and its deprecation belong to GenroPy's JS
compatibility layer, not these standalone libraries.

### Pretty XML formatting

Pretty XML is now indented during serialization, without reparsing the output.
Whitespace, empty-element spelling and trailing-newline layout may differ from
previous pretty output. Compare parsed content rather than serialized bytes;
see [XML indentation](docs/xml-indentation.md).

### Empty Bags in legacy XML input

Auto-detected `GenRoBag` XML with `_T="BAG"` or `_T="bag"` now reconstructs an
empty Bag instead of the erroneous strings `::BAG` or `::bag`. Code that worked
around those strings should consume the reconstructed Bag directly.

### XML label suffix collisions

The default XML reader now checks that generated duplicate labels are free.
For `<item>A</item><item_1>B</item_1><item>C</item>`, it preserves all three nodes
as `item`, `item_1`, `item_2`; previously `C` overwrote `B`. Renaming changes only
the internal label, retaining the source `xml_tag` for serialization. Explicit
label-remapping attributes retain their existing behavior. Applications must
not rely on the former silent overwrite.

Deep copies now also preserve `node_tag` and `xml_tag` at every level. This fixes
loss of nested XML tags when the constructor copies the result of XML parsing.
Serialization of such copies now uses the preserved tags rather than internal labels.

### Sum signature and recursion

The public signature is now `sum(what, strict=False, condition=None)` in Python
and `sum(what, strict=false, condition=null)` in JavaScript. Move positional
predicates from argument two to argument three; Python keyword `condition=`
continues to work. The former `deep` option is removed: summation selects only
nodes at the current level. Explicit traversal must be performed separately.
Old positional `deep` booleans in argument three now raise a TypeError rather
than silently changing behavior.

Strict mode returns None/null if a selected value is None/null/undefined or the
empty string. Without strict these values contribute zero. Zero and false are
valid, and an empty selection sums to zero. Filtering happens before strict
validation. Multiple criteria return one sum or None/null per criterion.

Legacy JS callers already passing strict in position two remain compatible in
argument layout; strict failure now returns null rather than undefined.
Non-empty non-numeric values are now ignored without strict and raise TypeError
with strict. Numeric strings are not converted. This replaces Python's previous
unconditional arithmetic error and JavaScript's accidental string concatenation.
Numeric values and booleans are summed; Python Decimal values retain their precision.
Filtering applies first. In strict mode all selected values are checked: a null
must not hide a non-numeric error later in the selection. A null result is returned
only if no invalid type is found.

### Attribute lookup order relative to legacy JavaScript

`get_node_by_attr` / `getNodeByAttr` searches all nodes at the current level
before descending into child Bags in insertion order. Once a branch is selected,
that branch is searched recursively before the next branch. This is not a global
breadth-first search. It preserves the Python legacy contract and the existing
standalone behavior, but differs from legacy JavaScript's immediate depth-first
walk. If several nodes match, the returned node may therefore differ when
migrating from legacy JavaScript. The JS mixin defaults to deep_first=true for legacy compatibility; the Python
mixin keeps false. Explicit deep_first overrides either default.

The new optional `deep_first` parameter defaults to false in both standalone
libraries. Python: `get_node_by_attr(attr, value, deep_first=False)`; its camel-case
bridge preserves the path-output argument before the new option:
`getNodeByAttr(attr, value, path=None, deep_first=False)`.
JavaScript: `getNodeByAttr(attr, value, caseInsensitive=false, deep_first=false)`.
An omitted/undefined JS value requests attribute presence, now preserved through
all recursive levels; previously nested searches inadvertently compared against
undefined. Python retains its existing None-as-presence semantics.

### Value lookup inside Bag rows

`get_node_by_value` / `getNodeByValue` now interprets a dotted key as a path when
searching a Bag-valued row, restoring legacy behavior. Previously it treated the
path as a direct label and could miss matches. Only current-level rows are
candidates; traversal of the path inside each row is not a recursive row search.
Non-Bag mapping keys retain their existing literal-key lookup semantics.

## Empty-path assignment

`set_item('', source)` / `setItem('', source)` now updates the current Bag
from the first-level entries of another Bag or mapping/object, returning the
destination Bag. It no longer creates an empty-label node. Unmentioned nodes
remain; matching nested Bag values are replaced, not recursively merged.
Bag entries carry their attributes; values are read normally (resolvers may
be evaluated). Empty input leaves the destination unchanged. Scalar input is
a no-op, as in legacy. Only the empty string invokes this behavior.

## fill_from replaces contents

`fill_from` and `fillFrom` replace all previous contents, including with mapping
sources. This intentionally differs from legacy Python mapping input, which
merged entries. Use explicit update operations to retain unmentioned nodes.
The existing atomic preparation and replacement behavior remains unchanged.

## Node lists are snapshots

`get_nodes()` / `getNodes()` returns a new list of the current nodes, unlike
legacy unfiltered access to the internal list. Nodes themselves are shared,
not copied. Mutating the result list does not change the Bag; modifying a node
does. Later structural changes are not reflected in an earlier list. Filtered
results follow the same rule. Use public Bag operations for structural changes.
Compatibility mixins deliberately retain this snapshot contract.
