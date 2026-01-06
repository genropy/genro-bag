# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagResolver module - lazy/dynamic value resolution for BagNodes.

This module provides the BagResolver class, which enables lazy loading
of values in BagNodes. Instead of storing a static value, a node can
have a resolver that computes the value on-demand.

Key Concepts:
    - The resolver is CALLABLE: use resolver() to get the value
    - Supports CACHING with TTL (time-to-live)
    - The resolved value is typically a Bag (for hierarchical navigation)
    - Proxy methods (keys, items, etc.) delegate to the resolved Bag

Caching Semantics:
    - cache_time = 0  -> NO cache, load() called ALWAYS
    - cache_time > 0  -> cache for N seconds (TTL)
    - cache_time < 0  -> INFINITE cache (until manual reset())
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from genro_toolbox import smartasync, smartawait

if TYPE_CHECKING:
    from .bagnode import BagNode


class BagResolver:
    """BagResolver is an abstract class for dynamically computed values.

    A resolver allows a BagNode to have a value that is computed on-demand
    instead of being stored statically. The result can be cached for a
    configurable duration.

    read_only Mode (how BagNode.get_value interacts with resolver):
        - read_only=True (default): Each call to get_value() invokes resolver(),
          which calls load(). The result is returned directly, NOT stored in
          node._value. Good for computed/dynamic values that shouldn't be cached
          in the node itself.

        - read_only=False: When cache expires, get_value() calls resolver() which
          calls load(), then stores the result in node._value. Subsequent calls
          return node._value until cache expires again. Good for expensive
          operations where you want the node to hold the cached result.

    Class Attributes:
        class_kwargs: dict of {param_name: default_value}
            Parameters with defaults, passable as keyword args.
            - 'cache_time': 0 = no cache, >0 = TTL in seconds, <0 = infinite cache
            - 'read_only': if True, resolved value is NOT saved in node._value

        class_args: list of positional parameter names
            Required parameters, passable as positional args.
            Order in class_args corresponds to order in *args.

    Example:
        class UrlResolver(BagResolver):
            class_kwargs = {'cache_time': 300, 'read_only': False, 'timeout': 30}
            class_args = ['url']

            def load(self):
                return fetch(self._kw['url'], timeout=self._kw['timeout'])

        resolver = UrlResolver('http://...', cache_time=60)
        # resolver._kw['url'] = 'http://...'
        # resolver._kw['cache_time'] = 60 (overrides default 300)
        # resolver._kw['timeout'] = 30 (default)
    """

    class_kwargs: dict[str, Any] = {"cache_time": 0, "read_only": True}
    class_args: list[str] = []

    __slots__ = (
        "_kw",  # dict: all parameters from class_kwargs/class_args
        "_init_args",  # list: original positional args (for serialize)
        "_init_kwargs",  # dict: original keyword args (for serialize)
        "_parent_node",  # BagNode | None: bidirectional link to parent
        "_fingerprint",  # int: hash for __eq__ comparison
        "_cache_last_update",  # datetime | None: last load() timestamp
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the resolver.

        Handles a flexible parameter system:
        1. positional args -> mapped to _kw[class_args[i]]
        2. named kwargs -> mapped to _kw[name] if in class_kwargs
        3. extra kwargs -> also saved in _kw

        At the end calls self.init() as a hook for subclasses.
        """
        # Save original args/kwargs to enable re-serialization
        self._init_args: list[Any] = list(args)
        self._init_kwargs: dict[str, Any] = dict(kwargs)

        # Parent node reference - set by BagNode when resolver is assigned
        self._parent_node: BagNode | None = None

        # Cache state
        self._cache_last_update: datetime | None = None

        # Build _kw dict from class_args and class_kwargs
        self._kw: dict[str, Any] = {}

        # Map positional args to _kw
        # Ex: UrlResolver('http://...') -> _kw['url'] = 'http://...'
        class_kwargs_copy = dict(self.class_kwargs)
        for j, arg in enumerate(args):
            parname = self.class_args[j]
            self._kw[parname] = arg
            class_kwargs_copy.pop(parname, None)
            kwargs.pop(parname, None)

        # Map class_kwargs with defaults
        for parname, dflt in class_kwargs_copy.items():
            self._kw[parname] = kwargs.pop(parname, dflt)

        # Extra kwargs also go to _kw
        self._kw.update(kwargs)

        # Compute fingerprint for equality comparison
        self._fingerprint: int = self._compute_fingerprint()

        # Hook for subclasses
        self.init()

    # =========================================================================
    # EQUALITY
    # =========================================================================

    def __eq__(self, other: object) -> bool:
        """Two resolvers are equal if same class and same fingerprint."""
        if not isinstance(other, self.__class__):
            return False
        return self._fingerprint == other._fingerprint

    def _compute_fingerprint(self) -> int:
        """Compute hash based on class and parameters."""
        data = {
            "resolver_class": self.__class__.__name__,
            "resolver_module": self.__class__.__module__,
            "args": self._init_args,
            "kwargs": self._kw,
        }
        return hash(json.dumps(data, sort_keys=True, default=str))

    # =========================================================================
    # PARENT NODE PROPERTY
    # =========================================================================

    @property
    def parent_node(self) -> BagNode | None:
        """Get the parent node this resolver is attached to."""
        return self._parent_node

    @parent_node.setter
    def parent_node(self, parent_node: BagNode | None) -> None:
        """Set the parent node."""
        self._parent_node = parent_node

    # =========================================================================
    # CACHE TIME PROPERTY
    # =========================================================================

    @property
    def cache_time(self) -> int:
        """Get cache time in seconds."""
        return self._kw.get("cache_time", 0)

    # =========================================================================
    # READ ONLY PROPERTY
    # =========================================================================

    @property
    def read_only(self) -> bool:
        """Whether resolver is in read-only mode."""
        return self._kw.get("read_only", True)

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def reset(self) -> None:
        """Invalidate cache, forcing reload on next call."""
        self._cache_last_update = None

    @property
    def expired(self) -> bool:
        """Check if cache has expired."""
        cache_time = self.cache_time
        if cache_time == 0:
            return True
        # None means never updated, or datetime.min makes elapsed > any TTL
        elapsed = datetime.now() - (self._cache_last_update or datetime.min)
        if cache_time < 0:
            # Infinite cache: only expired if never loaded
            return self._cache_last_update is None
        return elapsed > timedelta(seconds=cache_time)

    # =========================================================================
    # __call__ - MAIN ENTRY POINT
    # =========================================================================

    @smartasync
    async def __call__(self, **kwargs: Any) -> Any:
        """Resolve and return the value.

        Behavior depends on read_only mode:
        - read_only=True: Always calls load(). If kwargs provided, they are
          merged temporarily into _kw for this call only, then restored.
        - read_only=False: Uses caching. If cache not expired, returns None
          (signaling BagNode.get_value to use node._value). If expired, calls
          load() and returns the result for BagNode to store.

        Args:
            **kwargs: Temporary parameter overrides (only for read_only=True).

        Returns:
            The resolved value from load(), or None if cached (read_only=False).
        """
        if self.read_only:
            # Pure getter mode: always call load(), no concurrency control
            if kwargs:
                original_kw = self._kw
                self._kw = {**original_kw, **kwargs}
                try:
                    return await smartawait(self.load())
                finally:
                    self._kw = original_kw
            return await smartawait(self.load())

        # Cached mode (read_only=False)
        return await smartawait(self._resolve_cached())

    @smartasync
    async def _resolve_cached(self) -> Any:
        """Resolve with caching for read_only=False mode.

        Called when read_only=False. Checks cache expiration and either:
        - Returns None if cache valid (BagNode.get_value uses node._value)
        - Calls load() if expired, updates timestamp, returns result

        Returns:
            The resolved value if cache expired, or None to signal
            BagNode.get_value to use the cached node._value.
        """
        if not self.expired:
            return None  # Signal Node to use cached _value

        result = await smartawait(self.load())
        self._cache_last_update = datetime.now()
        return result

    # =========================================================================
    # METHODS TO OVERRIDE IN SUBCLASSES
    # =========================================================================

    @smartasync
    async def load(self) -> Any:
        """Load and return the resolved value.

        MUST be overridden in subclasses.
        Use @smartasync decorator for sync/async compatibility.

        Returns:
            The resolved value (e.g., Bag, dict, or any other type).

        Raises:
            NotImplementedError: If not overridden in subclass.
        """
        raise NotImplementedError("Subclasses must implement load()")

    def init(self) -> None:
        """Hook called at the end of __init__.

        Subclasses can override for additional setup
        without having to manage super().__init__().
        """
        pass

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def serialize(self) -> dict[str, Any]:
        """Serialize resolver for persistence/transport.

        Returns:
            Dict with all info to recreate the resolver:
            - resolver_module: Module path
            - resolver_class: Class name
            - args: Original positional arguments
            - kwargs: All parameters including defaults
        """
        return {
            "resolver_module": self.__class__.__module__,
            "resolver_class": self.__class__.__name__,
            "args": list(self._init_args),
            "kwargs": dict(self._kw),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> BagResolver:
        """Recreate resolver from serialized data.

        Args:
            data: Dict from serialize()

        Returns:
            New Resolver instance with same parameters.
        """
        module = importlib.import_module(data["resolver_module"])
        resolver_cls = getattr(module, data["resolver_class"])
        return resolver_cls(*data.get("args", ()), **data.get("kwargs", {}))

    # =========================================================================
    # PROXY METHODS - DELEGATE TO RESOLVED BAG
    # =========================================================================

    def __getitem__(self, k: str) -> Any:
        """Proxy for bag[key]. Resolves and delegates."""
        return self()[k]

    def _htraverse(self, *args: Any, **kwargs: Any) -> Any:
        """Proxy for _htraverse. Resolves and delegates."""
        return self()._htraverse(*args, **kwargs)

    def get_node(self, k: str) -> Any:
        """Proxy for get_node. Resolves and delegates."""
        return self().get_node(k)

    def keys(self) -> list[str]:
        """Proxy for keys(). Resolves and delegates."""
        return list(self().keys())

    def items(self) -> list[tuple[str, Any]]:
        """Proxy for items(). Resolves and delegates."""
        return list(self().items())

    def values(self) -> list[Any]:
        """Proxy for values(). Resolves and delegates."""
        return list(self().values())


class BagCbResolver(BagResolver):
    """Resolver that calls a callback function to get the value.

    The callback can be sync or async - handled automatically.

    Parameters (class_args):
        callback: Callable that returns the value. Can be sync or async.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 0 (no cache).
        read_only: If True, resolver acts as pure getter. Default True.

    Example:
        >>> from datetime import datetime
        >>> resolver = BagCbResolver(datetime.now)
        >>> resolver()  # returns current datetime
        datetime.datetime(2026, 1, 5, 10, 30, 45, 123456)

        >>> # With async callback
        >>> async def fetch_data():
        ...     await asyncio.sleep(0.1)
        ...     return {'status': 'ok'}
        >>> resolver = BagCbResolver(fetch_data)
        >>> await resolver()  # works in async context
        {'status': 'ok'}

        >>> # With caching
        >>> resolver = BagCbResolver(datetime.now, cache_time=60)
        >>> t1 = resolver()
        >>> t2 = resolver()  # same value, cached
        >>> t1 == t2
        True
    """

    class_kwargs = {"cache_time": 0, "read_only": True}
    class_args = ["callback"]

    @smartasync
    async def load(self) -> Any:
        """Call the callback and return its result.

        Uses @smartasync to work in both sync and async contexts.
        Uses smartawait to handle both sync and async callbacks.

        Returns:
            The value returned by the callback.

        Raises:
            TypeError: If callback is not callable.
        """
        callback: Callable[[], Any] = self._kw["callback"]
        return await smartawait(callback())
