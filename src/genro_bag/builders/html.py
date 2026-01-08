# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder - HTML5 element builder with W3C schema validation.

This module provides builders for generating HTML5 documents. The schema
is loaded from a pre-compiled MessagePack file generated from W3C Validator
RELAX NG schema files.

Example:
    Creating an HTML document::

        from genro_bag import Bag
        from genro_bag.builders import HtmlBuilder

        store = Bag(builder=HtmlBuilder())
        body = store.body()
        div = body.div(id='main', class_='container')
        div.h1(value='Welcome')
        div.p(value='Hello, World!')
        ul = div.ul()
        ul.li(value='Item 1')
        ul.li(value='Item 2')
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BagBuilderBase

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


# Cache for loaded schema
_schema_cache: dict | None = None


def _load_html5_schema() -> dict:
    """Load HTML5 schema from pre-compiled MessagePack.

    Returns:
        Dict with 'elements' (set) and 'void_elements' (set).
    """
    global _schema_cache

    if _schema_cache is not None:
        return _schema_cache

    from ..bag import Bag

    schema_file = Path(__file__).parent / "schemas" / "html5_schema.msgpack"

    if not schema_file.exists():
        raise FileNotFoundError(
            f"HTML5 schema not found: {schema_file}\nRun: python scripts/build_html5_schema.py"
        )

    schema_bag = Bag.from_tytx(
        schema_file.read_bytes(),
        transport="msgpack",
    )

    elements_node = schema_bag.get_node("_elements")
    void_node = schema_bag.get_node("_void_elements")

    _schema_cache = {
        "elements": frozenset(elements_node.value) if elements_node else frozenset(),
        "void_elements": frozenset(void_node.value) if void_node else frozenset(),
    }

    return _schema_cache


class HtmlBuilder(BagBuilderBase):
    """Builder for HTML5 elements.

    Provides dynamic methods for all 112 HTML5 tags via __getattr__.
    Void elements (meta, br, img, etc.) automatically use empty string value.

    The schema is loaded from a pre-compiled MessagePack file generated
    from W3C Validator RELAX NG schema files.

    Usage:
        >>> bag = Bag(builder=HtmlBuilder)
        >>> bag.div(id='main').p(value='Hello')
        >>> bag.ul().li(value='Item 1')

    Attributes:
        VOID_ELEMENTS: Set of void (self-closing) element names.
        ALL_TAGS: Set of all valid HTML5 element names.
    """

    def __init__(self, bag: Bag):
        """Initialize HtmlBuilder with W3C HTML5 schema."""
        super().__init__(bag)
        self._schema_data = _load_html5_schema()

    @property
    def VOID_ELEMENTS(self) -> frozenset[str]:
        """Void elements (self-closing, no content)."""
        return self._schema_data["void_elements"]  # type: ignore[no-any-return]

    @property
    def ALL_TAGS(self) -> frozenset[str]:
        """All valid HTML5 element names."""
        return self._schema_data["elements"]  # type: ignore[no-any-return]

    def __getattr__(self, name: str) -> Callable[..., Bag | BagNode]:
        """Dynamic method for any HTML tag.

        Args:
            name: Tag name (e.g., 'div', 'span', 'meta')

        Returns:
            Callable that creates a child with that tag.

        Raises:
            AttributeError: If name is not a valid HTML tag.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        if name in self._schema_data["elements"]:
            return self._make_tag_method(name)

        raise AttributeError(f"'{name}' is not a valid HTML tag")

    def _make_tag_method(self, name: str) -> Callable[..., Bag | BagNode]:
        """Create a method for a specific tag."""
        is_void = name in self._schema_data["void_elements"]

        def tag_method(
            _target: Bag,
            _tag: str = name,
            _label: str | None = None,
            value: Any = None,
            **attr: Any,
        ) -> Bag | BagNode:
            if is_void and value is None:
                value = ""
            return self.child(_target, _tag, _label=_label, value=value, **attr)

        return tag_method

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
        from ..bag import Bag

        tag = node.tag or node.label
        attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith("_"))
        attrs_str = f" {attrs}" if attrs else ""
        spaces = "  " * indent

        node_value = node.get_value(static=True)
        is_leaf = not isinstance(node_value, Bag)

        if is_leaf:
            if node_value == "":
                return f"{spaces}<{tag}{attrs_str}>"
            return f"{spaces}<{tag}{attrs_str}>{node_value}</{tag}>"

        lines = [f"{spaces}<{tag}{attrs_str}>"]
        for child in node_value:
            lines.append(self._node_to_html(child, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)
