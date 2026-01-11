# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builder for Bag.

This module provides:
- XsdBuilder: Dynamic builder from XSD schema

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import XsdBuilder
    >>>
    >>> bag = Bag(builder=XsdBuilder, builder_xsd_source='schema.xsd')
    >>> doc = bag.Document()
"""

from .xsd_schema import XsdBuilder

__all__ = ["XsdBuilder"]
