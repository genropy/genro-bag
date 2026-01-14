# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""TableBuilder - Example builder using JSON schema with attribute validation.

Demonstrates:
- Loading schema from JSON file
- Pure Python attribute validation from attrs spec
- =ref references for content categories
- Structure and attribute validation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from genro_bag import Bag, BagBuilderBase

if TYPE_CHECKING:
    from genro_bag import BagNode


# Load schema from JSON
SCHEMA_PATH = Path(__file__).parent / "html_tables.json"


class TableBuilder(BagBuilderBase):
    """Builder for HTML table elements using JSON schema.

    Schema loaded from html_tables.json (in same directory) provides:
    - Element children constraints (table → thead, tbody, tr, etc.)
    - Attribute validation via pure Python validation
    - Reference resolution for content categories (=flow)

    Example:
        >>> store = Bag(builder=TableBuilder())
        >>> table = store.table()
        >>> thead = table.thead()
        >>> tr = thead.tr()
        >>> tr.th(value='Header 1', scope='col')
        >>> tr.th(value='Header 2', scope='col')
        >>>
        >>> tbody = table.tbody()
        >>> row = tbody.tr()
        >>> row.td(value='Cell 1', colspan=2)
        >>> row.td(value='Cell 2')
    """

    def __init__(self):
        """Initialize builder with schema from JSON."""
        super().__init__()
        self._load_schema()

    def _load_schema(self):
        """Load schema from JSON file."""
        if SCHEMA_PATH.exists():
            data = json.loads(SCHEMA_PATH.read_text())
            # Set _schema from elements
            self._schema = data.get("elements", {})
            # Store refs for dynamic _ref_* resolution
            self._refs = data.get("refs", {})
        else:
            # Fallback inline schema
            self._schema = {
                "table": {"children": "thead, tbody, tfoot, tr"},
                "thead": {"children": "tr"},
                "tbody": {"children": "tr"},
                "tfoot": {"children": "tr"},
                "tr": {"children": "th, td"},
                "th": {"leaf": False},
                "td": {"leaf": False},
            }
            self._refs = {}

    def __getattr__(self, name: str):
        """Handle _ref_* lookups for dynamic references."""
        if name.startswith("_ref_"):
            ref_name = name[5:]  # '_ref_flow' -> 'flow'
            if ref_name in self._refs:
                return self._refs[ref_name]
            raise AttributeError(f"Reference '{ref_name}' not found in schema refs")

        # Delegate to parent for _schema lookup
        return super().__getattr__(name)


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
        self._store = Bag(builder=TableBuilder())
        self._table = self._store.table()
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
        """Validate table structure."""
        return self._store.builder.check(self._table, parent_tag="table")

    def to_html(self, indent: int = 0) -> str:
        """Generate HTML string."""
        # Get the table node (not its value)
        table_node = self._store.get_node("table_0")
        return self._node_to_html(table_node, indent)

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
    """Demo of TableBuilder with validation."""
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

    # Demo attribute validation
    print("\n" + "=" * 60)
    print("Attribute Validation Demo")
    print("=" * 60)

    store = Bag(builder=TableBuilder())
    table = store.table()
    tbody = table.tbody()
    tr = tbody.tr()

    # Valid attributes
    print("\nCreating td with colspan=2 (valid)...")
    tr.td(value="Merged cell", colspan=2)
    print("  Success!")

    # Test scope enum on th
    print("\nCreating th with scope='col' (valid enum)...")
    tr2 = tbody.tr()
    tr2.th(value="Header", scope="col")
    print("  Success!")

    # Invalid attribute
    print("\nTrying td with colspan=0 (invalid, min=1)...")
    try:
        tr.td(value="Bad cell", colspan=0)
        print("  Created (validation not triggered)")
    except Exception as e:
        print(f"  Validation error: {e}")

    print("\nTrying th with scope='invalid' (invalid enum)...")
    try:
        tr2.th(value="Bad header", scope="invalid")
        print("  Created (validation not triggered)")
    except Exception as e:
        print(f"  Validation error: {e}")


if __name__ == "__main__":
    demo()
