"""Pretty XML is emitted from nodes, without reparsing serialized content."""
from xml.dom import minidom
from xml.etree import ElementTree as ET

import pytest

from genro_bag import Bag


def example():
    b = Bag()
    b.set_item('root.text', '  a & <b>\n  c  ')
    b.set_item('root.branch.n', 12)
    b.set_item('root.empty', Bag())
    b.set_item('tail', 'end')
    return b


def test_direct_pretty_output_and_compact_stays_unchanged(monkeypatch):
    b = example()
    def forbidden(*args, **kwargs):
        pytest.fail('Serialization must not parse XML')
    monkeypatch.setattr(minidom, 'parseString', forbidden)
    monkeypatch.setattr(b, '_prettify_xml', forbidden, raising=False)
    assert b.to_xml(pretty=True) == (
        '<root>\n  <text>  a &amp; &lt;b&gt;\n  c  </text>\n'
        '  <branch>\n    <n>12</n>\n  </branch>\n  <empty/>\n</root>\n<tail>end</tail>'
    )
    assert b.to_xml() == (
        '<root><text>  a &amp; &lt;b&gt;\n  c  </text>'
        '<branch><n>12</n></branch><empty/></root><tail>end</tail>'
    )


def test_pretty_preserves_text_attributes_and_namespaces():
    b = Bag()
    b.set_item('root', Bag(), {'xmlns:p': 'urn:test'})
    b.set_item('root.p:child', ' \n<&> ', {'title': 'a\tb\nc"d'})
    compact = ET.fromstring(b.to_xml())
    pretty = ET.fromstring(b.to_xml(pretty=True))
    assert pretty[0].tag == compact[0].tag == '{urn:test}child'
    assert pretty[0].text == compact[0].text == ' \n<&> '
    assert pretty[0].attrib == compact[0].attrib


def test_empty_and_explicit_close_and_headers(tmp_path):
    assert Bag().to_xml(pretty=True) == ''
    b = Bag({'a': None, 'b': Bag()})
    xml = b.to_xml(pretty=True, self_closed_tags=[], doc_header=True)
    assert xml == "<?xml version='1.0' encoding='UTF-8'?>\n<a></a>\n<b></b>"
    target = tmp_path / 'bag.xml'
    assert b.to_xml(filename=str(target), pretty=True, self_closed_tags=[], doc_header=True) is None
    assert target.read_text() == xml
    assert b.to_xml(pretty=True, doc_header='<!DOCTYPE a>') == '<!DOCTYPE a>\n<a/>\n<b/>'


def test_xml_space_preserve_keeps_subtree_compact():
    b = Bag()
    b.set_item('root.group', Bag({'a': 'x', 'b': 'y'}), {'xml:space': 'preserve'})
    assert b.to_xml(pretty=True) == (
        '<root>\n  <group xml:space="preserve"><a>x</a><b>y</b></group>\n</root>'
    )


def test_wide_bag_serializes_each_node_once(monkeypatch):
    b = Bag({f'n{i}': str(i) for i in range(1000)})
    original = b._node_to_xml
    count = 0
    def counted(*args, **kwargs):
        nonlocal count
        count += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(b, '_node_to_xml', counted)
    xml = b.to_xml(pretty=True)
    assert count == 1000
    assert xml.count('\n') == 999
    assert xml.endswith('<n999>999</n999>')
