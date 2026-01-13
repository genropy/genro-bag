# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder - HTML5 element builder with W3C schema validation.

This module provides builders for generating HTML5 documents. The schema
is loaded from a pre-compiled MessagePack file generated from W3C Validator
RELAX NG schema files using SchemaBuilder.

Example:
    Creating an HTML document::

        from genro_bag import Bag
        from genro_bag.builders import HtmlBuilder

        store = Bag(builder=HtmlBuilder)
        body = store.body()
        div = body.div(id='main', class_='container')
        div.h1(value='Welcome')
        div.p(value='Hello, World!')
        ul = div.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...builder import BagBuilderBase

if TYPE_CHECKING:
    from ...bagnode import BagNode


class HtmlBuilder(BagBuilderBase):
    """Builder for HTML5 elements.

    Uses pre-compiled schema loaded via schema_path. All element handling
    is provided by BagBuilderBase.__getattr__.

    Usage:
        >>> bag = Bag(builder=HtmlBuilder)
        >>> bag.div(id='main').p(value='Hello')
        >>> bag.ul().li(value='Item 1')
    """

    schema_path = Path(__file__).parent / "html5_schema.bag.mp"

    def compile(self, destination: str | Path | None = None) -> str:
        """Compile the bag to HTML.

        Args:
            destination: If provided, write HTML to this file path.

        Returns:
            HTML string representation.
        """
        lines = []
        for node in self.bag:
            lines.append(self._node_to_html(node, indent=0))
        html = "\n".join(lines)

        if destination:
            Path(destination).write_text(html)

        return html

    def _node_to_html(self, node: BagNode, indent: int = 0) -> str:
        """Recursively convert a node to HTML."""
        from ...bag import Bag

        tag = node.tag or node.label
        attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith("_"))
        attrs_str = f" {attrs}" if attrs else ""
        spaces = "  " * indent

        node_value = node.get_value(static=True)
        is_leaf = not isinstance(node_value, Bag)

        if is_leaf:
            # Void elements: empty string or None value
            if node_value == "" or node_value is None:
                return f"{spaces}<{tag}{attrs_str}>"
            return f"{spaces}<{tag}{attrs_str}>{node_value}</{tag}>"

        lines = [f"{spaces}<{tag}{attrs_str}>"]
        for child in node_value:
            lines.append(self._node_to_html(child, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)
