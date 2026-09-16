# Dictionary conversion

Python: `bag.as_dict(ascii=False, lower=False, recursive=False, exclude_null_values=False)`.
The camel-case alias uses `excludeNullValues`.
JavaScript: `bag.asDict(ascii=false, lower=false, recursive=false, excludeNullValues=false)`.

Defaults and the first two arguments are unchanged. Recursive conversion converts
nested Bags only; ordinary dictionaries, objects and arrays retain their identity.
Null exclusion removes None in Python and null/undefined in JS. Empty Bags,
strings, zero and false remain. Attributes are not exported. Values are read
normally, including resolver evaluation. Conversion does not mutate the source.
Options propagate to nested Bags. This is a tree conversion, not a cycle-aware
object graph clone.

The GenroJS compatibility mixin retains `asDict(recursive, excludeNullValues)`.
Its legacy behavior additionally supports `recursive='flat'` (later keys win),
`_autolist` arrays, exclusion of empty Bags, and omission of strings ending in
`::JS` from object results. These conventions do not apply to the new libraries.
