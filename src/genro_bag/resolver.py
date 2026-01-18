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

Retry Policy:
    - retry_policy = None -> NO retry (default)
    - retry_policy = "network" -> use predefined RETRY_POLICIES["network"]
    - retry_policy = {...} -> custom policy dict
"""

from __future__ import annotations

import asyncio
import functools
import importlib
import json
import random
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from genro_toolbox import smartasync

# =============================================================================
# RETRY POLICIES - predefined configurations
# =============================================================================

RETRY_POLICIES: dict[str, dict[str, Any]] = {
    "network": {
        "max_attempts": 3,
        "delay": 1.0,
        "backoff": 2.0,
        "jitter": True,
        "on": (ConnectionError, TimeoutError, OSError),
    },
    "aggressive": {
        "max_attempts": 5,
        "delay": 0.5,
        "backoff": 2.0,
        "jitter": True,
        "on": (Exception,),
    },
    "gentle": {
        "max_attempts": 2,
        "delay": 2.0,
        "backoff": 1.5,
        "jitter": False,
        "on": (ConnectionError, TimeoutError),
    },
}


# =============================================================================
# RETRY DECORATOR
# =============================================================================


def with_retry(func: Callable) -> Callable:
    """Decorator that adds retry logic based on resolver's retry_policy.

    Reads self._kw["retry_policy"] to determine retry behavior:
    - None: no retry, execute function directly
    - str: lookup in RETRY_POLICIES dict
    - dict: use as custom policy

    Policy dict keys:
    - max_attempts: maximum number of attempts (default: 3)
    - delay: initial delay between retries in seconds (default: 1.0)
    - backoff: multiplier for delay after each retry (default: 2.0)
    - jitter: add random jitter to delay (default: True)
    - on: tuple of exception types to retry on (default: (Exception,))
    """
    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        policy = _get_retry_policy(self)
        if policy is None:
            return func(self, *args, **kwargs)

        max_attempts = policy.get("max_attempts", 3)
        delay = policy.get("delay", 1.0)
        backoff = policy.get("backoff", 2.0)
        jitter = policy.get("jitter", True)
        exceptions = policy.get("on", (Exception,))

        last_error = None
        current_delay = delay

        for attempt in range(max_attempts):
            try:
                return func(self, *args, **kwargs)
            except exceptions as e:
                last_error = e
                if attempt < max_attempts - 1:
                    sleep_time = current_delay
                    if jitter:
                        sleep_time *= (1 + random.random() * 0.1)
                    time.sleep(sleep_time)
                    current_delay *= backoff

        raise last_error  # type: ignore[misc]

    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        policy = _get_retry_policy(self)
        if policy is None:
            return await func(self, *args, **kwargs)

        max_attempts = policy.get("max_attempts", 3)
        delay = policy.get("delay", 1.0)
        backoff = policy.get("backoff", 2.0)
        jitter = policy.get("jitter", True)
        exceptions = policy.get("on", (Exception,))

        last_error = None
        current_delay = delay

        for attempt in range(max_attempts):
            try:
                return await func(self, *args, **kwargs)
            except exceptions as e:
                last_error = e
                if attempt < max_attempts - 1:
                    sleep_time = current_delay
                    if jitter:
                        sleep_time *= (1 + random.random() * 0.1)
                    await asyncio.sleep(sleep_time)
                    current_delay *= backoff

        raise last_error  # type: ignore[misc]

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def _get_retry_policy(resolver) -> dict[str, Any] | None:
    """Get retry policy from resolver, resolving string references."""
    policy = resolver._kw.get("retry_policy")
    if policy is None:
        return None
    if isinstance(policy, str):
        return RETRY_POLICIES.get(policy)
    return policy

if TYPE_CHECKING:
    from .bagnode import BagNode


class BagResolver:
    """BagResolver is an abstract class for dynamically computed values.

    A resolver allows a BagNode to have a value that is computed on-demand
    instead of being stored statically. The result can be cached for a
    configurable duration.

    Parameter Flow:
        Parameters can come from three sources, with priority (highest first):
        1. call_kwargs: passed to get_item()/get_value() at call time
        2. node.attr: attributes on the parent BagNode
        3. resolver._kw: default parameters set at resolver construction

        The resolver merges these into effective_kw before calling load().
        Cache is invalidated when effective parameters change.

        Example flow:
            bag.get_item('data', x=10)  # call_kwargs: x=10
                -> node.get_value(x=10)
                    -> resolver(x=10)
                        -> effective_kw = {**resolver._kw, **node.attr, x: 10}
                        -> load() uses self._kw (which is effective_kw)

    read_only Mode:
        - read_only=True: Each call invokes load(). Result is NOT stored in
          node._value. Good for computed/dynamic values.
        - read_only=False (default): Result is stored in node._value and cached.
          Good for expensive operations.
        NOTE: If cache_time != 0, read_only is forced to False.

    Class Attributes:
        class_kwargs: dict of {param_name: default_value}
            Parameters with defaults, passable as keyword args.
            - 'cache_time': 0 = no cache, >0 = TTL seconds, <0 = infinite
            - 'read_only': if True, value is NOT saved in node._value
            - 'retry_policy': retry config or preset name ('network', 'aggressive')

        class_args: list of positional parameter names
            Required parameters, passable as positional args.

        internal_params: set of parameter names that are internal
            These parameters (cache_time, read_only, retry_policy) are NOT
            read from node.attr during parameter merging. They control
            resolver behavior, not computation parameters.

    Example:
        class CalcResolver(BagResolver):
            class_kwargs = {'cache_time': 60, 'multiplier': 2}
            class_args = ['base']
            internal_params = {'cache_time', 'read_only', 'retry_policy'}

            def load(self):
                return self._kw['base'] * self._kw['multiplier']

        bag['calc'] = CalcResolver(10, multiplier=3)  # base=10, multiplier=3
        bag['calc']  # -> 30 (uses resolver defaults)

        bag.set_attr('calc', multiplier=5)  # override via node attr
        bag['calc']  # -> 50 (reads multiplier from node.attr)

        bag.get_item('calc', multiplier=7)  # override via call_kwargs
        # -> 70 (call_kwargs has highest priority)
    """

    class_kwargs: dict[str, Any] = {"cache_time": 0, "read_only": False, "retry_policy": None}
    class_args: list[str] = []
    internal_params: set[str] = {"cache_time", "read_only", "retry_policy"}

    __slots__ = (
        "_kw",  # dict: all parameters from class_kwargs/class_args
        "_init_args",  # list: original positional args (for serialize)
        "_init_kwargs",  # dict: original keyword args (for serialize)
        "_parent_node",  # BagNode | None: bidirectional link to parent
        "_fingerprint",  # int: hash for __eq__ comparison
        "_cache_last_update",  # datetime | None: last load() timestamp
        "_cached_value",  # Any: cached result when standalone (no parent node)
        "_last_effective_fingerprint",  # int | None: fingerprint of last effective params
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
        self._cached_value: Any = None
        self._last_effective_fingerprint: int | None = None

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

    def _compute_effective_fingerprint(self, effective_kw: dict[str, Any]) -> int:
        """Compute hash based on effective parameters for cache invalidation."""
        return hash(json.dumps(effective_kw, sort_keys=True, default=str))

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
        return self._kw.get("cache_time", 0)  # type: ignore[no-any-return]

    # =========================================================================
    # READ ONLY PROPERTY
    # =========================================================================

    @property
    def read_only(self) -> bool:
        """Whether resolver is in read-only mode.

        Returns False if cache_time != 0 (caching requires storing value).
        """
        if self.cache_time != 0:
            return False
        return self._kw.get("read_only", False)  # type: ignore[no-any-return]

    # =========================================================================
    # CACHED VALUE PROPERTY
    # =========================================================================

    @property
    def cached_value(self) -> Any:
        """Get cached value from parent node or local storage."""
        return self._parent_node._value if self._parent_node else self._cached_value

    @cached_value.setter
    def cached_value(self, value: Any) -> None:
        """Set cached value in parent node or local storage."""
        if self._parent_node:
            self._parent_node._value = value
        else:
            self._cached_value = value

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def reset(self) -> None:
        """Invalidate cache, forcing reload on next call."""
        self._cache_last_update = None
        self._last_effective_fingerprint = None

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
    # ASYNC PROPERTIES
    # =========================================================================

    @property
    def is_async(self) -> bool:
        """Whether this resolver is async (implements async_load).

        Returns True if subclass overrides async_load(), False if it overrides load().
        Deduced by checking if async_load is NOT the base class NotImplementedError.
        """
        # Check if async_load was overridden (not the base class version)
        return type(self).async_load is not BagResolver.async_load

    @property
    def in_async_context(self) -> bool:
        """Whether we are currently running inside an async context.

        Returns True if there's a running event loop, False otherwise.
        """
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    # =========================================================================
    # __call__ - MAIN ENTRY POINT
    # =========================================================================

    def __call__(self, static: bool = False, **call_kwargs: Any) -> Any:
        """Resolve and return the value.

        Args:
            static: If True, return cached value without triggering load.
            **call_kwargs: Override parameters for this call only.

        Returns:
            The resolved value, or a coroutine if in async context.

        Parameter Priority (highest to lowest):
            1. call_kwargs: Parameters passed to this call
            2. node.attr: Attributes on the parent node (if attached)
            3. resolver._kw: Default parameters set at construction

        Cache Invalidation:
            Cache is invalidated when the effective parameters (after merging)
            differ from the parameters used in the last load. This is detected
            by comparing fingerprints of the effective_kw dict.
        """
        if static:
            return self.cached_value

        # Build effective parameters: resolver < node < call_kwargs
        effective_kw = dict(self._kw)
        if self._parent_node:
            for key in self._kw:
                if key not in self.internal_params and key in self._parent_node.attr:
                    effective_kw[key] = self._parent_node.attr[key]
        effective_kw.update(call_kwargs)

        # Compute fingerprint of effective parameters
        current_fingerprint = self._compute_effective_fingerprint(effective_kw)

        # Check if cache is still valid (same params AND not expired)
        if (
            not self.read_only
            and current_fingerprint == self._last_effective_fingerprint
            and not self.expired
        ):
            return self.cached_value

        # Parameters changed or cache expired, need to reload
        self._last_effective_fingerprint = current_fingerprint

        # Temporarily set _kw to effective_kw for load()
        original_kw = self._kw
        self._kw = effective_kw
        try:
            return self._dispatch_load()
        finally:
            self._kw = original_kw

    def _dispatch_load(self) -> Any:
        """Dispatch to correct load method based on sync/async context."""
        match (self.is_async, self.in_async_context):
            case (False, False):
                return self._sync_sync_load()
            case (False, True):
                return self._sync_async_load()
            case (True, False):
                return self._async_sync_load()
            case (True, True):
                return self._async_async_load()

    # =========================================================================
    # LOAD VARIANTS - 4 cases (is_async, in_async_context)
    # =========================================================================

    def _finalize_result(self, result: Any) -> Any:
        """Store result in cache and node (if not read_only)."""
        self._cache_last_update = datetime.now()
        if not self.read_only:
            self.cached_value = result
        return result

    @with_retry
    def _sync_sync_load(self) -> Any:
        """Sync resolver in sync context - calls load()."""
        return self._finalize_result(self.load())

    @with_retry
    @smartasync
    def _sync_async_load(self) -> Any:
        """Sync resolver in async context - wraps load() for async."""
        return self._finalize_result(self.load())

    @with_retry
    def _async_sync_load(self) -> Any:
        """Async resolver in sync context - runs async_load() synchronously."""
        result = smartasync(self.async_load)()
        return self._finalize_result(result)

    @with_retry
    async def _async_async_load(self) -> Any:
        """Async resolver in async context - awaits async_load()."""
        return self._finalize_result(await self.async_load())

    # =========================================================================
    # METHODS TO OVERRIDE IN SUBCLASSES
    # =========================================================================

    def load(self) -> Any:
        """Override this for SYNC resolvers.

        Implement this method in subclasses that perform synchronous operations
        (e.g., file system access, CPU-bound computations).

        Returns:
            The resolved value (e.g., Bag, dict, or any other type).

        Example:
            class FileResolver(BagResolver):
                def load(self):
                    return Path(self._kw['path']).read_text()
        """
        raise NotImplementedError("Sync resolvers must implement load()")

    async def async_load(self) -> Any:
        """Override this for ASYNC resolvers.

        Implement this method in subclasses that perform asynchronous operations
        (e.g., network requests, async I/O).

        Returns:
            The resolved value (e.g., Bag, dict, or any other type).

        Example:
            class UrlResolver(BagResolver):
                async def async_load(self):
                    async with httpx.AsyncClient() as client:
                        response = await client.get(self._kw['url'])
                        return response.text
        """
        raise NotImplementedError("Async resolvers must implement async_load()")

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
        return resolver_cls(*data.get("args", ()), **data.get("kwargs", {}))  # type: ignore[no-any-return]

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
    Extra kwargs are passed to the callback when load() is called.

    Parameters (class_args):
        callback: Callable that returns the value. Can be sync or async.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 0 (no cache).
        read_only: If True, value is not stored in node._value. Default False.

    Example:
        >>> def somma(a, b):
        ...     return a + b
        >>> resolver = BagCbResolver(somma, a=3, b=5)
        >>> resolver()  # returns 8
        8

        >>> # Parameters are stored in node attributes when attached
        >>> bag = Bag()
        >>> bag.set_item('calc', resolver)
        >>> bag['calc']  # returns 8
        8
        >>> bag.set_attr('calc', a=10)  # changes parameter, invalidates cache
        >>> bag['calc']  # returns 15
        15

        >>> # With async callback
        >>> async def fetch_data(url, timeout=30):
        ...     async with httpx.AsyncClient() as client:
        ...         return await client.get(url, timeout=timeout)
        >>> resolver = BagCbResolver(fetch_data, url='http://...', timeout=10)
        >>> await resolver()  # works in async context
    """

    class_kwargs = {"cache_time": 0, "read_only": False}
    class_args = ["callback"]
    internal_params = {"cache_time", "read_only", "retry_policy", "callback"}

    @property
    def is_async(self) -> bool:
        """Check if callback is async."""
        return asyncio.iscoroutinefunction(self._kw["callback"])

    def load(self) -> Any:
        """Call sync callback with parameters from _kw."""
        params = {k: v for k, v in self._kw.items() if k not in self.internal_params}
        return self._kw["callback"](**params)

    async def async_load(self) -> Any:
        """Call async callback with parameters from _kw."""
        params = {k: v for k, v in self._kw.items() if k not in self.internal_params}
        return await self._kw["callback"](**params)
