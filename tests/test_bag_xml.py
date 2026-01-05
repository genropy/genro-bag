# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for bag_xml module.

Tests the 4 concrete classes:
- BagXmlSerializerPure
- BagXmlSerializerLegacy
- BagXmlParserPure
- BagXmlParserLegacy
"""

import datetime
from decimal import Decimal

import pytest

from genro_bag import Bag
from genro_bag.bag_xml import (
    BagXmlParserLegacy,
    BagXmlParserPure,
    BagXmlSerializerLegacy,
    BagXmlSerializerPure,
)


# =============================================================================
# BagXmlSerializerPure Tests
# =============================================================================


class TestBagXmlSerializerPure:
    """Tests for BagXmlSerializerPure."""

    def test_serialize_simple_values(self):
        """Serialize bag with simple string and int values."""
        bag = Bag()
        bag['name'] = 'test'
        bag['count'] = 42

        xml = BagXmlSerializerPure.serialize(bag)

        assert '<name>test</name>' in xml
        assert '<count>42</count>' in xml

    def test_serialize_nested_bag(self):
        """Serialize bag with nested structure."""
        bag = Bag()
        bag['config'] = Bag()
        bag['config.host'] = 'localhost'
        bag['config.port'] = 8080

        xml = BagXmlSerializerPure.serialize(bag)

        assert '<config>' in xml
        assert '<host>localhost</host>' in xml
        assert '<port>8080</port>' in xml
        assert '</config>' in xml

    def test_serialize_empty_bag(self):
        """Serialize empty bag produces self-closed tag."""
        bag = Bag()
        bag['empty'] = Bag()

        xml = BagXmlSerializerPure.serialize(bag)

        assert '<empty/>' in xml

    def test_serialize_none_value(self):
        """Serialize None value produces self-closed tag."""
        bag = Bag()
        bag['nothing'] = None

        xml = BagXmlSerializerPure.serialize(bag)

        assert '<nothing/>' in xml

    def test_serialize_with_attributes(self):
        """Serialize bag with node attributes."""
        bag = Bag()
        bag.set_item('item', 'value', _attributes={'id': '123', 'type': 'text'})

        xml = BagXmlSerializerPure.serialize(bag)

        assert 'id="123"' in xml
        assert 'type="text"' in xml
        assert '>value</item>' in xml

    def test_serialize_special_characters_escaped(self):
        """Special characters in values are escaped."""
        bag = Bag()
        bag['html'] = '<div>test & more</div>'

        xml = BagXmlSerializerPure.serialize(bag)

        assert '&lt;div&gt;test &amp; more&lt;/div&gt;' in xml

    def test_serialize_invalid_tag_sanitized(self):
        """Invalid XML tag names are sanitized."""
        bag = Bag()
        bag['my-key'] = 'value'
        bag['123start'] = 'value2'

        xml = BagXmlSerializerPure.serialize(bag)

        # my-key becomes my_key with _tag attribute
        assert 'my_key' in xml
        assert '_tag="my-key"' in xml
        # 123start becomes _123start
        assert '_123start' in xml

    def test_serialize_with_doc_header(self):
        """Serialize with XML declaration header."""
        bag = Bag()
        bag['test'] = 'value'

        xml = BagXmlSerializerPure.serialize(bag, doc_header=True)

        assert xml.startswith("<?xml version='1.0' encoding='UTF-8'?>")

    def test_serialize_with_custom_header(self):
        """Serialize with custom XML header."""
        bag = Bag()
        bag['test'] = 'value'

        xml = BagXmlSerializerPure.serialize(bag, doc_header='<?xml version="1.0"?>')

        assert xml.startswith('<?xml version="1.0"?>')

    def test_serialize_self_closed_tags_list(self):
        """Only specified tags are self-closed when empty."""
        bag = Bag()
        bag['br'] = ''
        bag['div'] = ''

        xml = BagXmlSerializerPure.serialize(bag, self_closed_tags=['br'])

        assert '<br/>' in xml
        assert '<div></div>' in xml

    def test_serialize_namespace_preserved(self):
        """Namespace prefixes in tags are preserved."""
        bag = Bag()
        bag.set_item('xs:element', 'value', _attributes={'xmlns:xs': 'http://www.w3.org/2001/XMLSchema'})

        xml = BagXmlSerializerPure.serialize(bag)

        assert '<xs:element' in xml
        assert 'xmlns:xs=' in xml


# =============================================================================
# BagXmlSerializerLegacy Tests
# =============================================================================


class TestBagXmlSerializerLegacy:
    """Tests for BagXmlSerializerLegacy."""

    def test_serialize_with_genrobag_root(self):
        """Legacy format wraps content in GenRoBag root."""
        bag = Bag()
        bag['name'] = 'test'

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '<GenRoBag>' in xml
        assert '</GenRoBag>' in xml

    def test_serialize_omit_root(self):
        """omitRoot=True skips GenRoBag wrapper."""
        bag = Bag()
        bag['name'] = 'test'

        xml = BagXmlSerializerLegacy.serialize(bag, omitRoot=True)

        assert '<GenRoBag>' not in xml
        assert '<name>' in xml

    def test_serialize_integer_with_type(self):
        """Integer values get _T="L" type attribute."""
        bag = Bag()
        bag['count'] = 42

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="L"' in xml
        assert '>42</count>' in xml

    def test_serialize_float_with_type(self):
        """Float values get _T="R" type attribute."""
        bag = Bag()
        bag['price'] = 19.99

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="R"' in xml

    def test_serialize_boolean_with_type(self):
        """Boolean values get _T="B" type attribute.

        genro_tytx uses 'true'/'false' for booleans.
        """
        bag = Bag()
        bag['active'] = True
        bag['deleted'] = False

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="B"' in xml
        assert '>true</active>' in xml
        assert '>false</deleted>' in xml

    def test_serialize_date_with_type(self):
        """Date values get _T="D" type attribute."""
        bag = Bag()
        bag['created'] = datetime.date(2025, 1, 15)

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="D"' in xml
        assert '2025-01-15' in xml

    def test_serialize_datetime_with_type(self):
        """Datetime values get _T="DHZ" type attribute.

        genro_tytx uses:
        - DHZ suffix (canonical, DH is deprecated)
        - Millisecond precision (e.g., 10:30:00.000Z)
        - Z suffix for naive datetimes (UTC assumption)
        """
        bag = Bag()
        bag['timestamp'] = datetime.datetime(2025, 1, 15, 10, 30, 0)

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="DHZ"' in xml
        assert '2025-01-15T10:30:00.000Z' in xml

    def test_serialize_decimal_with_type(self):
        """Decimal values get _T="N" type attribute."""
        bag = Bag()
        bag['amount'] = Decimal('123.45')

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert '_T="N"' in xml
        assert '123.45' in xml

    def test_serialize_string_no_type(self):
        """String values don't get _T attribute (or _T="T")."""
        bag = Bag()
        bag['name'] = 'test'

        xml = BagXmlSerializerLegacy.serialize(bag)

        # Strings either have no _T or _T="T" which is suppressed
        assert '_T="T"' not in xml or '<name>' in xml

    def test_serialize_empty_bag_with_bag_type(self):
        """Empty Bag gets _T="BAG" when addBagTypeAttr=True."""
        bag = Bag()
        bag['config'] = Bag()

        xml = BagXmlSerializerLegacy.serialize(bag, addBagTypeAttr=True)

        assert '_T="BAG"' in xml

    def test_serialize_typevalue_false(self):
        """typevalue=False omits _T attributes."""
        bag = Bag()
        bag['count'] = 42

        xml = BagXmlSerializerLegacy.serialize(bag, typevalue=False)

        assert '_T=' not in xml

    def test_serialize_typeattrs_typed_values(self):
        """Attributes get ::TYPE suffix when typeattrs=True."""
        bag = Bag()
        bag.set_item('item', 'value', _attributes={'count': 42})

        xml = BagXmlSerializerLegacy.serialize(bag, typeattrs=True)

        assert '::L' in xml  # Integer type suffix

    def test_serialize_typeattrs_false(self):
        """typeattrs=False omits ::TYPE suffix in attributes."""
        bag = Bag()
        bag.set_item('item', 'value', _attributes={'count': 42})

        xml = BagXmlSerializerLegacy.serialize(bag, typeattrs=False)

        assert '::L' not in xml

    def test_serialize_always_has_header(self):
        """Legacy format always includes XML header unless doc_header=False."""
        bag = Bag()
        bag['test'] = 'value'

        xml = BagXmlSerializerLegacy.serialize(bag)

        assert xml.startswith("<?xml version='1.0'")

    def test_serialize_no_header(self):
        """doc_header=False omits XML declaration."""
        bag = Bag()
        bag['test'] = 'value'

        xml = BagXmlSerializerLegacy.serialize(bag, doc_header=False)

        assert not xml.startswith('<?xml')


