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
    - cache_time = 0      -> NO cache, load() called ALWAYS
    - cache_time > 0      -> passive cache for N seconds (TTL, reload on next access)
    - cache_time = False  -> INFINITE cache (until manual reset())

Synchronous active triggers:
    - reactive = True     -> auto-refresh when a non-internal param changes
    - reset(refresh=True) -> explicit eager refresh + notify subscribers

Retry Policy:
    - retry_policy = None -> NO retry (default)
    - retry_policy = "network" -> use predefined RETRY_POLICIES["network"]
    - retry_policy = {...} -> custom policy dict
"""

from __future__ import annotations

import functools
import importlib
import inspect
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from genro_toolbox import RETRY_PRESETS, retry_call

# =============================================================================
# RETRY POLICIES - backward-compatible alias for genro_toolbox.RETRY_PRESETS
# =============================================================================
from genro_bag._camel_names import (
    BagResolverNamesMixin,
    translate_legacy_resolver_kwargs,
)

RETRY_POLICIES = RETRY_PRESETS


# =============================================================================
# RETRY DECORATOR
# =============================================================================


def with_retry(func: Callable) -> Callable:
    """Decorator that adds retry logic based on resolver's retry_policy.

    Reads self._kw["retry_policy"] to determine retry behavior:
    - None: no retry, execute function directly
    - str: lookup in RETRY_PRESETS dict
    - dict: use as custom policy

    Delegates to genro_toolbox.retry_call for the actual retry logic.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        policy = _get_retry_policy(self)
        if policy is None:
            return func(self, *args, **kwargs)
        return retry_call(func, args=(self, *args), kwargs=kwargs, policy=policy)
    return wrapper


def _get_retry_policy(resolver) -> dict[str, Any] | None:
    """Get retry policy from resolver, resolving string references."""
    policy = resolver._kw.get("retry_policy")
    if policy is None:
        return None
    if isinstance(policy, str):
        return RETRY_PRESETS.get(policy)
    result: dict[str, Any] = policy
    return result

if TYPE_CHECKING:
    from .bagnode import BagNode


