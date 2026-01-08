# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pytest configuration and fixtures."""

import pytest

from genro_toolbox import reset_smartasync_cache

from genro_bag import Bag


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test.

    This ensures that async context detection starts fresh for each test,
    preventing state leakage between sync and async tests.
    """
    reset_smartasync_cache(Bag.get_node)
    reset_smartasync_cache(Bag.get_item)
    yield
