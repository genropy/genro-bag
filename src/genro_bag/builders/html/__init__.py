# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML5 builder package.

Provides HtmlBuilder for creating HTML5 documents with W3C schema validation.
The schema is pre-compiled from W3C Validator RELAX NG files.

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import HtmlBuilder
    >>>
    >>> doc = Bag(builder=HtmlBuilder)
    >>> doc.body().div(id='main').p(value='Hello')
"""

from .html_builder import HtmlBuilder

__all__ = ["HtmlBuilder"]