class BagResolver(BagResolverNamesMixin):
    """BagResolver is an abstract class for dynamically computed values.

    A resolver allows a BagNode to have a value that is computed on-demand
    instead of being stored statically. The result can be cached for a
    configurable duration.

    Parameter Flow:
        Parameters come from two sources, with priority (highest first):
        1. node.attr: attributes on the parent BagNode (mutable)
        2. resolver._kw: defaults set at resolver construction

        Passing kwargs to the call (get_item/get_value) is syntactic sugar
        for set_attr(**kwargs) followed by the read: changing arguments is
        modelled as "updating the resolver state", not as a transient
        override. This preserves the invariant that a cached value is always
        coherent with the current node.attr.

        Example flow:
            bag.get_item('data', x=10)
                ≡ bag.set_attr('data', x=10); bag['data']
                -> merge node.attr (x=10) with resolver._kw (defaults)
                -> load(); cache + node.attr stay coherent

    read_only Mode:
        - read_only=True: Each call invokes load(). Result is NOT stored in
          node._value. Good for computed/dynamic values.
        - read_only=False (default): Result is stored in node._value and cached.
          Good for expensive operations.
        NOTE: If cache_time != 0, read_only is forced to False.

    Reactive Mode:
        - reactive=True: When a non-internal param changes via set_attr, the
          resolver refreshes immediately on the caller thread and emits an update
          event. Enables synchronous dataflow cascades.
        - Incompatible with read_only.

    Class Attributes:
        class_kwargs: dict of {param_name: default_value}
            Parameters with defaults, passable as keyword args.
            - 'cache_time': 0 = no cache, >0 = passive TTL, False = infinite
            - 'interval': only None is supported; scheduling belongs outside the Bag
            - 'reactive': False = lazy, True = push-refresh on param change
            - 'read_only': if True, value is NOT saved in node._value
            - 'retry_policy': retry config or preset name ('network', 'aggressive')

        class_args: list of positional parameter names
            Required parameters, passable as positional args.

        internal_params: set of parameter names that are internal
            These parameters (cache_time, interval, reactive, read_only,
            retry_policy, as_bag) are NOT read from node.attr during merging
            and do NOT trigger reactive refresh. They control resolver
            behavior, not computation.

    Example:
        class CalcResolver(BagResolver):
            class_kwargs = {'cache_time': 60, 'multiplier': 2}
            class_args = ['base']

            def load(self):
                return self.kw['base'] * self.kw['multiplier']

        bag['calc'] = CalcResolver(10, multiplier=3)  # base=10, multiplier=3
        bag['calc']  # -> 30 (uses resolver defaults)

        bag.set_attr('calc', multiplier=5)  # update via node attr
        bag['calc']  # -> 50 (reads multiplier from node.attr)

        bag.get_item('calc', multiplier=7)  # override via call_kwargs
        # -> 70 (call_kwargs has highest priority)
    """

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "interval": None,
        "reactive": False,
        "read_only": False,
        "retry_policy": None,
        "as_bag": None,
    }
    class_args: list[str] = []
    internal_params: set[str] = {
        "cache_time", "interval", "reactive", "read_only", "retry_policy", "as_bag",
    }

    __slots__ = (
        "_kw",  # dict: all parameters from class_kwargs/class_args
        "_init_args",  # list: original positional args (for serialize)
        "_init_kwargs",  # dict: original keyword args (for serialize)
        "_legacy_init_kwargs",  # dict: original spellings for legacy serialization
        "_parent_node",  # BagNode | None: bidirectional link to parent
        "_cache_last_update",  # datetime | None: last load() timestamp
        "_cached_value",  # Any: cached result when standalone (no parent node)
        "_refresh_running",  # bool: a refresh is currently executing
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the resolver.

        Handles a flexible parameter system:
        1. positional args -> mapped to _kw[class_args[i]]
        2. named kwargs -> mapped to _kw[name] if in class_kwargs
        3. extra kwargs -> also saved in _kw

        At the end calls self.init() as a hook for subclasses.
        """
        # Save original args/kwargs to enable re-serialization.
        self._init_args: list[Any] = list(args)
        self._legacy_init_kwargs: dict[str, Any] = dict(kwargs)
        kwargs = translate_legacy_resolver_kwargs(kwargs)
        self._init_kwargs: dict[str, Any] = dict(kwargs)

        # Parent node reference - set by BagNode when resolver is assigned
        self._parent_node: BagNode | None = None

        # Cache state
        self._cache_last_update: datetime | None = None
        self._cached_value: Any = None

        # Prevent recursive synchronous refresh.
        self._refresh_running: bool = False

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

        # Validate parameters
        ct = self._kw.get("cache_time", 0)
        if isinstance(ct, (int, float)) and not isinstance(ct, bool) and ct < 0:
            raise ValueError(
                f"cache_time={ct!r} is no longer supported. "
                "Use cache_time=False for infinite caching."
            )

        if self._kw.get("interval") is not None:
            raise ValueError("interval is not supported; schedule refresh outside the Bag")
        if inspect.iscoroutinefunction(self.load) or (
            type(self).load is BagResolver.load and hasattr(type(self), "async_load")
        ):
            raise TypeError("BagResolver requires synchronous load(); async_load() is not supported")

        if self._kw.get("reactive") and self._init_kwargs.get("read_only") is True:
            raise ValueError(
                "read_only=True is incompatible with reactive=True: the "
                "reactive refresh writes the value to the node for subscribers "
                "to observe, but read_only prevents that write. Use read_only=False "
                "or drop reactive."
            )

        # Hook for subclasses
        self.init()

    # =========================================================================
    # EQUALITY
    # =========================================================================

    def __eq__(self, other: object) -> bool:
        """Two resolvers are equal if same class and same parameters."""
        if not isinstance(other, self.__class__):
            return False
        return self._init_args == other._init_args and self._kw == other._kw

    # =========================================================================
    # PARENT NODE PROPERTY
    # =========================================================================

    @property
    def parent_node(self) -> BagNode | None:
        """Get the parent node this resolver is attached to."""
        return self._parent_node

    @parent_node.setter
    def parent_node(self, parent_node: BagNode | None) -> None:
        """Set the parent node and validate scheduling options."""
        if self._parent_node is not None and parent_node is None:
            self._stop_interval()
        self._parent_node = parent_node
        if parent_node is not None:
            self._start_interval()

    # =========================================================================
    # CACHE TIME PROPERTY
    # =========================================================================

    @property
    def cache_time(self) -> int | float | bool:
        """Get cache time setting (expiration policy).

        Returns:
            0: no cache, reload on every access.
            N>0: passive TTL, cache valid for N seconds.
            False: infinite cache (until manual reset()).

        Note:
            Refresh scheduling belongs outside the Bag.
        """
        return self._kw.get("cache_time", 0)  # type: ignore[no-any-return]

    # =========================================================================
    # INTERVAL PROPERTY (mutable: assignment reconfigures the timer)
    # =========================================================================

    @property
    def interval(self) -> int | float | None:
        """Compatibility setting; only None is supported."""
        return self._kw.get("interval")

    @interval.setter
    def interval(self, value: int | float | None) -> None:
        """Reject automatic scheduling."""
        if value is not None:
            raise ValueError("interval is not supported; schedule refresh outside the Bag")
        self._kw["interval"] = None

    # =========================================================================
    # KW PROPERTY (transformed kwargs for load)
    # =========================================================================

    @property
    def kw(self) -> dict[str, Any]:
        """Pre-processed kwargs, result of on_loading(self._kw).

        Subclasses' load() must read from self.kw (not self._kw)
        so that on_loading transformations are visible. Default on_loading is
        identity, so self.kw returns self._kw unchanged.
        """
        result = self.on_loading(self._kw)
        self._require_sync_result(result)
        return result

    # =========================================================================
    # REACTIVE PROPERTY (mutable)
    # =========================================================================

    @property
    def reactive(self) -> bool:
        """Whether the resolver auto-refreshes on parameter change.

        When True, any set_attr on the parent node that changes a domain
        parameter (non-internal) triggers reset(refresh=True) instead of the
        default lazy reset(). Refreshes execute immediately on the caller thread.
        """
        return bool(self._kw.get("reactive"))

    @reactive.setter
    def reactive(self, value: bool) -> None:
        """Toggle reactive behavior after construction.

        Rejects the read_only + reactive combination as at construction.
        """
        if value and self._init_kwargs.get("read_only") is True:
            raise ValueError(
                "read_only=True is incompatible with reactive=True: the "
                "reactive refresh writes the value to the node for subscribers "
                "to observe, but read_only prevents that write."
            )
        self._kw["reactive"] = bool(value)

    # =========================================================================
    # READ ONLY PROPERTY
    # =========================================================================

    @property
    def read_only(self) -> bool:
        """Whether resolver is in read-only mode.

        If True, the resolved value is NOT stored in node._value.
        If not explicitly passed, derived from cache_time, interval, reactive:
        no cache and no active trigger → read_only=True, otherwise read_only=False.
        """
        if "read_only" in self._init_kwargs:
            return self._init_kwargs["read_only"]  # type: ignore[no-any-return]
        if self._kw.get("interval") is not None or self._kw.get("reactive"):
            return False
        return self.cache_time is not False and self.cache_time == 0

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

    def reset(self, refresh: bool = False) -> None:
        """Invalidate the cache; refresh=True reloads and notifies synchronously."""
        self._cache_last_update = None
        if not refresh:
            return
        if self.read_only:
            raise ValueError("reset(refresh=True) is incompatible with read_only=True")
        if self._refresh_running:
            return
        self._refresh_running = True
        try:
            self._kw = self._build_effective_kw()
            self._finalize_result_and_notify(self.load())
        finally:
            self._refresh_running = False

    def _start_interval(self) -> None:
        """Reject automatic scheduling; retained for node attachment compatibility."""
        if self.interval is not None:
            raise ValueError("interval is not supported; schedule refresh outside the Bag")

    def _stop_interval(self) -> None:
        """Compatibility hook: synchronous resolvers own no background timers."""

    @property
    def expired(self) -> bool:
        """Check if cache has expired."""
        cache_time = self.cache_time
        if cache_time is False:
            # Infinite cache: only expired if never loaded
            return self._cache_last_update is None
        if cache_time == 0:
            return True
        elapsed = datetime.now() - (self._cache_last_update or datetime.min)
        return elapsed > timedelta(seconds=cache_time)

    # =========================================================================
    # ASYNC PROPERTIES
    # =========================================================================

    @property
    def is_async(self) -> bool:
        """Compatibility property: resolvers always execute synchronously."""
        return False

    # =========================================================================
    # __call__ - MAIN ENTRY POINT
    # =========================================================================

    def __call__(self, static: bool = False, **call_kwargs: Any) -> Any:
        """Resolve and return the value.

        Args:
            static: If True, return cached value without triggering load.
            **call_kwargs: Parameters for this call. They update node.attr
                (or resolver._kw for standalone resolvers) — "changing
                arguments = updating resolver state". No temporary overrides.

        Returns:
            The resolved value, synchronously in every execution context.

        Semantic rule:
            node.attr is the current input of the resolver. When cached,
            node._value is coherent with node.attr. Passing kwargs updates
            node.attr (visible to subscribers via upd_attrs) and then runs
            the normal pull path — so the new cached value is coherent with
            the new attributes.

            Standalone resolvers (no parent_node) update self._kw directly.

        Parameter Priority (highest to lowest at merge time):
            1. node.attr: Attributes on the parent node (if attached)
            2. resolver._kw: Defaults from construction
        """
        if static:
            return self.cached_value

        # call_kwargs update the resolver state before the load. When attached,
        # they go through node.attr (emitting upd_attrs and, when reactive,
        # performing the refresh via the existing set_attr hook). Standalone
        # resolvers update _kw directly since there is no node.
        if call_kwargs:
            if self._parent_node is not None:
                self._parent_node.set_attr(**call_kwargs)
            else:
                self._kw.update(call_kwargs)
                self._cache_last_update = None

        # Without call_kwargs: use cache if valid
        if not self.read_only and not self.expired:
            return self.cached_value

        # Cache expired or read_only: reload
        return self._load_with_kw(self._build_effective_kw())

    def _build_effective_kw(self) -> dict[str, Any]:
        """Build effective parameters by merging resolver._kw with node.attr."""
        effective_kw = dict(self._kw)
        if self._parent_node:
            for key in self._kw:
                if key not in self.internal_params and key in self._parent_node.attr:
                    effective_kw[key] = self._parent_node.attr[key]
        return effective_kw

    def _load_with_kw(self, effective_kw: dict[str, Any]) -> Any:
        """Execute load with the given effective parameters.

        Assigns effective_kw to self._kw permanently: changing arguments is
        modelled as "updating the resolver state", not as a transient swap.
        """
        self._kw = effective_kw
        return self._dispatch_load()

    def _dispatch_load(self) -> Any:
        """Load directly on the caller's thread in every execution context."""
        return self._sync_sync_load()

    def _prepare_result(self, result: Any) -> Any:
        """Common post-load processing: as_bag conversion + timestamp update.

        Conversion to Bag (controlled by as_bag parameter):
        - as_bag=True: always convert to Bag if possible
        - as_bag=False: never convert, keep original value
        - as_bag not set (None): convert only if read_only=False (implicit as_bag=True)

        Convertible types:
        - dict/list: Bag(dict) or indexed Bag
        - str starting with '<': Bag.from_xml()
        - str starting with '{' or '[': Bag.from_json()
        - bytes: decoded and parsed as XML/JSON
        - Bag: returned as-is
        """
        self._require_sync_result(result)
        as_bag = self._kw.get("as_bag")
        if as_bag is True:
            should_convert = True
        elif as_bag is False:
            should_convert = False
        else:
            # as_bag not explicitly set: convert if will be cached (not read_only)
            should_convert = not self.read_only

        if should_convert and result is not None and self.parent_node is not None:
            bag_class = self.parent_node.parent_bag.__class__
            if not isinstance(result, bag_class):
                try:
                    bag = bag_class()
                    bag.fill_from(result)
                    if len(bag):
                        result = bag
                except (TypeError, FileNotFoundError, ValueError):
                    pass  # Not convertible to Bag — keep original result
        result = self.on_loaded(result)
        self._require_sync_result(result)
        self._cache_last_update = datetime.now()
        return result

    def _finalize_result(self, result: Any) -> Any:
        """Store result in cache silently (passive, pull-driven path).

        Used by the pull path: reading a node with a resolver calls load()
        and writes the result without emitting a mutation event. A pull is
        a read, not a semantic mutation.
        """
        result = self._prepare_result(result)
        if not self.read_only:
            self.cached_value = result
        return result

    def _finalize_result_and_notify(self, result: Any) -> Any:
        """Store result through the node mutation channel (active path).

        Used by synchronous refresh and reactive parameter changes:
        writes via parent_node.set_value(), which fires _on_node_changed
        so subscribers receive an update event.

        Falls back to silent write if the resolver has no parent_node or
        is read_only (no observable target for the event).
        """
        result = self._prepare_result(result)
        if self.read_only:
            return result
        if self._parent_node is not None:
            self._parent_node.set_value(result)
        else:
            self.cached_value = result
        return result

    @with_retry
    def _sync_sync_load(self) -> Any:
        """Sync resolver in sync context - calls load()."""
        return self._finalize_result(self.load())

    @staticmethod
    def _require_sync_result(result: Any) -> None:
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError("BagResolver requires a synchronous value; awaitable results are not supported")

    def load(self) -> Any:
        """Override this for SYNC resolvers.

        Implement this method in subclasses that perform synchronous operations
        (e.g., file system access, CPU-bound computations).

        Returns:
            The resolved value (e.g., Bag, dict, or any other type).

        Example:
            class FileResolver(BagResolver):
                def load(self):
                    return Path(self.kw['path']).read_text()
        """
        raise NotImplementedError("Sync resolvers must implement load()")

    def init(self) -> None:
        """Hook called at the end of __init__.

        Subclasses can override for additional setup
        without having to manage super().__init__().
        """
        pass

    def on_loading(self, kw: dict[str, Any]) -> dict[str, Any]:
        """Pre-processing hook applied to kwargs before load().

        Default implementation is identity: returns kw unchanged.

        Subclasses override to transform inputs (e.g. resolve path pointers,
        inject defaults, normalize values). Must return a COMPLETE dict with
        the same keys as input, not a delta — some resolvers (url_resolver,
        BagCbResolver) iterate over the full kwargs dict.

        Called via the self.kw property; load() implementations read self.kw
        (not self._kw) so transformations are visible.
        """
        return kw

    def on_loaded(self, result: Any) -> Any:
        """Post-processing hook applied after load() and _prepare_result.

        Default implementation is identity: returns result unchanged.

        Subclasses override to adapt the produced value (e.g. filter,
        decorate, normalize). Runs AFTER the as_bag conversion in
        _prepare_result, so if as_bag=True the hook receives a Bag.
        """
        return result

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

        The named class must be a BagResolver subclass: the payload chooses
        the class name, never its ancestry, so this check cannot be forged.
        Without it any importable callable would be instantiated with
        payload-supplied arguments.

        The returned resolver is inert — it is built, never called. Any I/O
        happens later, when the caller reads the value.

        Args:
            data: Dict from serialize()

        Returns:
            New Resolver instance with same parameters.

        Raises:
            ValueError: If the named class is not a BagResolver subclass.
        """
        module = importlib.import_module(data["resolver_module"])
        resolver_cls = getattr(module, data["resolver_class"])
        if not (isinstance(resolver_cls, type) and issubclass(resolver_cls, BagResolver)):
            raise ValueError(
                f"{data['resolver_module']}.{data['resolver_class']} is not a "
                f"BagResolver subclass: refusing to instantiate it."
            )
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


class BagSyncResolver(BagResolver):
    """Compatibility base for explicitly synchronous resolvers."""


class BagCbResolver(BagSyncResolver):
    """Resolver that calls a **sync** callback function to get the value.

    Extra kwargs are passed to the callback when load() is called. The
    callback must be a plain function returning a synchronous value.

    Parameters (class_args):
        callback: Sync callable that returns the value.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 0 (no cache).
        read_only: If True, value is not stored in node._value. Default False.

    Raises:
        TypeError: If ``callback`` is a coroutine function.

    Example:
        >>> def somma(a, b):
        ...     return a + b
        >>> resolver = BagCbResolver(somma, a=3, b=5)
        >>> resolver()  # returns 8
        8
    """

    class_kwargs = {"cache_time": 0, "interval": None, "read_only": False, "as_bag": False}
    class_args = ["callback"]
    internal_params = BagResolver.internal_params | {"callback"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cb = self._kw.get("callback")
        if inspect.iscoroutinefunction(cb):
            raise TypeError(
                "BagCbResolver requires a sync callback. "
                "Run asynchronous work outside the Bag."
            )

    def load(self) -> Any:
        """Call sync callback with parameters from kw."""
        params = {k: v for k, v in self.kw.items() if k not in self.internal_params}
        return self.kw["callback"](**params)


class BagAsyncCbResolver(BagResolver):
    """Removed asynchronous callback API, retained for a clear migration error."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "BagAsyncCbResolver is no longer supported; "
            "use BagCbResolver with a synchronous callback"
        )
