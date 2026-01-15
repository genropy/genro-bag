# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Example: Shopping list and contacts table using HtmlBuilder."""

from pathlib import Path

from genro_bag import Bag
from genro_bag.builders import HtmlBuilder


def build_page():
    """Build the page content using HtmlBuilder."""
    bag = Bag(builder=HtmlBuilder)

    # Build HTML structure
    html = bag.html()

    # Head section
    head = html.head()
    head.meta(charset="utf-8")
    head.title(value="HTML Page Example")
    head.style(
        value="""
body { font-family: sans-serif; margin: 20px; }
#header { background: #f0f0f0; padding: 10px; }
#content { margin: 20px 0; }
#footer { background: #f0f0f0; padding: 10px; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #f5f5f5; }
ul { margin: 10px 0; }
    """
    )

    # Body section
    body = html.body()
    page_div = body.div(id="page")

    # Header
    header = page_div.div(id="header")
    header.h1(value="Welcome")
    header.h2(value="Page subtitle")

    # Content
    content = page_div.div(id="content")

    # Shopping list
    content.h3(value="Shopping List")
    lista = content.ul()
    lista.li(value="Bread")
    lista.li(value="Milk")
    lista.li(value="Eggs")

    # Contacts table
    content.h3(value="Contacts")
    table = content.table()

    # Table header
    thead = table.thead()
    tr = thead.tr()
    tr.th(value="Name")
    tr.th(value="Email")
    tr.th(value="Phone")

    # Table body
    tbody = table.tbody()
    for name, email, phone in [
        ("John Smith", "john@example.com", "555-1234567"),
        ("Jane Doe", "jane@example.com", "555-7654321"),
    ]:
        row = tbody.tr()
        row.td(value=name)
        row.td(value=email)
        row.td(value=phone)

    # Footer
    footer = page_div.div(id="footer")
    footer.span(value="© 2025 - All rights reserved")

    return bag


def demo():
    """Demo of HtmlBuilder."""
    print("=" * 60)
    print("HtmlBuilder Demo")
    print("=" * 60)

    bag = build_page()

    # Generate HTML
    print("\n" + "=" * 60)
    print("Generated HTML")
    print("=" * 60)
    html = bag.builder.compile()
    print(html)

    # Save to file
    output_dir = Path(__file__).parent
    output_path = output_dir / "example.html"
    bag.builder.compile(destination=output_path)
    print(f"\nHTML saved to: {output_path}")


if __name__ == "__main__":
    demo()
