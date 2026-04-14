"""Pytest configuration and fixtures for comparative testing.

Provides fixtures that yield Bag classes from four implementations:
- original: gnr.core.gnrbag (Genropy's original monolithic Bag)
- new: genro_bag (modern modular rewrite)
- wrapper: replacement.gnrbag (compatibility wrapper over genro_bag)
- new_wrapper: replacement.gnrbag_wrapper (deprecation wrapper with __getattr__)
"""

import sys
from pathlib import Path

# Ensure tests/ directory is importable (for helpers.py)
_tests_dir = str(Path(__file__).parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

import pytest  # noqa: E402
from genro_toolbox import reset_smartasync_cache  # noqa: E402
from gnr.core.gnrbag import Bag as OriginalBag  # noqa: E402
from helpers import impl_name_from_class  # noqa: E402
from replacement.gnrbag import Bag as WrapperBag  # noqa: E402
from replacement.gnrbag_wrapper import Bag as NewWrapperBag  # noqa: E402

import genro_bag  # noqa: E402


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test."""
    reset_smartasync_cache()
    yield


@pytest.fixture(
    params=["original", "new", "wrapper", "new_wrapper"],
    ids=["original", "new", "wrapper", "new_wrapper"],
)
def bag_class(request):
    """Return a Bag class for the given implementation."""
    if request.param == "original":
        return OriginalBag
    elif request.param == "new":
        return genro_bag.Bag
    elif request.param == "wrapper":
        return WrapperBag
    else:
        return NewWrapperBag


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
    return impl_name_from_class(bag_class)
