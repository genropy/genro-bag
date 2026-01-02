
# RHB Specification — 03 Resolver

Resolver types:
- sync: returns value or (value, attrs)
- async: stores result in Bag path

Caching:
- cachetime 0 = no cache (sync only)
- cachetime -1 = infinite
- cachetime N seconds

Invalidation allowed externally.
