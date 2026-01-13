# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builders for Bag.

This module provides:
- XsdBuilder: Dynamic builder that parses XSD at runtime
- XsdReader: Low-level XSD parser for schema generation

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.xsd import XsdBuilder
    >>>
    >>> bag = Bag(builder=XsdBuilder, builder_xsd_source='pain.001.001.12.xsd')
    >>> doc = bag.Document()
"""

from .xsd_builder import XsdBuilder
from .xsd_reader import XsdReader

__all__ = ["XsdBuilder", "XsdReader"]
