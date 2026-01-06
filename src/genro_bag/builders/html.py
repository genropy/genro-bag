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
        >>> bag = Bag(builder=HtmlBuilder())
        >>> bag.div(id='main').p(value='Hello')
        >>> bag.ul().li(value='Item 1')

    Attributes:
        VOID_ELEMENTS: Set of void (self-closing) element names.
        ALL_TAGS: Set of all valid HTML5 element names.
    """

    def __init__(self):
        """Initialize HtmlBuilder with W3C HTML5 schema."""
        self._schema_data = _load_html5_schema()

    @property
    def VOID_ELEMENTS(self) -> frozenset[str]:
        """Void elements (self-closing, no content)."""
        return self._schema_data["void_elements"]

    @property
    def ALL_TAGS(self) -> frozenset[str]:
        """All valid HTML5 element names."""
        return self._schema_data["elements"]

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


class HtmlHeadBuilder(HtmlBuilder):
    """Builder for HTML head section.

    Allows all HTML tags but semantically intended for head content
    (meta, title, link, style, script, etc.)
    """

    pass


class HtmlBodyBuilder(HtmlBuilder):
    """Builder for HTML body section.

    Allows all HTML tags for body content generation.
    """

    pass


class HtmlPage:
    """HTML page with separate head and body Bags.

    Creates a complete HTML document structure with:
    - html root Bag
    - head Bag with HtmlHeadBuilder (metadata only)
    - body Bag with HtmlBodyBuilder (flow content)

    Usage:
        >>> page = HtmlPage()
        >>> page.head.title(value='My Page')
        >>> page.head.meta(charset='utf-8')
        >>> page.body.div(id='main').p(value='Hello World')
        >>> html = page.to_html()
    """

    def __init__(self):
        """Initialize the page with head and body."""
        from ..bag import Bag

        self.html = Bag()
        self.head = Bag(builder=HtmlHeadBuilder())
        self.body = Bag(builder=HtmlBodyBuilder())
        self.html.set_item("head", self.head)
        self.html.set_item("body", self.body)

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

    def _store_to_html(self, bag: Bag, tag: str, indent: int = 0) -> str:
        """Convert a Bag to HTML with a wrapper tag."""
        spaces = "  " * indent
        lines = [f"{spaces}<{tag}>"]
        for node in bag:
            lines.append(self._node_to_html(node, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)

    def to_html(self, filename: str | None = None, output_dir: str | None = None) -> str:
        """Generate complete HTML.

        Args:
            filename: If provided, save to output_dir/filename
            output_dir: Directory to save to (default: current directory)

        Returns:
            HTML string, or path if filename was provided
        """
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            self._store_to_html(self.head, "head", indent=0),
            self._store_to_html(self.body, "body", indent=0),
            "</html>",
        ]
        html_content = "\n".join(html_lines)

        if filename:
            output_dir = Path.cwd() if output_dir is None else Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / filename
            output_path.write_text(html_content)
            return str(output_path)

        return html_content

    def print_tree(self):
        """Print the tree structure for debugging."""
        from ..bag import Bag

        print("=" * 60)
        print("HEAD")
        print("=" * 60)
        for path, node in self.head.walk():
            indent_level = "  " * path.count(".")
            tag = node.tag or node.label
            value_str = ""
            node_value = node.get_value(static=True)
            if not isinstance(node_value, Bag) and node_value:
                val = str(node_value)
                value_str = f': "{val[:30]}..."' if len(val) > 30 else f': "{val}"'
            print(f"{indent_level}<{tag}>{value_str}")

        print("\n" + "=" * 60)
        print("BODY")
        print("=" * 60)
        for path, node in self.body.walk():
            indent_level = "  " * path.count(".")
            tag = node.tag or node.label
            node_value = node.get_value(static=True)
            value_str = (
                f': "{node_value}"' if not isinstance(node_value, Bag) and node_value else ""
            )
            attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith("_"))
            attrs_str = f" [{attrs}]" if attrs else ""
            print(f"{indent_level}<{tag}{attrs_str}>{value_str}")
