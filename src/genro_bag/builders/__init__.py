# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builders for domain-specific Bag construction.

This module provides builder classes for creating structured Bag hierarchies
with validation support. Builders enable fluent APIs for specific domains
like HTML, XML schemas, etc.

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import HtmlBuilder
    >>>
    >>> store = Bag(builder=HtmlBuilder())
    >>> body = store.body()
    >>> div = body.div(id='main')
    >>> div.p(value='Hello, World!')
"""

from genro_bag.builders.base import BagBuilderBase
from genro_bag.builders.decorators import element
from genro_bag.builders.html import HtmlBodyBuilder, HtmlBuilder, HtmlHeadBuilder, HtmlPage

__all__ = [
    "BagBuilderBase",
    "element",
    "HtmlBuilder",
    "HtmlHeadBuilder",
    "HtmlBodyBuilder",
    "HtmlPage",
]
