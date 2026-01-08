# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builders for domain-specific Bag construction.

This module provides builder classes for creating structured Bag hierarchies
with validation support. Builders enable fluent APIs for specific domains
like HTML, XML schemas, etc.

Builder Types:
    - **BagBuilderBase**: Abstract base class for custom builders
    - **HtmlBuilder**: HTML5 document builder with element validation
    - **XsdBuilder**: Dynamic builder from XML Schema (XSD) files

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import HtmlBuilder
    >>>
    >>> store = Bag(builder=HtmlBuilder())
    >>> body = store.body()
    >>> div = body.div(id='main')
    >>> div.p(value='Hello, World!')

XSD Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import XsdBuilder
    >>>
    >>> xsd_content = open('invoice.xsd').read()
    >>> schema = Bag.from_xml(xsd_content)
    >>> builder = XsdBuilder(schema)
    >>>
    >>> invoice = Bag(builder=builder)
    >>> invoice.Invoice().Header().Date(value='2025-01-01')
"""

from genro_bag.builders.base import BagBuilderBase, element
from genro_bag.builders.html import HtmlBuilder
from genro_bag.builders.validations import Max, MaxLength, Min, MinLength, Pattern
from genro_bag.builders.xsd import XsdBuilder

__all__ = [
    "BagBuilderBase",
    "element",
    "Pattern",
    "Min",
    "Max",
    "MinLength",
    "MaxLength",
    "HtmlBuilder",
    "XsdBuilder",
]
