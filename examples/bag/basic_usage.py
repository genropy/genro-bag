# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Basic Bag usage examples.

Demonstrates fundamental Bag operations:
- Creating Bags and adding items
- Accessing values with dot notation and paths
- Iterating over nodes
- XML and JSON serialization
"""

from __future__ import annotations

from genro_bag import Bag


def demo_basic_operations():
    """Basic Bag creation and manipulation."""
    print("=" * 60)
    print("Basic Operations")
    print("=" * 60)

    # Create empty Bag
    bag = Bag()

    # Add items using set_item
    bag.set_item("name", "John Doe")
    bag.set_item("age", 30)
    bag.set_item("active", True)

    # Add item with attributes
    bag.set_item("email", "john@example.com", _attributes={"verified": True})

    # Access values
    print(f"Name: {bag['name']}")
    print(f"Age: {bag['age']}")
    print(f"Email verified: {bag.get_node('email').attr['verified']}")

    return bag


def demo_nested_structure():
    """Creating nested Bag structures."""
    print("\n" + "=" * 60)
    print("Nested Structures")
    print("=" * 60)

    # Create nested structure
    root = Bag()

    # Create nested Bag for address
    address = Bag()
    address.set_item("street", "Via Roma 123")
    address.set_item("city", "Roma")
    address.set_item("zip", "00100")
    address.set_item("country", "IT")

    root.set_item("person", Bag())
    root["person"].set_item("name", "Mario Rossi")
    root["person"].set_item("address", address)

    # Access nested values with path
    print(f"City: {root['person.address.city']}")
    print(f"Full path access: {root['person.name']}")

    return root


def demo_iteration():
    """Iterating over Bag nodes."""
    print("\n" + "=" * 60)
    print("Iteration")
    print("=" * 60)

    bag = Bag()
    bag.set_item("a", 1)
    bag.set_item("b", 2)
    bag.set_item("c", 3)

    # Iterate over nodes
    print("Iterating over nodes:")
    for node in bag:
        # Use get_value(static=True) to avoid triggering resolvers in generic code
        print(f"  {node.label} = {node.get_value(static=True)}")

    # Using walk() for nested structures
    nested = Bag()
    nested.set_item("level1", Bag())
    nested["level1"].set_item("level2", Bag())
    nested["level1.level2"].set_item("value", "deep")

    print("\nWalking nested structure:")
    for path, node in nested.walk():
        # Use get_value(static=True) to show cached value without side-effects
        value = node.get_value(static=True)
        print(f"  {path}: {value if not node.is_branch else '(Bag)'}")


def demo_serialization():
    """XML and JSON serialization."""
    print("\n" + "=" * 60)
    print("Serialization")
    print("=" * 60)

    bag = Bag()
    bag.set_item("product", Bag())
    bag["product"].set_item("name", "Widget")
    bag["product"].set_item("price", 29.99)
    bag["product"].set_item("stock", 100)

    # To XML
    xml = bag.to_xml(pretty=True)
    print("XML output:")
    print(xml)

    # To JSON
    json_str = bag.to_json()
    print("\nJSON output:")
    print(json_str)


def demo_xml_parsing():
    """Parsing XML into Bag."""
    print("\n" + "=" * 60)
    print("XML Parsing")
    print("=" * 60)

    xml_content = """
    <catalog>
        <book id="1">
            <title>Python Cookbook</title>
            <author>David Beazley</author>
            <price>49.99</price>
        </book>
        <book id="2">
            <title>Fluent Python</title>
            <author>Luciano Ramalho</author>
            <price>59.99</price>
        </book>
    </catalog>
    """

    bag = Bag.from_xml(xml_content)

    print("Parsed structure:")
    for path, node in bag.walk():
        indent = "  " * path.count(".")
        if node.is_branch:
            attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items())
            print(f"{indent}{node.label} {attrs}".strip())
        else:
            # Use get_value(static=True) to avoid triggering resolvers
            print(f"{indent}{node.label}: {node.get_value(static=True)}")


def demo():
    """Run all demos."""
    demo_basic_operations()
    demo_nested_structure()
    demo_iteration()
    demo_serialization()
    demo_xml_parsing()


if __name__ == "__main__":
    demo()