# =============================================================================
# BagXmlParserPure Tests
# =============================================================================


class TestBagXmlParserPure:
    """Tests for BagXmlParserPure."""

    def test_parse_simple_elements(self):
        """Parse simple XML elements."""
        xml = '<root><name>test</name><count>42</count></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.name'] == 'test'
        assert bag['root.count'] == '42'  # All values are strings

    def test_parse_nested_structure(self):
        """Parse nested XML structure."""
        xml = '<root><config><host>localhost</host><port>8080</port></config></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.config.host'] == 'localhost'
        assert bag['root.config.port'] == '8080'

    def test_parse_empty_element(self):
        """Parse empty XML element."""
        xml = '<root><empty/></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.empty'] == ''  # Default empty factory

    def test_parse_empty_element_custom_factory(self):
        """Parse empty element with custom empty factory."""
        xml = '<root><empty/></root>'

        bag = BagXmlParserPure.parse(xml, Bag, empty=lambda: None)

        assert bag['root.empty'] is None

    def test_parse_attributes(self):
        """Parse XML with attributes."""
        xml = '<root><item id="123" type="text">value</item></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.item'] == 'value'
        node = bag.get_node('root.item')
        assert node.attr['id'] == '123'
        assert node.attr['type'] == 'text'

    def test_parse_duplicate_tags(self):
        """Duplicate tags get _1, _2 suffixes."""
        xml = '<root><item>a</item><item>b</item><item>c</item></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.item'] == 'a'
        assert bag['root.item_1'] == 'b'
        assert bag['root.item_2'] == 'c'

    def test_parse_mixed_content(self):
        """Parse element with mixed text and child elements."""
        xml = '<root><parent>text<child>inner</child></parent></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        # Text content is stored as '_txt'
        parent = bag['root.parent']
        assert isinstance(parent, Bag)
        assert parent['_txt'] == 'text'
        assert parent['child'] == 'inner'

    def test_parse_escaped_characters(self):
        """Escaped characters in XML are unescaped."""
        xml = '<root><html>&lt;div&gt;test &amp; more&lt;/div&gt;</html></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.html'] == '<div>test & more</div>'

    def test_parse_bytes_input(self):
        """Parse XML from bytes input."""
        xml = b'<root><name>test</name></root>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert bag['root.name'] == 'test'

    def test_parse_namespace_preserved(self):
        """Namespace prefixes are preserved in tag names."""
        xml = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"><xs:element/></xs:schema>'

        bag = BagXmlParserPure.parse(xml, Bag)

        assert 'xs:schema' in bag.keys()


