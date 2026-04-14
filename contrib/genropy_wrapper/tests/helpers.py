"""Shared test helpers for comparative wrapper testing."""


def impl_name_from_class(bag_class):
    """Return 'original', 'new', 'wrapper', or 'new_wrapper' for a Bag class."""
    mod = bag_class.__module__
    if mod.startswith("gnr."):
        return "original"
    elif mod.startswith("genro_bag"):
        return "new"
    elif "gnrbag_wrapper" in mod:
        return "new_wrapper"
    return "wrapper"


def make_nested_bag(cls):
    """Create a nested bag: a={x:1, y:2}, b={z:3}, c=4."""
    b = cls()
    inner_a = cls()
    inner_a["x"] = 1
    inner_a["y"] = 2
    b["a"] = inner_a
    inner_b = cls()
    inner_b["z"] = 3
    b["b"] = inner_b
    b["c"] = 4
    return b


def make_flat_bag(cls):
    """Create a flat bag: name=Alice, age=30, city=Rome."""
    b = cls()
    b["name"] = "Alice"
    b["age"] = 30
    b["city"] = "Rome"
    return b
