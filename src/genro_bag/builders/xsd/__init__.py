# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builder for Bag.

This module provides:
- XsdBuilder: Dynamic builder from XSD schema

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.xsd import XsdBuilder
    >>>
    >>> xsd_content = open('schema.xsd').read()
    >>> schema = Bag.from_xml(xsd_content)
    >>> builder = XsdBuilder(schema)
"""

from .xsd_schema import XsdBuilder

__all__ = ["XsdBuilder"]
