# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for Bag.to_xml() and Bag.from_xml() methods."""

import datetime

from genro_bag import Bag


class TestBagToXml:
    """Tests for Bag.to_xml() method."""

    def test_simple_values(self):
        """Test serialization of simple scalar values."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42
        bag["price"] = 3.14

        xml = bag.to_xml()

        assert "<name>test</name>" in xml
        assert "<count>42</count>" in xml
        assert "<price>3.14</price>" in xml

    def test_nested_bag(self):
        """Test serialization of nested Bag structures."""
        bag = Bag()
        bag["person.name"] = "Alice"
        bag["person.age"] = 30

        xml = bag.to_xml()

        assert "<person>" in xml
        assert "<name>Alice</name>" in xml
        assert "<age>30</age>" in xml
        assert "</person>" in xml

    def test_empty_values(self):
        """Test serialization of empty/None values."""
        bag = Bag()
        bag["empty"] = ""
        bag["none"] = None

        xml = bag.to_xml()

        # Empty values produce self-closed tags by default
        assert "<empty/>" in xml
        assert "<none/>" in xml

    def test_special_characters_escaped(self):
        """Test that special XML characters are escaped."""
        bag = Bag()
        bag["text"] = '<script>alert("xss")</script>'
        bag["ampersand"] = "A & B"

        xml = bag.to_xml()

        assert "&lt;script&gt;" in xml
        assert "&amp;" in xml

    def test_attributes(self):
        """Test serialization with node attributes."""
        bag = Bag()
        bag.set_item("item", "value", _attributes={"id": "123", "active": True})

        xml = bag.to_xml()

        assert 'id="123"' in xml
        assert 'active="True"' in xml

    def test_doc_header_true(self):
        """Test XML declaration with doc_header=True."""
        bag = Bag()
        bag["test"] = "value"

        xml = bag.to_xml(doc_header=True)

        assert xml.startswith("<?xml version='1.0' encoding='UTF-8'?>")

    def test_doc_header_custom(self):
        """Test custom XML declaration."""
        bag = Bag()
        bag["test"] = "value"

        custom_header = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        xml = bag.to_xml(doc_header=custom_header)

        assert xml.startswith(custom_header)

    def test_pretty_print(self):
        """Test pretty-printed output with indentation."""
        bag = Bag()
        bag["root.child"] = "value"

        xml = bag.to_xml(pretty=True)

        # Pretty print adds indentation and newlines
        assert "\n" in xml

    def test_self_closed_tags_list(self):
        """Test self_closed_tags parameter."""
        bag = Bag()
        bag["br"] = ""
        bag["div"] = ""

        # Only 'br' should be self-closed
        xml = bag.to_xml(self_closed_tags=["br"])

        assert "<br/>" in xml
        assert "<div></div>" in xml

    def test_invalid_tag_sanitization(self):
        """Test that invalid XML tag names are sanitized."""
        bag = Bag()
        bag["123numeric"] = "value"
        bag["with space"] = "value"

        xml = bag.to_xml()

        # Numeric start gets underscore prefix
        assert "<_123numeric" in xml
        # Space replaced with underscore
        assert "<with_space" in xml
        # Original tag stored in _tag attribute
        assert "_tag=" in xml


class TestBagFromXml:
    """Tests for Bag.from_xml() method."""

    def test_simple_xml(self):
        """Test parsing simple XML elements."""
        xml = "<root><name>test</name><count>42</count></root>"

        bag = Bag.from_xml(xml)

        assert bag["root.name"] == "test"
        assert bag["root.count"] == "42"  # Plain XML values are strings

    def test_nested_structure(self):
        """Test parsing nested XML structure."""
        xml = """
        <config>
            <database>
                <host>localhost</host>
                <port>5432</port>
            </database>
        </config>
        """

        bag = Bag.from_xml(xml)

        assert bag["config.database.host"] == "localhost"
        assert bag["config.database.port"] == "5432"

    def test_attributes_as_node_attrs(self):
        """Test that XML attributes become node attributes.

        Note: The parser uses TYTX decoding which auto-converts numeric strings
        and boolean strings to their typed values.
        """
        xml = '<root><item id="123" active="true">value</item></root>'

        bag = Bag.from_xml(xml)

        assert bag["root.item"] == "value"
        node = bag.get_node("root.item")
        # TYTX auto-decodes "123" as integer and "true" as boolean
        assert node.attr["id"] == 123
        assert node.attr["active"] is True

    def test_empty_element(self):
        """Test parsing empty elements."""
        xml = "<root><empty/></root>"

        bag = Bag.from_xml(xml)

        # Empty element value depends on implementation
        assert "empty" in bag["root"].keys()

    def test_empty_factory(self):
        """Test empty parameter provides factory for empty elements."""
        xml = "<root><empty/></root>"

        bag = Bag.from_xml(xml, empty=lambda: "default")

        assert bag["root.empty"] == "default"

    def test_duplicate_labels(self):
        """Test handling of duplicate element names."""
        xml = "<root><item>first</item><item>second</item><item>third</item></root>"

        bag = Bag.from_xml(xml)

        assert bag["root.item"] == "first"
        assert bag["root.item_1"] == "second"
        assert bag["root.item_2"] == "third"

    def test_mixed_content(self):
        """Test elements with both text and child elements."""
        xml = "<root><parent>text<child>nested</child></parent></root>"

        bag = Bag.from_xml(xml)

        # Text content stored in _ key
        assert bag["root.parent._"] == "text"
        assert bag["root.parent.child"] == "nested"


class TestBagFromXmlLegacyFormat:
    """Tests for parsing legacy GenRoBag XML format."""

    def test_genrobag_wrapper_removed(self):
        """Test that GenRoBag wrapper element is removed."""
        xml = "<GenRoBag><name>test</name></GenRoBag>"

        bag = Bag.from_xml(xml)

        # GenRoBag wrapper is stripped
        assert bag["name"] == "test"
        assert "GenRoBag" not in bag.keys()

    def test_type_T_integer(self):
        """Test _T="L" for integer type."""
        xml = '<GenRoBag><count _T="L">42</count></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["count"] == 42
        assert isinstance(bag["count"], int)

    def test_type_T_decimal(self):
        """Test _T="N" for Decimal type."""
        from decimal import Decimal

        xml = '<GenRoBag><price _T="N">3.14</price></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["price"] == Decimal("3.14")
        assert isinstance(bag["price"], Decimal)

    def test_type_T_boolean(self):
        """Test _T="B" for boolean type."""
        xml = '<GenRoBag><active _T="B">true</active><disabled _T="B">false</disabled></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["active"] is True
        assert bag["disabled"] is False

    def test_type_T_date(self):
        """Test _T="D" for date type."""
        xml = '<GenRoBag><created _T="D">2025-01-05</created></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["created"] == datetime.date(2025, 1, 5)

    def test_type_T_datetime(self):
        """Test _T="DH" for datetime type."""
        xml = '<GenRoBag><timestamp _T="DH">2025-01-05T10:30:00</timestamp></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["timestamp"] == datetime.datetime(2025, 1, 5, 10, 30, 0)

    def test_type_T_time(self):
        """Test _T="H" for time type."""
        xml = '<GenRoBag><start_time _T="H">14:30:00</start_time></GenRoBag>'

        bag = Bag.from_xml(xml)

        assert bag["start_time"] == datetime.time(14, 30, 0)

    def test_tytx_attribute_format(self):
        """Test ::TYPE suffix in attribute values."""
        from decimal import Decimal

        xml = '<GenRoBag><item count="42::L" price="3.14::N">value</item></GenRoBag>'

        bag = Bag.from_xml(xml)

        node = bag.get_node("item")
        assert node.attr["count"] == 42
        assert node.attr["price"] == Decimal("3.14")

    def test_nested_elements_in_genrobag(self):
        """Test nested elements in GenRoBag format.

        Note: Array types (A*) are not supported. Nested elements
        are parsed as regular Bag children.
        """
        xml = """<GenRoBag><numbers>
            <n>1</n><n>2</n><n>3</n>
        </numbers></GenRoBag>"""

        bag = Bag.from_xml(xml)

        # Nested elements become Bag children with duplicate handling
        assert bag["numbers.n"] == "1"
        assert bag["numbers.n_1"] == "2"
        assert bag["numbers.n_2"] == "3"

    def test_empty_with_type(self):
        """Test empty element with type.

        Note: Empty string with integer type causes ValueError in TYTX decoder.
        This test verifies that an empty element without content stays empty.
        """
        xml = '<GenRoBag><empty _T="T"></empty></GenRoBag>'

        bag = Bag.from_xml(xml)

        # Empty text type returns empty string
        assert bag["empty"] == ""


class TestBagXmlRoundTrip:
    """Tests for to_xml/from_xml round-trip consistency."""

    def test_simple_roundtrip(self):
        """Test that simple values survive round-trip."""
        original = Bag()
        original["name"] = "test"
        original["description"] = "A test bag"

        xml = original.to_xml()
        restored = Bag.from_xml(f"<root>{xml}</root>")

        assert restored["root.name"] == "test"
        assert restored["root.description"] == "A test bag"

    def test_nested_roundtrip(self):
        """Test that nested structure survives round-trip."""
        original = Bag()
        original["config.db.host"] = "localhost"
        original["config.db.port"] = "5432"
        original["config.app.name"] = "myapp"

        xml = original.to_xml()
        restored = Bag.from_xml(f"<root>{xml}</root>")

        assert restored["root.config.db.host"] == "localhost"
        assert restored["root.config.db.port"] == "5432"
        assert restored["root.config.app.name"] == "myapp"

    def test_attributes_roundtrip(self):
        """Test that attributes survive round-trip.

        Note: TYTX auto-decodes numeric strings to integers.
        """
        original = Bag()
        original.set_item("item", "value", _attributes={"id": "123"})

        xml = original.to_xml()
        restored = Bag.from_xml(f"<root>{xml}</root>")

        node = restored.get_node("root.item")
        # TYTX decodes "123" as integer
        assert node.attr["id"] == 123

    def test_special_chars_roundtrip(self):
        """Test that special characters survive round-trip."""
        original = Bag()
        original["text"] = "Hello <world> & friends"

        xml = original.to_xml()
        restored = Bag.from_xml(f"<root>{xml}</root>")

        assert restored["root.text"] == "Hello <world> & friends"
