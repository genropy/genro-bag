# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builder for Bag.

This module provides:
- XsdBuilder: Abstract base for XSD-based builders

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.xsd import XsdBuilder
    >>>
    >>> class PainBuilder(XsdBuilder):
    ...     xsd_source = 'pain.001.001.12.xsd'
    ...
    >>> bag = Bag(builder=PainBuilder)
    >>> doc = bag.Document()
"""

from .xsd_schema_builder import XsdSchemaBuilder

__all__ = ["XsdSchemaBuilder"]
