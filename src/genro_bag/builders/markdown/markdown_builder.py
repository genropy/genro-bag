# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""MarkdownBuilder - Markdown document builder.

Provides elements for building Markdown documents programmatically.
The compile() method walks the Bag and renders each node using _render_value()
which applies compile_template from the schema.

Example:
    Creating a Markdown document::

        from genro_bag import Bag
        from genro_bag.builders import MarkdownBuilder

        doc = Bag(builder=MarkdownBuilder)
        doc.h1("My Document")
        doc.p("This is a paragraph.")

        # Create a table
        table = doc.table()
        header = table.tr()
        header.th("Name")
        header.th("Value")
        row = table.tr()
        row.td("foo")
        row.td("bar")

        # Code block
        doc.code("print('hello')", lang="python")

        # Generate markdown
        md = doc.builder.compile()
"""

from __future__ import annotations

from pathlib import Path

from ...builder import BagBuilderBase, element


class MarkdownBuilder(BagBuilderBase):
    """Builder for Markdown documents.

    Each element uses compile_template to define its markdown structure.
    The compile() method renders nodes using _render_value() from base class.
    """

    # -------------------------------------------------------------------------
    # Headings
    # -------------------------------------------------------------------------

    @element(sub_tags="", compile_template="# {node_value}")
    def h1(self, node_value: str):
        """Level 1 heading."""
        ...

    @element(sub_tags="", compile_template="## {node_value}")
    def h2(self, node_value: str):
        """Level 2 heading."""
        ...

    @element(sub_tags="", compile_template="### {node_value}")
    def h3(self, node_value: str):
        """Level 3 heading."""
        ...

    @element(sub_tags="", compile_template="#### {node_value}")
    def h4(self, node_value: str):
        """Level 4 heading."""
        ...

    @element(sub_tags="", compile_template="##### {node_value}")
    def h5(self, node_value: str):
        """Level 5 heading."""
        ...

    @element(sub_tags="", compile_template="###### {node_value}")
    def h6(self, node_value: str):
        """Level 6 heading."""
        ...

    # -------------------------------------------------------------------------
    # Block elements
    # -------------------------------------------------------------------------

    @element(sub_tags="")
    def p(self, node_value: str):
        """Paragraph."""
        ...

    @element(sub_tags="", compile_template="```{lang}\n{node_value}\n```")
    def code(self, node_value: str, lang: str = ""):
        """Code block with optional language."""
        ...

    @element(sub_tags="", compile_callback="_compile_blockquote")
    def blockquote(self, node_value: str):
        """Blockquote."""
        ...

    @element(sub_tags="", compile_template="---")
    def hr(self):
        """Horizontal rule."""
        ...

    # -------------------------------------------------------------------------
    # Table elements
    # -------------------------------------------------------------------------

    @element(sub_tags="tr", compile_callback="_compile_table")
    def table(self):
        """Table container."""
        ...

    @element(sub_tags="th,td")
    def tr(self):
        """Table row."""
        ...

    @element(sub_tags="")
    def th(self, node_value: str):
        """Table header cell."""
        ...

    @element(sub_tags="")
    def td(self, node_value: str):
        """Table data cell."""
        ...

    # -------------------------------------------------------------------------
    # List elements
    # -------------------------------------------------------------------------

    @element(sub_tags="li", compile_callback="_compile_ul")
    def ul(self):
        """Unordered list."""
        ...

    @element(sub_tags="li", compile_callback="_compile_ol")
    def ol(self):
        """Ordered list."""
        ...

    @element(sub_tags="")
    def li(self, node_value: str, idx: str | int | None = None):
        """List item."""
        ...

    # -------------------------------------------------------------------------
    # Inline elements
    # -------------------------------------------------------------------------

    @element(sub_tags="", compile_template="[{node_value}]({href})")
    def link(self, node_value: str, href: str):
        """Hyperlink."""
        ...

    @element(sub_tags="", compile_template="![{alt}]({src})")
    def img(self, src: str, alt: str = ""):
        """Image."""
        ...

    @element(sub_tags="", compile_template="**{node_value}**")
    def bold(self, node_value: str):
        """Bold text."""
        ...

    @element(sub_tags="", compile_template="*{node_value}*")
    def italic(self, node_value: str):
        """Italic text."""
        ...

    @element(sub_tags="", compile_template="`{node_value}`")
    def inlinecode(self, node_value: str):
        """Inline code."""
        ...

    @element(sub_tags="")
    def text(self, node_value: str):
        """Plain text."""
        ...

    # -------------------------------------------------------------------------
    # Compile to Markdown
    # -------------------------------------------------------------------------

    def compile(self, destination: str | Path | None = None) -> str:
        """Compile the bag to Markdown.

        Args:
            destination: If provided, write Markdown to this file path.

        Returns:
            Markdown string representation.
        """
        lines: list[str] = []
        for node in self.bag:
            rendered = self._render_value(node)
            if rendered:
                lines.append(rendered)
        md = "\n\n".join(lines)

        if destination:
            Path(destination).write_text(md)

        return md

    # -------------------------------------------------------------------------
    # Compile callbacks (modify ctx in place)
    # -------------------------------------------------------------------------

    def _compile_blockquote(self, ctx: dict) -> None:
        """Blockquote: prefix each line with '> '."""
        value = ctx["node_value"]
        ctx["node_value"] = "\n".join(f"> {line}" for line in value.split("\n"))

    def _compile_table(self, ctx: dict) -> None:
        """Table: render rows as markdown table."""
        from ...bag import Bag

        node = ctx["_node"]
        lines: list[str] = []
        rows = node.value if isinstance(node.value, Bag) else []
        is_first = True

        for row_node in rows:
            if row_node.tag != "tr":
                continue
            cells = row_node.value if isinstance(row_node.value, Bag) else []
            cell_texts = [str(cell.get_value(static=True) or "") for cell in cells]

            lines.append("| " + " | ".join(cell_texts) + " |")

            if is_first:
                lines.append("| " + " | ".join("---" for _ in cell_texts) + " |")
                is_first = False

        ctx["node_value"] = "\n".join(lines)

    def _compile_ul(self, ctx: dict) -> None:
        """Unordered list: prefix items with '- '."""
        self._compile_list(ctx, "-")

    def _compile_ol(self, ctx: dict) -> None:
        """Ordered list: prefix items with numbers."""
        self._compile_list(ctx, "ol")

    def _compile_list(self, ctx: dict, prefix: str) -> None:
        """List: render items with prefix."""
        from ...bag import Bag

        node = ctx["_node"]
        lines: list[str] = []
        items = node.value if isinstance(node.value, Bag) else []

        for i, item_node in enumerate(items, start=1):
            text = str(item_node.get_value(static=True) or "")
            # Use idx from node if provided, otherwise use i
            node_idx = item_node.attr.get("idx")
            if node_idx is not None:
                item_prefix = str(node_idx)
            else:
                item_prefix = f"{i}." if prefix == "ol" else prefix
            lines.append(f"{item_prefix} {text}")

        ctx["node_value"] = "\n".join(lines)
