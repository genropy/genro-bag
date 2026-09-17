"""Private parameter views shared by native and compatibility resolver APIs."""
from collections.abc import MutableMapping


class ResolverExtras(MutableMapping):
    """Live view of extras in the current load context or persistent state."""

    def __init__(self, resolver):
        self.resolver = resolver

    def _declared(self, key):
        return (key in self.resolver.class_kwargs
                or key in self.resolver.class_args
                or key in self.resolver.internal_params)

    def __iter__(self):
        return (key for key in self.resolver._parameter_values() if not self._declared(key))

    def __len__(self):
        return sum(1 for _ in self)

    def __getitem__(self, key):
        if self._declared(key):
            raise KeyError(key)
        return self.resolver._parameter_values()[key]

    def __setitem__(self, key, value):
        if self._declared(key):
            raise KeyError(f"{key!r} is a declared or internal parameter, not an extra")
        self.resolver._parameter_values()[key] = value

    def __delitem__(self, key):
        self[key]
        del self.resolver._parameter_values()[key]

    def copy(self):
        return dict(self)