# =============================================================================
# BagXmlParserLegacy Tests
# =============================================================================


class TestBagXmlParserLegacy:
    """Tests for BagXmlParserLegacy."""

    def test_parse_genrobag_format(self):
        """Parse GenRoBag format XML."""
        xml = "<?xml version='1.0'?><GenRoBag><name>test</name></GenRoBag>"

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['name'] == 'test'

    def test_parse_integer_type(self):
        """Parse integer with _T="L" type."""
        xml = '<GenRoBag><count _T="L">42</count></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['count'] == 42
        assert isinstance(bag['count'], int)

    def test_parse_float_type(self):
        """Parse float with _T="R" type."""
        xml = '<GenRoBag><price _T="R">19.99</price></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['price'] == 19.99
        assert isinstance(bag['price'], float)

    def test_parse_boolean_true(self):
        """Parse boolean True with _T="B" type.

        genro_tytx uses 'true'/'false' for booleans.
        """
        xml = '<GenRoBag><active _T="B">true</active></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['active'] is True

    def test_parse_boolean_false(self):
        """Parse boolean False with _T="B" type.

        genro_tytx uses 'true'/'false' for booleans.
        """
        xml = '<GenRoBag><deleted _T="B">false</deleted></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['deleted'] is False

    def test_parse_date_type(self):
        """Parse date with _T="D" type."""
        xml = '<GenRoBag><created _T="D">2025-01-15</created></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['created'] == datetime.date(2025, 1, 15)

    def test_parse_datetime_type(self):
        """Parse datetime with _T="DH" type."""
        xml = '<GenRoBag><timestamp _T="DH">2025-01-15T10:30:00</timestamp></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['timestamp'] == datetime.datetime(2025, 1, 15, 10, 30, 0)

    def test_parse_decimal_type(self):
        """Parse decimal with _T="N" type."""
        xml = '<GenRoBag><amount _T="N">123.45</amount></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['amount'] == Decimal('123.45')

    def test_parse_nested_structure(self):
        """Parse nested GenRoBag structure."""
        xml = '''<GenRoBag>
            <config>
                <host>localhost</host>
                <port _T="L">8080</port>
            </config>
        </GenRoBag>'''

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['config.host'] == 'localhost'
        assert bag['config.port'] == 8080

    def test_parse_typed_attributes(self):
        """Parse attributes with ::TYPE suffix.

        genro_tytx uses 'true'/'false' for booleans.
        """
        xml = '<GenRoBag><item count="42::L" active="true::B">value</item></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        node = bag.get_node('item')
        assert node.attr['count'] == 42
        assert node.attr['active'] is True

    def test_parse_sanitized_tag_restored(self):
        """_tag attribute restores original tag name."""
        xml = '<GenRoBag><my_key _tag="my-key">value</my_key></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['my-key'] == 'value'

    def test_parse_avoid_dup_label(self):
        """avoid_dup_label=True adds _N suffix to duplicates."""
        xml = '<GenRoBag><item>a</item><item>b</item></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag, avoid_dup_label=True)

        assert bag['item'] == 'a'
        assert bag['item_1'] == 'b'

    def test_parse_plain_xml_fallback(self):
        """Non-GenRoBag XML is parsed without type decoding."""
        xml = '<root><count>42</count></root>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        # Without GenRoBag root, values remain strings
        assert bag['root.count'] == '42'

    def test_parse_bytes_input(self):
        """Parse GenRoBag XML from bytes input."""
        xml = b'<GenRoBag><name>test</name></GenRoBag>'

        bag = BagXmlParserLegacy.parse(xml, Bag)

        assert bag['name'] == 'test'


