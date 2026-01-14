# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pytest configuration and fixtures."""

import pytest
from genro_toolbox import reset_smartasync_cache


@pytest.fixture(autouse=True)
def reset_smartasync_caches():
    """Reset smartasync cache before each test.

    This ensures that async context detection starts fresh for each test,
    preventing state leakage between sync and async tests.
    """
    reset_smartasync_cache()
    yield
