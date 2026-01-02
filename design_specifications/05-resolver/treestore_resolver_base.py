# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""TreeStore resolver classes for lazy/dynamic value resolution.

This module provides a resolver system inspired by Genropy's BagResolver,
enabling lazy evaluation and dynamic value computation for TreeStoreNode.

Key Concepts:
    Resolvers allow a node's value to be computed on-demand rather than
    stored statically. This is useful for:

    - **Traversal resolvers**: Load hierarchical data lazily (e.g., directory
      contents, remote API responses). These resolvers populate node._value
      with a TreeStore, enabling path traversal through the resolved content.
      Typically use cache_time=-1 (infinite cache) with manual invalidation.

    - **Leaf resolvers**: Compute dynamic values that may change over time
      (e.g., sensor readings, computed metrics). These use read_only=True
      to avoid caching in the node, recalculating on each access.

Path Traversal with Resolvers:
    When accessing a path like 'alfa.beta.gamma.delta' where 'beta' has a
    resolver, the traversal:

    1. Reaches 'beta' and detects its resolver
    2. Calls resolver.load() to get the resolved TreeStore
    3. Populates beta._value with the result (for traversal to continue)
    4. Continues traversal with 'gamma.delta' in the resolved TreeStore

    If 'gamma.delta' also contains resolvers, they are resolved recursively.
    This enables lazy loading of deeply nested hierarchical structures.

Sync/Async Transparency:
    All resolvers use the @smartasync decorator on their load() method,
    providing automatic context detection:

    - From sync context: async load() is executed via asyncio.run()
    - From async context: load() returns a coroutine for normal await

    This means the same resolver works transparently in both contexts
    without requiring separate sync/async APIs.

Caching:
    Resolvers support TTL-based caching via cache_time parameter:

    - cache_time=0: No caching, always recompute (default)
    - cache_time>0: Cache for specified seconds
    - cache_time=-1: Cache forever (until manual reset() call)

    For traversal resolvers, cache_time=-1 is recommended with explicit
    invalidation via resolver.reset() when the source data changes.

Serialization:
    Resolvers can be serialized for persistence/export. The serialize()
    method stores:

    - resolver_module: The module containing the resolver class
    - resolver_class: The class name
    - args: Positional arguments passed to __init__
    - kwargs: Keyword arguments passed to __init__

    For CallbackResolver, the callback must be a top-level importable
    function for serialization to work.

Example:
    Basic resolver for lazy directory loading::

        class DirectoryResolver(TreeStoreResolver):
            def __init__(self, path, **kwargs):
                super().__init__(cache_time=-1, **kwargs)
                self.path = path
                self._init_args = (path,)

            @smartasync
            async def load(self):
                store = TreeStore()
                for name in os.listdir(self.path):
                    full_path = os.path.join(self.path, name)
                    if os.path.isdir(full_path):
                        # Subdirectories get their own resolver
                        store.set_item(name)
                        store.set_resolver(name, DirectoryResolver(full_path))
                    else:
                        store.set_item(name, full_path)
                return store

        # Usage
        store.set_item('docs')
        store.set_resolver('docs', DirectoryResolver('/path/to/docs'))

        # Lazy traversal - resolves only when accessed
        store['docs.subdir.file.txt']  # Resolves 'docs', then 'subdir'

    Sensor resolver (read_only, no caching)::

        class TemperatureResolver(TreeStoreResolver):
            def __init__(self, sensor_id, **kwargs):
                super().__init__(cache_time=0, read_only=True, **kwargs)
                self.sensor_id = sensor_id

            @smartasync
            async def load(self):
                return read_sensor(self.sensor_id)

        # Each access reads the current temperature
        node.resolver = TemperatureResolver('sensor_1')
        print(node.value)  # 22.5
        print(node.value)  # 22.7 (re-read)
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta
from typing import Any, Callable, TYPE_CHECKING

from genro_toolbox import smartasync