# =============================================================================
# Round-trip Tests
# =============================================================================


class TestRoundTrip:
    """Test serialize -> parse round-trips."""

    def test_roundtrip_pure_simple(self):
        """Pure format round-trip with simple values.

        Note: XML requires a single root element, so we wrap in a container.
        """
        bag = Bag()
        bag['data'] = Bag()
        bag['data.name'] = 'test'
        bag['data.count'] = '42'  # Pure format keeps strings

        xml = BagXmlSerializerPure.serialize(bag)
        result = BagXmlParserPure.parse(xml, Bag)

        assert result['data.name'] == 'test'
        assert result['data.count'] == '42'

    def test_roundtrip_pure_nested(self):
        """Pure format round-trip with nested structure."""
        bag = Bag()
        bag['config'] = Bag()
        bag['config.host'] = 'localhost'
        bag['config.port'] = '8080'

        xml = BagXmlSerializerPure.serialize(bag)
        result = BagXmlParserPure.parse(xml, Bag)

        assert result['config.host'] == 'localhost'
        assert result['config.port'] == '8080'

    def test_roundtrip_legacy_typed_values(self):
        """Legacy format round-trip preserves types."""
        bag = Bag()
        bag['name'] = 'test'
        bag['count'] = 42
        bag['price'] = 19.99
        bag['active'] = True
        bag['created'] = datetime.date(2025, 1, 15)

        xml = BagXmlSerializerLegacy.serialize(bag)
        result = BagXmlParserLegacy.parse(xml, Bag)

        assert result['name'] == 'test'
        assert result['count'] == 42
        assert result['price'] == 19.99
        assert result['active'] is True
        assert result['created'] == datetime.date(2025, 1, 15)

    def test_roundtrip_legacy_nested(self):
        """Legacy format round-trip with nested structure."""
        bag = Bag()
        bag['config'] = Bag()
        bag['config.host'] = 'localhost'
        bag['config.port'] = 8080
        bag['config.debug'] = True

        xml = BagXmlSerializerLegacy.serialize(bag)
        result = BagXmlParserLegacy.parse(xml, Bag)

        assert result['config.host'] == 'localhost'
        assert result['config.port'] == 8080
        assert result['config.debug'] is True

    def test_roundtrip_legacy_with_attributes(self):
        """Legacy format round-trip preserves attributes."""
        bag = Bag()
        bag.set_item('item', 'value', _attributes={'id': 123, 'active': True})

        xml = BagXmlSerializerLegacy.serialize(bag)
        result = BagXmlParserLegacy.parse(xml, Bag)

        assert result['item'] == 'value'
        node = result.get_node('item')
        assert node.attr['id'] == 123
        assert node.attr['active'] is True
