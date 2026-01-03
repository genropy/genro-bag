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

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from genro_toolbox import SmartLock, smartasync, smartawait

if TYPE_CHECKING:
    from .bag_node import BagNode


class BagResolver:
    """BagResolver is an abstract class for dynamically computed values.

    A resolver allows a BagNode to have a value that is computed on-demand
    instead of being stored statically. The result can be cached for a
    configurable duration.

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

    class_kwargs: dict[str, Any] = {'cache_time': 0, 'read_only': True}
    class_args: list[str] = []

    __slots__ = (
        '_kw',                  # dict: all parameters from class_kwargs/class_args
        '_init_args',           # list: original positional args (for serialize)
        '_init_kwargs',         # dict: original keyword args (for serialize)
        '_parent_node',         # BagNode | None: bidirectional link to parent
        '_fingerprint',         # int: hash for __eq__ comparison
        '_cache_last_update',   # datetime | None: last load() timestamp
        '_async_lock',          # SmartLock: for concurrent access
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

        # Async concurrency control (created on-demand)
        self._async_lock: SmartLock = SmartLock()

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
        import json
        data = {
            'resolver_class': self.__class__.__name__,
            'resolver_module': self.__class__.__module__,
            'args': self._init_args,
            'kwargs': self._kw,
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
        return self._kw.get('cache_time', 0)

    # =========================================================================
    # READ ONLY PROPERTY
    # =========================================================================

    @property
    def read_only(self) -> bool:
        """Whether resolver is in read-only mode."""
        return self._kw.get('read_only', True)

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

    def __call__(self, **kwargs: Any) -> Any:
        """Resolve and return the value.

        For read_only=True: kwargs are merged temporarily for this call only.
        For read_only=False: kwargs ignored, uses concurrency control.

        Returns:
            The resolved value from load().
        """
        if self.read_only:
            # Pure getter mode: always call load(), no concurrency control
            if kwargs:
                original_kw = self._kw
                self._kw = {**original_kw, **kwargs}
                try:
                    return self.load()
                finally:
                    self._kw = original_kw
            return self.load()

        # Cached mode: use concurrency control
        return self._resolve_cached()

    @smartasync
    async def _resolve_cached(self) -> Any:
        """Resolve with concurrency control for read_only=False.

        Ensures only one load() runs at a time. Other callers wait
        for the result via Future.

        Returns:
            The resolved value, or None to signal Node to use _value.
        """
        # Fast path: cache valid
        if not self.expired:
            return None  # Signal Node to use cached _value

        return await self._async_lock.run_once(self._do_load)

    async def _do_load(self) -> Any:
        """Execute load and update cache timestamp."""
        # Double-check after acquiring lock
        if not self.expired:
            return None  # Another caller completed while we waited

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
            'resolver_module': self.__class__.__module__,
            'resolver_class': self.__class__.__name__,
            'args': list(self._init_args),
            'kwargs': dict(self._kw),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> BagResolver:
        """Recreate resolver from serialized data.

        Args:
            data: Dict from serialize()

        Returns:
            New Resolver instance with same parameters.
        """
        import importlib
        module = importlib.import_module(data['resolver_module'])
        resolver_cls = getattr(module, data['resolver_class'])
        return resolver_cls(*data.get('args', ()), **data.get('kwargs', {}))

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
