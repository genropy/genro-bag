"""Pytest configuration and fixtures for comparative testing.

Provides fixtures that yield Bag classes from three implementations:
- original: gnr.core.gnrbag (Genropy's original monolithic Bag)
- new: genro_bag (modern modular rewrite)
- wrapper: replacement.gnrbag (compatibility wrapper over genro_bag)
"""

import pytest
import genro_bag
from gnr.core.gnrbag import Bag as OriginalBag
from genro_toolbox import reset_smartasync_cache
from replacement.gnrbag import Bag as WrapperBag


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test."""
    reset_smartasync_cache()
    yield


@pytest.fixture(
    params=["original", "new", "wrapper"],
    ids=["original", "new", "wrapper"],
)
def bag_class(request):
    """Return a Bag class for the given implementation."""
    if request.param == "original":
        return OriginalBag
    elif request.param == "new":
        return genro_bag.Bag
    else:
        return WrapperBag


@pytest.fixture(
    params=["original", "wrapper"],
    ids=["original", "wrapper"],
)
def bag_class_camel(request):
    """Bag class that supports camelCase API (getItem, setItem, addItem, etc.)."""
    if request.param == "original":
        return OriginalBag
    else:
        return WrapperBag


@pytest.fixture(
    params=["new", "wrapper"],
    ids=["new", "wrapper"],
)
def bag_class_snake(request):
    """Bag class with snake_case API (new + wrapper only)."""
    if request.param == "new":
        return genro_bag.Bag
    else:
        return WrapperBag


@pytest.fixture
def impl_name(bag_class):
    """Return the implementation name for the current bag_class."""
    module = bag_class.__module__
    if module == "gnr.core.gnrbag":
        return "original"
    elif module.startswith("genro_bag"):
        return "new"
    else:
        return "wrapper"
