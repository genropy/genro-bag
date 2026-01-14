# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contact list HTML page using declarative builder pattern."""

from pathlib import Path

from genro_bag import Bag
from genro_bag.builders import HtmlBuilder


class ContactListPage:
    """A contact list page built with HtmlBuilder."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.page = Bag(builder=HtmlBuilder)
        self.prepare_head(self.page.head())
        self.build()

    def prepare_head(self, head):
        """Build the head section."""
        head.meta(charset="utf-8")
        head.title("Contacts")
        head.style(
            """
            body { font-family: sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; }
            th { background: #f5f5f5; }
        """
        )

    def prepare_contacts_table(self, block, contacts):
        """Build a table from contact data."""
        table = block.table()

        # Header
        thead = table.thead()
        tr = thead.tr()
        for header in ["Name", "Email", "Phone"]:
            tr.th(header)

        # Body
        tbody = table.tbody()
        for contact in contacts:
            tr = tbody.tr()
            tr.td(contact["name"])
            tr.td(contact["email"])
            tr.td(contact["phone"])

    def build(self):
        """Build the page body with contacts."""
        body = self.page.body()
        body.h1("Contact List")
        self.prepare_contacts_table(body, self.contacts)
        return self

    def to_html(self, destination=None):
        """Compile the page to HTML."""
        return self.page.builder.compile(destination=destination)


if __name__ == "__main__":
    contacts = [
        {"name": "John Smith", "email": "john@example.com", "phone": "555-1234"},
        {"name": "Jane Doe", "email": "jane@example.com", "phone": "555-5678"},
        {"name": "Bob Wilson", "email": "bob@example.com", "phone": "555-9012"},
    ]

    page = ContactListPage(contacts)

    destination = Path(__file__).with_suffix(".html")
    html = page.to_html(destination=destination)
    print(html)