if TYPE_CHECKING:
    from ..store import TreeStoreNode


class TreeStoreResolver:
    """Base class for lazy/dynamic value resolution.

    A resolver computes a node's value on-demand instead of storing it
    statically. Subclasses must implement the load() method.

    There are two main use cases:

    1. **Traversal resolvers**: Return a TreeStore that enables further
       path navigation. The resolved TreeStore is stored in node._value
       to allow traversal to continue. Use cache_time=-1 for infinite
       caching with manual invalidation via reset().

    2. **Leaf resolvers**: Return a scalar value (temperature, computed
       result, etc.). With read_only=True and cache_time=0, each access
       recomputes the value without storing it.

    Attributes:
        parent_node: The TreeStoreNode this resolver is attached to.
            Set automatically when assigning resolver to a node.
        cache_time: Cache duration in seconds. 0=no cache, >0=seconds,
            -1=infinite (until reset() is called).
        read_only: If True, resolved value is not stored in node._value.
            Only applies when accessing node.value directly, not during
            path traversal (which always populates _value).

    Example:
        Subclass and implement load()::

            class MyResolver(TreeStoreResolver):
                @smartasync
                async def load(self):
                    return await fetch_data()

            node.resolver = MyResolver(cache_time=300)
            value = node.value  # Triggers load(), caches for 5 minutes
    """

    __slots__ = (
        "parent_node",
        "_cache_time",
        "read_only",
        "_cache",
        "_cache_timestamp",
        "_cache_time_delta",
        "_init_args",
        "_init_kwargs",
    )

    def __init__(
        self,
        cache_time: int = 0,
        read_only: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the resolver.

        Args:
            cache_time: Cache duration in seconds.
                - 0: No caching, always recompute (default).
                - >0: Cache result for this many seconds.
                - -1: Cache forever until reset() is called. Recommended
                  for traversal resolvers with manual invalidation.
            read_only: If True, resolved value is not stored in node._value
                when accessing node.value directly. Note: during path
                traversal, _value is always populated regardless of this
                setting, to enable navigation through the resolved TreeStore.
            **kwargs: Additional arguments stored in _init_kwargs for
                serialization. Subclasses should store their custom
                parameters here.
        """
        self.parent_node: TreeStoreNode | None = None
        self.read_only = read_only
        self._cache: Any = None
        self._cache_timestamp: datetime | None = None
        self._cache_time_delta: timedelta | None = None
        self._init_args: tuple = ()
        self._init_kwargs: dict[str, Any] = dict(kwargs)

        # Set cache_time via property to initialize _cache_time_delta
        self.cache_time = cache_time

    @property
    def cache_time(self) -> int:
        """Cache duration in seconds (0=none, >0=seconds, -1=infinite)."""
        return self._cache_time

    @cache_time.setter
    def cache_time(self, value: int) -> None:
        """Set cache duration and initialize internal timedelta.

        Args:
            value: Cache time in seconds. Use -1 for infinite cache.
        """
        self._cache_time = value
        if value != 0:
            if value < 0:
                self._cache_time_delta = timedelta.max
            else:
                self._cache_time_delta = timedelta(seconds=value)
            self._cache = None
            self._cache_timestamp = None

    @property
    def expired(self) -> bool:
        """Check if the cached value has expired.

        Returns:
            True if cache is expired, not present, or caching is disabled.
            False if cache is still valid.
        """
        if self._cache_time == 0:
            return True
        if self._cache_timestamp is None:
            return True
        elapsed = datetime.now() - self._cache_timestamp
        return elapsed > self._cache_time_delta

    def reset(self) -> None:
        """Invalidate the cache, forcing recomputation on next access.

        For traversal resolvers with cache_time=-1, call this method
        when the underlying data source has changed to trigger a fresh
        load() on the next access.

        Example:
            >>> resolver = DirectoryResolver('/path/to/dir', cache_time=-1)
            >>> store.set_resolver('docs', resolver)
            >>> store['docs.file.txt']  # Loads directory contents
            >>> # ... files change on disk ...
            >>> resolver.reset()  # Invalidate cache
            >>> store['docs.file.txt']  # Reloads directory contents
        """
        self._cache = None
        self._cache_timestamp = None

    def _update_cache(self, value: Any) -> None:
        """Store value in cache with current timestamp.

        Args:
            value: The resolved value to cache.
        """
        self._cache = value
        self._cache_timestamp = datetime.now()

    @smartasync
    async def load(self) -> Any:
        """Load and return the resolved value.

        Subclasses must override this method to provide the actual
        value computation. The method is decorated with @smartasync,
        enabling transparent sync/async operation:

        - From sync context: executed via asyncio.run() automatically
        - From async context: returns coroutine for normal await

        For traversal resolvers, return a TreeStore containing the
        hierarchical data. For leaf resolvers, return a scalar value.

        Returns:
            The resolved value. For traversal resolvers, this should be
            a TreeStore instance. For leaf resolvers, any value type.

        Raises:
            NotImplementedError: If not overridden in subclass.

        Example:
            Async resolver fetching remote data::

                @smartasync
                async def load(self):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(self.url) as response:
                            data = await response.json()
                    return TreeStore(data)

            Sync resolver reading local files::

                @smartasync
                async def load(self):
                    # Can be sync - smartasync handles it
                    with open(self.path) as f:
                        return f.read()
        """
        raise NotImplementedError("Subclasses must implement load()")

    def _htraverse(self, remaining_path: str | None = None) -> Any:
        """Resolve value and optionally continue path traversal.

        This method is called by TreeStoreNode.value property when
        the node has a resolver. It handles cache checking/updating
        and delegates further path navigation to the resolved result.

        Note: This method is NOT called during TreeStore._htraverse
        path traversal. During traversal, the store directly calls
        load() and populates node._value to enable navigation.

        Args:
            remaining_path: Additional path segments to traverse after
                resolution. If provided and the resolved value is a
                TreeStore, continues navigation via result.get_item().

        Returns:
            If remaining_path is empty or None: the resolved value.
            If remaining_path is provided: the value at the remaining
            path within the resolved TreeStore.

        Example:
            Direct access (no remaining path)::

                node.resolver = MyResolver()
                node.value  # Calls _htraverse(None) -> resolved value

            With remaining path (internal use)::

                resolver._htraverse('child.grandchild')
                # Returns resolved_treestore['child.grandchild']
        """
        # Check cache first
        if self._cache_time != 0 and not self.expired:
            result = self._cache
        else:
            # Load value (smartasync handles sync/async)
            result = self.load()

            # Update cache if caching is enabled
            if self._cache_time != 0:
                self._update_cache(result)

            # If not read_only, store in node's _value
            if not self.read_only and self.parent_node is not None:
                self.parent_node._value = result

        # Continue traversal if there's remaining path
        if remaining_path and hasattr(result, "get_item"):
            return result.get_item(remaining_path)

        return result

    def serialize(self) -> dict[str, Any]:
        """Serialize the resolver for persistence/export.

        Creates a dictionary containing all information needed to
        recreate the resolver via deserialize(). Based on Genropy's
        BagResolver.resolverSerialize() pattern.

        The serialized data includes:
        - resolver_module: Full module path (e.g., 'myapp.resolvers')
        - resolver_class: Class name (e.g., 'DirectoryResolver')
        - args: Positional arguments from _init_args
        - kwargs: Keyword arguments including cache_time, read_only,
          and any custom kwargs from _init_kwargs

        For CallbackResolver, the callback function must be a top-level
        importable function (not a lambda or nested function) for
        serialization to work correctly.

        Returns:
            Dictionary suitable for JSON serialization and later
            reconstruction via deserialize().

        Example:
            >>> resolver = DirectoryResolver('/path', cache_time=-1)
            >>> data = resolver.serialize()
            >>> # data = {
            >>> #     'resolver_module': 'genro_treestore.resolver',
            >>> #     'resolver_class': 'DirectoryResolver',
            >>> #     'args': ('/path',),
            >>> #     'kwargs': {'cache_time': -1, 'read_only': True}
            >>> # }
        """
        return {
            "resolver_module": self.__class__.__module__,
            "resolver_class": self.__class__.__name__,
            "args": self._init_args,
            "kwargs": {
                "cache_time": self.cache_time,
                "read_only": self.read_only,
                **self._init_kwargs,
            },
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> TreeStoreResolver:
        """Recreate a resolver from serialized data.

        Dynamically imports the resolver class and instantiates it
        with the stored arguments.

        Args:
            data: Dictionary from serialize() containing resolver_module,
                resolver_class, args, and kwargs.

        Returns:
            New resolver instance of the appropriate subclass.

        Raises:
            ModuleNotFoundError: If resolver_module cannot be imported.
            AttributeError: If resolver_class is not found in the module.

        Example:
            >>> data = {
            ...     'resolver_module': 'genro_treestore.resolver',
            ...     'resolver_class': 'CallbackResolver',
            ...     'args': (my_callback,),
            ...     'kwargs': {'cache_time': 300}
            ... }
            >>> resolver = TreeStoreResolver.deserialize(data)
        """
        module = importlib.import_module(data["resolver_module"])
        resolver_cls = getattr(module, data["resolver_class"])
        return resolver_cls(*data.get("args", ()), **data.get("kwargs", {}))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(cache_time={self.cache_time}, read_only={self.read_only})"
        )


class CallbackResolver(TreeStoreResolver):
    """Resolver that invokes a callback function to compute values.

    A simple resolver that delegates value computation to a user-provided
    function. The callback receives the parent node as its argument,
    allowing access to the node's context (label, attributes, siblings).

    This is useful for:
    - Computed values based on other nodes in the tree
    - Simple transformations or calculations
    - Quick prototyping before creating a custom resolver class

    For serialization to work, the callback must be a top-level function
    that can be imported by name (not a lambda or nested function).

    Attributes:
        callback: The function to call on each resolution.

    Example:
        Computed value based on siblings::

            def compute_total(node):
                store = node.parent
                price = store.get_item('price')
                quantity = store.get_item('quantity')
                return price * quantity

            store.set_item('price', 100)
            store.set_item('quantity', 5)
            store.set_item('total')
            store.set_resolver('total', CallbackResolver(compute_total))

            print(store['total'])  # 500

        With caching::

            resolver = CallbackResolver(
                expensive_computation,
                cache_time=300  # Cache for 5 minutes
            )
    """

    __slots__ = ("callback",)

    def __init__(
        self,
        callback: Callable[[TreeStoreNode], Any],
        **kwargs: Any,
    ) -> None:
        """Initialize the callback resolver.

        Args:
            callback: Function to invoke for value computation.
                Signature: callback(node: TreeStoreNode) -> Any
                The node parameter is the TreeStoreNode this resolver
                is attached to, providing access to node.parent (the
                containing TreeStore), node.label, node.attr, etc.
            **kwargs: Additional arguments passed to TreeStoreResolver.
                Common options: cache_time, read_only.

        Example:
            >>> def get_timestamp(node):
            ...     return datetime.now().isoformat()
            >>> resolver = CallbackResolver(get_timestamp, cache_time=0)
        """
        super().__init__(**kwargs)
        self.callback = callback
        self._init_args = (callback,)

    @smartasync
    async def load(self) -> Any:
        """Invoke the callback and return its result.

        Returns:
            The value returned by self.callback(self.parent_node).
        """
        return self.callback(self.parent_node)

    def __repr__(self) -> str:
        callback_name = getattr(self.callback, "__name__", repr(self.callback))
        return f"CallbackResolver({callback_name}, cache_time={self.cache_time})"
