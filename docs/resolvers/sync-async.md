# Synchronous resolvers

Bag access and resolver loading are synchronous in every execution context,
including inside a running event loop. A resolver implements `def load(self)`
and returns its final value. Nested path traversal and legacy `getItem()` obey
the same contract; no thread, task, or coroutine is created automatically.

```python
from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver

bag = Bag({'answer': BagCbResolver(lambda: 42)})
assert bag['answer'] == 42

async def handler():
    assert bag['answer'] == 42  # still a direct synchronous access
```

`async def load`, `async_load`-only resolvers, async callbacks, and awaitable
loader results are rejected. `BagAsyncCbResolver` remains importable only to
raise an explicit migration error when constructed. Move asynchronous I/O
outside the Bag and store its completed result as ordinary data.

`reset()` invalidates the cache lazily. `reset(refresh=True)` reloads inline;
reactive attribute changes also refresh inline. Their errors propagate to the
caller. There is no next-tick coalescing or background execution.

Resolver intervals and Bag timer subscriptions are unsupported. The application
owns any scheduler and calls synchronous Bag operations when work is due.
