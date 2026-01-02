# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""
Original BagResolver class extracted from gnrbag.py for reference.

This is NOT meant to be executed - just a reference document.

================================================================================
OVERVIEW
================================================================================

BagResolver is an abstract class for "lazy loading" values in BagNodes.
Instead of having a static value, a node can have a resolver that computes
the value on-demand.

Key concepts:
- The resolver is CALLABLE: use resolver() to get the value
- Supports CACHING with TTL (time-to-live)
- The resolved value is typically a Bag (for hierarchical navigation)
- Proxy methods (keys, items, etc.) delegate to the resolved Bag

================================================================================
CACHING SEMANTICS
================================================================================

cacheTime controls caching behavior:
- cacheTime = 0  -> NO cache, load() called ALWAYS
- cacheTime > 0  -> cache for N seconds (TTL)
- cacheTime < 0  -> INFINITE cache (until manual reset())

================================================================================
USAGE PATTERN
================================================================================

1. In BagNode.getValue():
   if self._resolver and self._resolver.expired:
       self.value = self._resolver()  # calls __call__

2. As transparent proxy:
   resolver.keys()  # equivalent to resolver().keys()
   resolver['foo']  # equivalent to resolver()['foo']

================================================================================
"""

from datetime import datetime, timedelta


class BagResolver(object):
    """BagResolver is an abstract class for dynamically computed values.

    A resolver allows a BagNode to have a value that is computed on-demand
    instead of being stored statically. The result can be cached for a
    configurable duration.
    """

    # =========================================================================
    # CLASS-LEVEL CONFIGURATION
    # =========================================================================
    # These class variables define the parameters accepted by the resolver.
    # Subclasses override them to declare their own parameters.
    #
    # classKwargs: dict of {param_name: default_value}
    #   - Parameters with defaults, passable as keyword args
    #   - 'cacheTime': 0 = no cache, >0 = TTL in seconds, <0 = infinite cache
    #   - 'readOnly': if True, resolved value is NOT saved in node._value
    #
    # classArgs: list of positional parameter names
    #   - Required parameters, passable as positional args
    #   - Order in classArgs corresponds to order in *args
    #
    # Subclass example:
    #   class UrlResolver(BagResolver):
    #       classKwargs = {'cacheTime': 300, 'readOnly': False, 'timeout': 30}
    #       classArgs = ['url']  # first positional arg becomes self.url
    #
    #       def load(self):
    #           return fetch(self.url, timeout=self.timeout)
    #
    #   resolver = UrlResolver('http://...', cacheTime=60)
    #   # self.url = 'http://...'
    #   # self.cacheTime = 60 (overrides default 300)
    #   # self.timeout = 30 (default)
    # =========================================================================

    classKwargs = {'cacheTime': 0, 'readOnly': True}
    classArgs = []

    def __init__(self, *args, **kwargs):
        """Initialize the resolver.

        Handles a flexible parameter system:
        1. positional args -> mapped to self.{classArgs[i]}
        2. named kwargs -> mapped to self.{name} if in classKwargs
        3. extra kwargs -> saved in self.kwargs for custom use

        At the end calls self.init() as a hook for subclasses.
        """
        # =====================================================================
        # SERIALIZATION SUPPORT
        # Save original args/kwargs to enable re-serialization
        # =====================================================================
        self._initArgs = list(args)      # original args for serialize
        self._initKwargs = dict(kwargs)  # original kwargs for serialize

        # =====================================================================
        # PARENT NODE REFERENCE
        # Set by BagNode when resolver is assigned to the node
        # =====================================================================
        self.parentNode = None

        # =====================================================================
        # KWARGS STORAGE
        # Contains "extra" kwargs not in classKwargs (for custom use)
        # =====================================================================
        self.kwargs = {}

        # =====================================================================
        # POSITIONAL ARGS -> ATTRIBUTES
        # Maps args[i] -> self.{classArgs[i]}
        # Ex: UrlResolver('http://...') -> self.url = 'http://...'
        # =====================================================================
        classKwargs = dict(self.classKwargs)  # copy to avoid modifying class
        for j, arg in enumerate(args):
            parname = self.classArgs[j]       # parameter name
            setattr(self, parname, arg)       # self.url = arg
            classKwargs.pop(parname, None)    # remove from kwargs if present
            kwargs.pop(parname, None)         # remove from passed kwargs

        # =====================================================================
        # NAMED KWARGS -> ATTRIBUTES
        # For each parameter in classKwargs:
        # - If passed in kwargs: use that value
        # - Otherwise: use default from classKwargs
        # =====================================================================
        for parname, dflt in list(classKwargs.items()):
            setattr(self, parname, kwargs.pop(parname, dflt))

        # =====================================================================
        # EXTRA KWARGS
        # Everything remaining in kwargs goes to self.kwargs
        # These are custom parameters not declared in classKwargs
        # =====================================================================
        self.kwargs.update(kwargs)

        # Also attach extra kwargs as attributes
        self._attachKwargs()

        # =====================================================================
        # LEGACY: _attributes dict (probably no longer used)
        # Original comment "ma servono ?????" suggests uncertainty
        # =====================================================================
        self._attributes = {}

        # =====================================================================
        # HOOK FOR SUBCLASSES
        # Called at the end of __init__ for additional setup
        # =====================================================================
        self.init()

    # =========================================================================
    # EQUALITY
    # =========================================================================

    def __eq__(self, other):
        """Two resolvers are equal if same class and same kwargs.

        NOTE: only compares self.kwargs, not all attributes.
        This means two resolvers with same extra kwargs but different
        classKwargs might erroneously compare as equal.
        """
        try:
            if isinstance(other, self.__class__) and (self.kwargs == other.kwargs):
                return True
        except:
            return False

    # =========================================================================
    # PARENT NODE PROPERTY
    # =========================================================================
    # The resolver maintains a reference to the BagNode containing it.
    # This allows the resolver to access context (e.g., other nodes).
    #
    # NOTE: commented code shows it originally used weakref to avoid
    # reference cycles, but this was disabled.
    # =========================================================================

    def _get_parentNode(self):
        if hasattr(self, '_parentNode'):
            return self._parentNode

    def _set_parentNode(self, parentNode):
        if parentNode == None:
            self._parentNode = None
        else:
            # Originally: self._parentNode = weakref.ref(parentNode)
            self._parentNode = parentNode

    parentNode = property(_get_parentNode, _set_parentNode)

    # =========================================================================
    # INSTANCE KWARGS (for serialization/debug)
    # =========================================================================

    def _get_instanceKwargs(self):
        """Return all current parameters (classKwargs + classArgs).

        Useful for debug or to recreate a resolver with same parameters.
        """
        result = {}
        for par, dflt in list(self.classKwargs.items()):
            result[par] = getattr(self, par)
        for par in self.classArgs:
            result[par] = getattr(self, par)
        return result

    instanceKwargs = property(_get_instanceKwargs)

    def _attachKwargs(self):
        """Attach extra kwargs as instance attributes.

        Allows accessing custom kwargs as self.my_param
        instead of self.kwargs['my_param'].
        """
        for k, v in list(self.kwargs.items()):
            setattr(self, k, v)
            if k in self.classKwargs:
                self.kwargs.pop(k)

    # =========================================================================
    # CACHE TIME PROPERTY
    # =========================================================================
    # cacheTime controls cache TTL:
    # - 0: no cache, load() called every time
    # - >0: cache for N seconds
    # - <0: infinite cache (timedelta.max)
    #
    # When cacheTime is set (non-zero), initializes:
    # - _cacheTimeDelta: maximum cache duration
    # - _cache: the cached value (initially None)
    # - _cacheLastUpdate: last update timestamp (initially datetime.min)
    # =========================================================================

    def _set_cacheTime(self, cacheTime):
        """Set cache time and initialize cache structures."""
        self._cacheTime = cacheTime
        if cacheTime != 0:
            if cacheTime < 0:
                # Infinite cache
                self._cacheTimeDelta = timedelta.max
            else:
                # Cache for N seconds
                # NOTE: timedelta(0, cacheTime) = timedelta(days=0, seconds=cacheTime)
                self._cacheTimeDelta = timedelta(0, cacheTime)
            self._cache = None
            self._cacheLastUpdate = datetime.min  # forces expired=True on first call

    def _get_cacheTime(self):
        return self._cacheTime

    cacheTime = property(_get_cacheTime, _set_cacheTime)

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def reset(self):
        """Invalidate cache, forcing reload on next call.

        Useful when you know the underlying data has changed.
        """
        self._cache = None
        self._cacheLastUpdate = datetime.min

    def _get_expired(self):
        """Check if cache has expired.

        Returns:
            True if:
            - cacheTime == 0 (no cache)
            - _cacheLastUpdate == datetime.min (never updated / reset)
            - elapsed time > _cacheTimeDelta
        """
        if self._cacheTime == 0 or self._cacheLastUpdate == datetime.min:
            return True
        return ((datetime.now() - self._cacheLastUpdate) > self._cacheTimeDelta)

    expired = property(_get_expired)

    # =========================================================================
    # __call__ - MAIN ENTRY POINT
    # =========================================================================
    # This is the method called to get the resolved value.
    # Handles caching logic and calls load() when necessary.
    #
    # Typical usage:
    #   value = resolver()  # calls __call__
    #
    # In BagNode.getValue():
    #   if self._resolver.expired:
    #       self.value = self._resolver()
    # =========================================================================

    def __call__(self, **kwargs):
        """Resolve and return the value, using cache if available.

        Args:
            **kwargs: If different from self.kwargs, updates parameters
                      and invalidates cache (forces reload).

        Returns:
            The resolved value (typically a Bag).

        Logic:
        1. If kwargs passed and different -> update and reset cache
        2. If cacheTime == 0 -> always call load()
        3. If cache expired -> call load() and update cache
        4. Otherwise -> return cached value
        """
        # If new kwargs passed, update and invalidate cache
        if kwargs and kwargs != self.kwargs:
            self.kwargs.update(kwargs)
            self._attachKwargs()
            self.reset()

        # No cache: always call load()
        if self.cacheTime == 0:
            return self.load()

        # Cache expired: reload and update
        if self.expired:
            result = self.load()
            self._cacheLastUpdate = datetime.now()
            self._cache = result
        else:
            # Cache valid: use cached value
            result = self._cache
        return result

    # =========================================================================
    # METHODS TO OVERRIDE IN SUBCLASSES
    # =========================================================================

    def load(self):
        """Load and return the resolved value.

        MUST be overridden in subclasses.
        Typically returns a Bag to enable hierarchical navigation.

        Returns:
            The resolved value (e.g., Bag, dict, or any other type).
        """
        pass

    def init(self):
        """Hook called at the end of __init__.

        Subclasses can override for additional setup
        without having to manage super().__init__().
        """
        pass

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def resolverSerialize(self, args=None, kwargs=None):
        """Serialize the resolver for persistence/export.

        Returns a dict with all info to recreate the resolver:
        - resolverclass: class name
        - resolvermodule: module containing the class
        - args: original positional arguments
        - kwargs: original keyword arguments + current cacheTime

        Returns:
            Serializable dict (for JSON/XML).

        NOTE: there is no corresponding deserialize() in the base class.
        Deserialization is handled elsewhere in Genropy code.
        """
        attr = {}
        attr['resolverclass'] = self.__class__.__name__
        attr['resolvermodule'] = self.__class__.__module__
        attr['args'] = self._initArgs
        attr['kwargs'] = self._initKwargs
        attr['kwargs']['cacheTime'] = self.cacheTime  # use current value
        return attr

    # =========================================================================
    # PROXY METHODS - DELEGATE TO RESOLVED BAG
    # =========================================================================
    # These methods allow using the resolver as if it were the resolved Bag.
    # They call self() to resolve and then delegate.
    #
    # Example:
    #   resolver['foo']  ->  self()['foo']  ->  resolved_bag['foo']
    #   resolver.keys()  ->  self().keys()  ->  resolved_bag.keys()
    #
    # This pattern makes the resolver "transparent": you can navigate
    # through it as if it were already a Bag.
    # =========================================================================

    def __getitem__(self, k):
        """Proxy for bag[key]. Resolves and delegates."""
        return self()[k]

    def _htraverse(self, *args, **kwargs):
        """Proxy for _htraverse. Resolves and delegates.

        NOTE: this does NOT implement traversal logic.
        It simply calls self() to get the resolved Bag,
        then calls _htraverse on the Bag.

        The real traversal logic lives in the Bag, not here.
        """
        return self()._htraverse(*args, **kwargs)

    def getNode(self, k):
        """Proxy for getNode. Resolves and delegates."""
        return self().getNode(k)

    def keys(self):
        """Proxy for keys(). Resolves and delegates."""
        return list(self().keys())

    def items(self):
        """Proxy for items(). Resolves and delegates."""
        return list(self().items())

    def values(self):
        """Proxy for values(). Resolves and delegates."""
        return list(self().values())
