# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag package - hierarchical data container.

This package assembles the Bag class from its mixin modules.
Public API: Bag, BagException.
"""

from genro_bag.bag._core import Bag, BagException

__all__ = ["Bag", "BagException"]
