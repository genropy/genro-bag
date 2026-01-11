# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""RNG (RELAX NG) builder for Bag.

This module provides:
- RngBuilder: Dynamic builder from RNG schema

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.rng import RngBuilder
    >>>
    >>> bag = Bag(builder=RngBuilder, builder_rng_source='schema.rng')
    >>> doc = bag.html()
"""

from .rng_schema import RngBuilder

__all__ = ["RngBuilder"]
