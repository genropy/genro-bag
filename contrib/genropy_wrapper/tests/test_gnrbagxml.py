"""Tests for replacement.gnrbagxml — legacy-compatible XML serialization."""

import datetime
import os
import tempfile

import pytest
from decimal import Decimal

from replacement.gnrbag import Bag, BagAsXml
from replacement.gnrbagxml import BagToXml, BagFromXml, XmlOutputBag


# ---------------------------------------------------------------------------
# BagToXml tests
# ---------------------------------------------------------------------------

class TestBagToXml:
    """Test BagToXml serialization."""

    def test_basic_types_roundtrip(self):
        """All basic types serialize with correct _T codes and roundtrip."""
        b = Bag()
        b['name'] = 'hello'
        b['count'] = 42
        b['ratio'] = 3.14
        b['active'] = True
        b['birthday'] = datetime.date(1974, 11, 23)
        b['amount'] = Decimal('99.50')

        xml = b.toXml()
        assert '_T="L"' in xml  # int
        assert '_T="R"' in xml  # float
        assert '_T="B"' in xml  # bool
        assert '_T="D"' in xml  # date
        assert '_T="N"' in xml  # Decimal

        b2 = Bag()
        b2.fromXml(xml)
        assert b2['name'] == 'hello'
        assert b2['count'] == 42
        assert b2['ratio'] == 3.14
        assert b2['active'] is True
        assert b2['birthday'] == datetime.date(1974, 11, 23)
        assert b2['amount'] == Decimal('99.50')

    def test_nested_bag(self):
        """Nested bags produce proper XML hierarchy."""
        b = Bag()
        b['parent.child'] = 'value'
        xml = b.toXml()
        assert '<parent>' in xml
        assert '<child>value</child>' in xml
        assert '</parent>' in xml

    def test_genrobag_root(self):
        """Default output wraps in <GenRoBag>."""
        b = Bag()
        b['x'] = 1
        xml = b.toXml()
        assert '<GenRoBag>' in xml
        assert '</GenRoBag>' in xml

    def test_omit_root(self):
        """omitRoot=True removes <GenRoBag> wrapper."""
        b = Bag()
        b['x'] = 1
        xml = b.toXml(omitRoot=True)
        assert '<GenRoBag>' not in xml

    def test_doc_header(self):
        """docHeader controls XML declaration."""
        b = Bag()
        b['x'] = 1
        xml_with = b.toXml()
        assert "<?xml version='1.0'" in xml_with

        xml_without = b.toXml(docHeader=False)
        assert '<?xml' not in xml_without

        xml_custom = b.toXml(docHeader='<!-- custom -->')
        assert '<!-- custom -->' in xml_custom

    def test_translate_cb(self):
        """translate_cb is applied to string values."""
        b = Bag()
        b['greeting'] = 'hello'
        b['count'] = 42  # non-string: callback NOT applied

        xml = b.toXml(translate_cb=lambda s: s.upper())
        assert '>HELLO<' in xml
        assert '>42<' in xml  # int not affected

    def test_typevalue_false(self):
        """typevalue=False omits _T attributes."""
        b = Bag()
        b['count'] = 42
        xml = b.toXml(typevalue=False, omitRoot=True, docHeader=False)
        assert '_T=' not in xml
        assert '<count>42</count>' in xml

    def test_forbidden(self):
        """Nodes with __forbidden__ attribute are excluded."""
        b = Bag()
        b.setItem('visible', 'yes')
        b.setItem('secret', 'no', _attributes={'__forbidden__': True})
        xml = b.toXml()
        assert 'visible' in xml
        assert 'secret' not in xml

    def test_bag_as_xml(self):
        """BagAsXml embeds raw XML without escaping."""
        b = Bag()
        b.setItem('html', BagAsXml('<b>bold</b>'))
        xml = b.toXml(omitRoot=True, docHeader=False)
        assert '<html><b>bold</b></html>' in xml

    def test_forced_tag_attr(self):
        """forcedTagAttr uses attribute value as tag name."""
        b = Bag()
        b.setItem('row', 'value', _attributes={'_name': 'custom_tag'})
        xml = b.toXml(forcedTagAttr='_name', omitRoot=True, docHeader=False)
        assert '<custom_tag>' in xml
        assert '</custom_tag>' in xml

    def test_self_closed_tags(self):
        """self_closed_tags produce self-closing syntax."""
        b = Bag()
        b.setItem('br', '', _attributes={})
        xml = b.toXml(self_closed_tags=['br'], omitRoot=True, docHeader=False)
        assert '<br/>' in xml

    def test_pretty(self):
        """pretty=True produces indented XML."""
        b = Bag()
        b['a.b'] = 'value'
        xml = b.toXml(pretty=True)
        # Pretty XML should have indentation
        assert '\n' in xml

    def test_mode4d_noop(self):
        """mode4d parameter is accepted without error."""
        b = Bag()
        b['x'] = 1
        xml = b.toXml(mode4d=True)
        assert '<GenRoBag>' in xml

    def test_file_output(self):
        """filename parameter writes XML to file."""
        b = Bag()
        b['x'] = 1
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            path = f.name
        try:
            b.toXml(filename=path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert '<GenRoBag>' in content
        finally:
            os.unlink(path)

    def test_autocreate(self):
        """autocreate creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'sub', 'dir', 'out.xml')
            b = Bag()
            b['x'] = 1
            b.toXml(filename=path, autocreate=True)
            assert os.path.exists(path)

    def test_omit_unknown_types(self):
        """omitUnknownTypes filters callables from attributes."""
        b = Bag()
        b.setItem('node', 'value', _attributes={'name': 'ok', 'func': lambda: None})
        xml = b.toXml(omitUnknownTypes=True, omitRoot=True, docHeader=False)
        assert 'name=' in xml
        assert 'func=' not in xml

    def test_add_bag_type_attr_false(self):
        """addBagTypeAttr=False omits _T='BAG' on nested bags."""
        b = Bag()
        b['sub.x'] = 'val'
        xml = b.toXml(addBagTypeAttr=False, omitRoot=True, docHeader=False)
        assert '_T="BAG"' not in xml

    def test_flatten_tag(self):
        """__flatten__ tag returns value directly without tag wrapper."""
        b = Bag()
        b.setItem('__flatten__', 'inline content')
        xml = b.toXml(omitRoot=True, docHeader=False)
        assert 'inline content' in xml
        assert '<__flatten__>' not in xml


# ---------------------------------------------------------------------------
# BagFromXml tests
# ---------------------------------------------------------------------------

class TestBagFromXml:
    """Test BagFromXml deserialization."""

    def test_genrobag_format(self):
        """Parses GenRoBag format with _T type codes."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><name>John</name><age _T="L">30</age><ratio _T="R">3.14</ratio></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        assert b['name'] == 'John'
        assert b['age'] == 30
        assert isinstance(b['age'], int)
        assert b['ratio'] == 3.14

    def test_plain_xml(self):
        """Parses non-GenRoBag XML (all values as strings, root tag preserved)."""
        xml = '<root><item>hello</item><count>42</count></root>'
        b = Bag()
        b.fromXml(xml)
        # Plain XML: root tag becomes a node, no type conversion
        assert b['root.item'] == 'hello'
        assert b['root.count'] == '42'

    def test_array_handling(self):
        """Parses legacy array format with _T="AL" and <C> tags."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><items _T="AL"><C _T="L">10</C><C _T="L">20</C><C _T="L">30</C></items></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        result = b['items']
        assert isinstance(result, list)
        assert result == [10, 20, 30]

    def test_tag_override(self):
        """_tag attribute overrides the tag name as label."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><_3d _tag="3d">value</_3d></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        assert b['3d'] == 'value'

    def test_duplicate_tags(self):
        """Handles duplicate sibling tag names."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><phone><mobile _T="L">555</mobile><mobile _T="L">444</mobile></phone></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        nodes = b['phone'].nodes
        assert len(nodes) == 2
        assert nodes[0].label == 'mobile'
        assert nodes[1].label == 'mobile'

    def test_typed_attributes(self):
        """Parses ::TYPE suffix on attribute values."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><item count="42::L" active="y::B">text</item></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        node = b.getNode('item')
        assert node.attr['count'] == 42
        assert node.attr['active'] is True

    def test_nested_bag(self):
        """Parses nested XML into nested Bags."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><parent><child>value</child></parent></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        assert b['parent.child'] == 'value'

    def test_from_file(self):
        """Loads XML from a file path."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<GenRoBag><x _T="L">1</x></GenRoBag>'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml',
                                         delete=False, encoding='utf-8') as f:
            f.write(xml)
            path = f.name
        try:
            b = Bag()
            b.fromXml(path)
            assert b['x'] == 1
        finally:
            os.unlink(path)

    def test_date_type(self):
        """Date values roundtrip correctly."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><birthday _T="D">1974-11-23</birthday></GenRoBag>'''
        b = Bag()
        b.fromXml(xml)
        assert b['birthday'] == datetime.date(1974, 11, 23)

    def test_empty_value_with_empty_callback(self):
        """empty parameter provides default for empty elements."""
        xml = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag><item></item></GenRoBag>'''
        b = Bag()
        b.fromXml(xml, empty=lambda: 'DEFAULT')
        assert b['item'] == 'DEFAULT'


# ---------------------------------------------------------------------------
# Roundtrip tests
# ---------------------------------------------------------------------------

class TestRoundtrip:
    """Full toXml -> fromXml roundtrip tests."""

    def test_mixed_types(self):
        """All supported types survive a roundtrip."""
        b = Bag()
        b['s'] = 'text'
        b['i'] = 42
        b['f'] = 3.14
        b['b'] = True
        b['d'] = datetime.date(2025, 1, 15)
        b['n'] = Decimal('123.45')

        xml = b.toXml()
        b2 = Bag()
        b2.fromXml(xml)

        assert b2['s'] == 'text'
        assert b2['i'] == 42
        assert b2['f'] == 3.14
        assert b2['b'] is True
        assert b2['d'] == datetime.date(2025, 1, 15)
        assert b2['n'] == Decimal('123.45')

    def test_nested_roundtrip(self):
        """Nested structure survives roundtrip."""
        b = Bag()
        b['a.b.c'] = 'deep'
        b['a.x'] = 1

        xml = b.toXml()
        b2 = Bag()
        b2.fromXml(xml)

        assert b2['a.b.c'] == 'deep'
        assert b2['a.x'] == 1

    def test_special_chars(self):
        """XML special characters are properly escaped and restored."""
        b = Bag()
        b['text'] = 'a < b & c > d'

        xml = b.toXml()
        assert '&lt;' in xml
        assert '&amp;' in xml

        b2 = Bag()
        b2.fromXml(xml)
        assert b2['text'] == 'a < b & c > d'

    def test_attributes_roundtrip(self):
        """Node attributes survive roundtrip with type info."""
        b = Bag()
        b.setItem('node', 'value', _attributes={'count': 5, 'name': 'test'})

        xml = b.toXml()
        b2 = Bag()
        b2.fromXml(xml)

        node = b2.getNode('node')
        assert node.attr['count'] == 5
        assert node.attr['name'] == 'test'

    def test_empty_bag(self):
        """Empty bag roundtrips correctly."""
        b = Bag()
        xml = b.toXml()
        b2 = Bag()
        b2.fromXml(xml)
        assert len(b2) == 0


# ---------------------------------------------------------------------------
# XmlOutputBag tests
# ---------------------------------------------------------------------------

class TestXmlOutputBag:
    """Test streaming XML writer."""

    def test_basic_streaming(self):
        """XmlOutputBag produces valid XML."""
        with XmlOutputBag(bagcls=Bag) as xob:
            xob.addItemBag('item', 'hello', _attributes={'id': 1})
            xob.addItemBag('item', 'world', _attributes={'id': 2})
        result = xob.content
        assert '<GenRoBag>' in result
        assert '</GenRoBag>' in result
        assert 'hello' in result
        assert 'world' in result

    def test_omit_root(self):
        """XmlOutputBag respects omitRoot."""
        with XmlOutputBag(bagcls=Bag, omitRoot=True) as xob:
            xob.addItemBag('item', 'hello')
        assert '<GenRoBag>' not in xob.content

    def test_file_output(self):
        """XmlOutputBag writes to file."""
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            path = f.name
        try:
            with XmlOutputBag(filepath=path, bagcls=Bag) as xob:
                xob.addItemBag('item', 'hello')
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert 'hello' in content
        finally:
            os.unlink(path)
