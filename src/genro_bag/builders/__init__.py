# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builders for domain-specific Bag construction.

This module provides builder classes for creating structured Bag hierarchies
with validation support. Builders enable fluent APIs for specific domains
like HTML, XML schemas, Markdown, etc.

Builder Types:
    - **BagBuilderBase**: Abstract base class for custom builders
    - **SchemaBuilder**: Builder for creating schemas programmatically
    - **HtmlBuilder**: HTML5 document builder with element validation
    - **MarkdownBuilder**: Markdown document builder
    - **XsdBuilder**: Dynamic builder from XSD schema

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import HtmlBuilder
    >>>
    >>> store = Bag(builder=HtmlBuilder)
    >>> body = store.body()
    >>> div = body.div(id='main')
    >>> div.p(value='Hello, World!')
"""

from genro_bag.builder import (
    BagBuilderBase,
    Range,
    Regex,
    SchemaBuilder,
    abstract,
    element,
)
from genro_bag.builders.html import HtmlBuilder
from genro_bag.builders.markdown import MarkdownBuilder
from genro_bag.builders.xsd import XsdBuilder, XsdReader

__all__ = [
    "BagBuilderBase",
    "abstract",
    "element",
    "Range",
    "Regex",
    "HtmlBuilder",
    "MarkdownBuilder",
    "SchemaBuilder",
    "XsdBuilder",
    "XsdReader",
]
