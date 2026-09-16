# Query resolver evaluation

Query classification, value extraction and recursion now reuse one value read
per visited node occurrence. This is a correctness/performance improvement,
not a compatibility migration. It does not alter resolver cache settings.

- Null/None is a resolved value, not a signal to read again.
- Repeated value columns use the same value within one result row.
- A later query resolves uncached nodes again.
- Label/attribute-only queries do not resolve values unless classification or
  descent requires them.
- Static mode still does not invoke resolvers. Iterators stay lazy and limits
  prevent unnecessary descent.
- Values resolved explicitly by user callbacks or nested field lookups are
  outside this per-node guarantee.

Python uses `query(..., static=False)` for dynamic resolution. JavaScript uses
its existing final `isStatic` positional argument; public signatures are unchanged.
