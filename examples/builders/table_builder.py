# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""TableBuilder - Example builder for HTML tables.

Demonstrates:
- Using @element decorator with sub_tags for structure validation
- Building HTML tables with thead, tbody, tr, th, td
- High-level wrapper class for convenient API
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element

if TYPE_CHECKING:
    from genro_bag import BagNode


class TableBuilder(BagBuilderBase):
    """Builder for HTML table elements using @element decorators.

    Defines valid HTML table structure:
    - table can contain: caption, colgroup, thead, tbody, tfoot, tr
    - thead/tbody/tfoot can contain: tr
    - tr can contain: th, td
    - th/td are leaf elements (contain text)

    Example:
        >>> store = Bag(builder=TableBuilder)
        >>> table = store.table()
        >>> thead = table.thead()
        >>> tr = thead.tr()
        >>> tr.th(value='Header 1')
        >>> tr.th(value='Header 2')
        >>>
        >>> tbody = table.tbody()
        >>> row = tbody.tr()
        >>> row.td(value='Cell 1')
        >>> row.td(value='Cell 2')
    """

    @element(sub_tags="caption[:1], colgroup, thead[:1], tbody, tfoot[:1], tr")
    def table(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a table element."""
        return self.child(target, tag, **attr)

    @element()
    def caption(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a caption element."""
        return self.child(target, tag, **attr)

    @element(sub_tags="col")
    def colgroup(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a colgroup element."""
        return self.child(target, tag, **attr)

    @element()
    def col(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a col element (void)."""
        return self.child(target, tag, **attr)

    @element(sub_tags="tr")
    def thead(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a thead element."""
        return self.child(target, tag, **attr)

    @element(sub_tags="tr")
    def tbody(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a tbody element."""
        return self.child(target, tag, **attr)

    @element(sub_tags="tr")
    def tfoot(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a tfoot element."""
        return self.child(target, tag, **attr)

    @element(sub_tags="th, td")
    def tr(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a tr (table row) element."""
        return self.child(target, tag, **attr)

    @element()
    def th(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a th (table header cell) element."""
        return self.child(target, tag, **attr)

    @element()
    def td(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a td (table data cell) element."""
        return self.child(target, tag, **attr)


class HtmlTable:
    """High-level API for creating HTML tables.

    Wraps TableBuilder with a convenient interface.

    Example:
        >>> t = HtmlTable()
        >>> t.add_header(['Name', 'Age', 'City'])
        >>> t.add_row(['Alice', 30, 'NYC'])
        >>> t.add_row(['Bob', 25, 'LA'])
        >>> print(t.to_html())
    """

    def __init__(self):
        self._store = Bag(builder=TableBuilder)
        self._table = self._store.table()
        # Save table node reference - don't rely on auto-generated labels
        self._table_node = self._store.get_node_at(-1)
        self._thead: Bag | None = None
        self._tbody: Bag | None = None

    @property
    def store(self) -> Bag:
        """Access underlying Bag."""
        return self._store

    @property
    def table(self) -> Bag:
        """Access table Bag."""
        return self._table

    def add_header(self, cells: list[str], **row_attrs) -> Bag:
        """Add header row.

        Args:
            cells: List of header cell values.
            **row_attrs: Attributes for the tr element.

        Returns:
            The thead Bag.
        """
        if self._thead is None:
            self._thead = self._table.thead()
        tr = self._thead.tr(**row_attrs)
        for cell in cells:
            tr.th(value=str(cell), scope="col")
        return self._thead

    def add_row(self, cells: list, **row_attrs) -> Bag:
        """Add data row.

        Args:
            cells: List of cell values.
            **row_attrs: Attributes for the tr element.

        Returns:
            The tr Bag.
        """
        if self._tbody is None:
            self._tbody = self._table.tbody()
        tr = self._tbody.tr(**row_attrs)
        for cell in cells:
            tr.td(value=str(cell))
        return tr

    def check(self) -> list[str]:
        """Validate table structure.

        Returns:
            List of error messages (empty if valid).
        """
        results = self._store.builder.check(self._table)
        errors = []
        for path, _node, reasons in results:
            for reason in reasons:
                errors.append(f"{path}: {reason}")
        return errors

    def to_html(self, indent: int = 0) -> str:
        """Generate HTML string."""
        return self._node_to_html(self._table_node, indent)

    def _node_to_html(self, node: BagNode, indent: int = 0) -> str:
        """Convert node to HTML."""
        tag = node.tag or node.label
        attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith("_"))
        attrs_str = f" {attrs}" if attrs else ""
        spaces = "  " * indent

        node_value = node.get_value(static=True)
        is_leaf = not isinstance(node_value, Bag)

        if is_leaf:
            if node_value == "":
                return f"{spaces}<{tag}{attrs_str} />"
            return f"{spaces}<{tag}{attrs_str}>{node_value}</{tag}>"

        lines = [f"{spaces}<{tag}{attrs_str}>"]
        for child in node_value:
            lines.append(self._node_to_html(child, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)


def demo():
    """Demo of TableBuilder."""
    print("=" * 60)
    print("TableBuilder Demo")
    print("=" * 60)

    # Create table using high-level API
    t = HtmlTable()
    t.add_header(["Product", "Price", "Quantity"])
    t.add_row(["Widget", "$10.00", "5"])
    t.add_row(["Gadget", "$25.00", "3"])

    print("\nGenerated HTML:")
    print(t.to_html())

    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)
    errors = t.check()
    if errors:
        print("Errors found:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Table structure is valid!")

    # Demo: Using builder directly
    print("\n" + "=" * 60)
    print("Direct Builder Usage")
    print("=" * 60)

    store = Bag(builder=TableBuilder)
    table = store.table()
    tbody = table.tbody()
    tr = tbody.tr()
    tr.td(value="Direct cell 1")
    tr.td(value="Direct cell 2")

    print("Created table with tbody > tr > td structure")
    errors = store.builder.check()
    if not errors:
        print("Structure is valid!")


if __name__ == "__main__":
    demo()
