"""Legacy-compatible BagToXml / BagFromXml for the genropy wrapper.

Ported from gnr.core.gnrbagxml to work with genro_bag.Bag/BagNode objects
through the wrapper layer. Produces XML identical to the old BagToXml for
the legacy JS client.

Removed: mode4d (4D array support). Kept as no-op parameter.
Kept: translate_cb, catalog, typeattrs/typevalue, resolver serialization,
      __forbidden__, BagAsXml, forcedTagAttr, omitUnknownTypes, array READ.
"""

import datetime
import io
import json
import os
import re

from decimal import Decimal
from xml import sax
from xml.dom.minidom import parseString as _minidom_parseString
from xml.sax import saxutils
from xml.sax.handler import ContentHandler

import genro_bag
from gnr.core.gnrclasses import GnrClassCatalog

REGEX_XML_ILLEGAL = re.compile(r'<|>|&')
ZERO_TIME = datetime.time(0, 0)


class BagAsXml:
    """Wrapper class for storing raw XML values in a Bag node."""

    def __init__(self, value):
        self.value = value


def isValidValue(value):
    """Check if a value that would be falsy is still meaningful (0 or midnight)."""
    return value in (0, ZERO_TIME)


# ---------------------------------------------------------------------------
# BagFromXml
# ---------------------------------------------------------------------------

class BagFromXml:
    """Convert XML source to a Bag instance (legacy-compatible)."""

    def build(self, source, fromFile, catalog=None, bagcls=None, empty=None):
        return self._do_build(source, fromFile, catalog=catalog,
                              bagcls=bagcls, empty=empty)

    def _do_build(self, source, fromFile, catalog=None, bagcls=None, empty=None):
        bag_import = _SaxImporter()
        if not catalog:
            catalog = GnrClassCatalog()
        bag_import.catalog = catalog
        bag_import.bagcls = bagcls
        bag_import.empty = empty
        if fromFile:
            with open(source, 'rt', encoding='utf-8') as f:
                source = f.read()
        if isinstance(source, str):
            source = source.encode('utf-8')
        sax.parseString(source, bag_import)
        result = bag_import.bags[0][0]
        if bag_import.format == 'GenRoBag':
            result = result['GenRoBag']
        if result is None:
            result = []
        return result


class _SaxImporter(ContentHandler):
    """SAX handler that builds a Bag from XML events (legacy-compatible).

    Supports GenRoBag format detection, _T type codes, ::TYPE attribute
    suffixes, array handling (A* type codes with <C> tags), and duplicate
    tag labels via addItem.
    """

    def startDocument(self):
        self.bags = [[self.bagcls(), None]]
        self.valueList = []
        self.format = ''
        self.currType = None
        self.currArray = None

    def getValue(self, dtype=None):
        if self.valueList:
            if self.valueList[0] == '\n':
                self.valueList[:] = self.valueList[1:]
            if self.valueList:
                if self.valueList[-1] == '\n':
                    self.valueList.pop()
        value = ''.join(self.valueList)
        if dtype != 'BAG':
            value = saxutils.unescape(value)
        return value

    def startElement(self, tagLabel, attributes):
        attributes = dict([
            (str(k), self.catalog.fromTypedText(saxutils.unescape(v)))
            for k, v in attributes.items()
        ])
        if len(self.bags) == 1:
            if tagLabel.lower() == 'genrobag':
                self.format = 'GenRoBag'
            else:
                self.format = 'xml'
            self.bags.append((self.bagcls(), attributes))
        else:
            if self.format == 'GenRoBag':
                self.currType = None
                if '_T' in attributes:
                    self.currType = attributes.pop('_T')
                elif 'T' in attributes:
                    self.currType = attributes.pop('T')
                if not self.currArray:
                    newitem = self.bagcls()
                    if self.currType:
                        if self.currType.startswith("A"):
                            self.currArray = tagLabel
                            newitem = []
                    self.bags.append((newitem, attributes))
            else:
                if ''.join(self.valueList).strip() != '':
                    value = self.getValue()
                    if value:
                        dest = self.bags[-1][0]
                        dest.addItem('_', value)
                self.bags.append((self.bagcls(), attributes))
        self.valueList = []

    def characters(self, s):
        self.valueList.append(s)

    def endElement(self, tagLabel):
        value = self.getValue(dtype=self.currType)
        self.valueList = []
        dest = self.bags[-1][0]
        if self.format == 'GenRoBag':
            if value:
                if self.currType and self.currType != 'T':
                    try:
                        value = self.catalog.fromText(value, self.currType)
                    except Exception:
                        value = None
        if self.currArray:
            if self.currArray != tagLabel:
                # Array content element (<C>)
                if value == '':
                    if self.currType and self.currType != 'T':
                        value = self.catalog.fromText('', self.currType)
                dest.append(value)
            else:
                # Array enclosure element
                self.currArray = None
                curr, attributes = self.bags.pop()
                self._set_into_parent(tagLabel, curr, attributes)
        else:
            curr, attributes = self.bags.pop()
            if value or isValidValue(value):
                if curr:
                    if isinstance(value, str):
                        value = value.strip()
                    if value:
                        dest_inner = curr
                        dest_inner.addItem('_', value)
                else:
                    curr = value
            if not curr and not isValidValue(curr):
                if self.empty:
                    curr = self.empty()
                else:
                    curr = self.catalog.fromText('', self.currType)
            self._set_into_parent(tagLabel, curr, attributes)

    def _set_into_parent(self, tagLabel, curr, attributes):
        """Insert a parsed node into the parent Bag, supporting duplicates."""
        dest = self.bags[-1][0]
        if '_tag' in attributes:
            tagLabel = attributes.pop('_tag')
        dest.addItem(tagLabel, curr,
                     _attributes=attributes if attributes else None)


# ---------------------------------------------------------------------------
# BagToXml
# ---------------------------------------------------------------------------

class BagToXml:
    """Convert a Bag to XML string (legacy-compatible).

    Faithful port of gnr.core.gnrbagxml.BagToXml adapted for genro_bag.Bag.
    """

    def nodeToXmlBlock(self, node, namespaces=None):
        """Serialize a single BagNode to an XML fragment."""
        nodeattr = dict(node.attr)
        local_namespaces = [k[6:] for k in nodeattr.keys() if k.startswith('xmlns:')]
        current_namespaces = namespaces + local_namespaces

        if '__forbidden__' in nodeattr:
            return ''

        if self.unresolved and node.resolver is not None and not getattr(
                node.resolver, '_xmlEager', None):
            if not nodeattr.get('_resolver_name'):
                nodeattr['_resolver'] = json.dumps(node.resolver.resolverSerialize())
            value = ''
            if isinstance(node._value, genro_bag.Bag):
                value = self.bagToXmlBlock(node._value, namespaces=current_namespaces)
            return self.buildTag(node.label, value, nodeattr, '',
                                 xmlMode=True, namespaces=namespaces)

        nodeValue = node.getValue()

        if isinstance(nodeValue, genro_bag.Bag) and nodeValue:
            result = self.buildTag(
                node.label,
                self.bagToXmlBlock(nodeValue, namespaces=current_namespaces),
                nodeattr, '', xmlMode=True, localize=False,
                namespaces=namespaces)
        elif isinstance(nodeValue, BagAsXml):
            result = self.buildTag(node.label, nodeValue, nodeattr, '',
                                   xmlMode=True, namespaces=namespaces)
        else:
            result = self.buildTag(node.label, nodeValue, node.attr,
                                   namespaces=namespaces)
        return result

    def bagToXmlBlock(self, bag, namespaces=None):
        """Return XML block for all nodes in a Bag."""
        return '\n'.join([
            self.nodeToXmlBlock(node, namespaces=namespaces)
            for node in bag.nodes
        ])

    def build(self, bag, filename=None, encoding='UTF-8', catalog=None,
              typeattrs=True, typevalue=True, addBagTypeAttr=True,
              unresolved=False, autocreate=False, docHeader=None,
              self_closed_tags=None, translate_cb=None, omitUnknownTypes=False,
              omitRoot=False, forcedTagAttr=None, mode4d=False, pretty=None):
        """Serialize a Bag to complete XML string.

        Args:
            mode4d: Accepted for backward compatibility but has no effect.
        """
        result = ''
        if docHeader is not False:
            result = docHeader or "<?xml version='1.0' encoding='" + encoding + "'?>\n"
        if not catalog:
            catalog = GnrClassCatalog()
        # Register wrapper Bag class so catalog recognizes it
        catalog.names[type(bag)] = 'BAG'

        self.translate_cb = translate_cb
        self.omitUnknownTypes = omitUnknownTypes
        self.catalog = catalog
        self.typeattrs = typeattrs
        self.typevalue = typevalue
        self.self_closed_tags = self_closed_tags or []
        self.forcedTagAttr = forcedTagAttr
        self.addBagTypeAttr = addBagTypeAttr
        self.unresolved = unresolved

        if not typeattrs:
            self.catalog.addSerializer("asText", bool, lambda b: 'y' * int(b))

        if omitRoot:
            result = result + self.bagToXmlBlock(bag, namespaces=[])
        else:
            result = result + self.buildTag(
                'GenRoBag', self.bagToXmlBlock(bag, namespaces=[]),
                xmlMode=True, localize=False)

        if pretty:
            result = _minidom_parseString(result).toprettyxml()
            result = result.replace('\t\n', '').replace('\t\n', '')

        if filename:
            if autocreate:
                dirname = os.path.dirname(filename)
                if dirname and not os.path.exists(dirname):
                    os.makedirs(dirname)
            with open(filename, 'wt', encoding='utf-8') as output:
                output.write(result)
        return result

    def buildTag(self, tagName, value, attributes=None, cls='', xmlMode=False,
                 localize=True, namespaces=None):
        """Build a single XML tag string with type annotation and attributes."""
        t = cls
        if not t:
            if value != '':
                if isinstance(value, genro_bag.Bag):
                    if self.addBagTypeAttr:
                        value, t = '', 'BAG'
                    else:
                        value = ''
                elif isinstance(value, BagAsXml):
                    value = value.value
                else:
                    value, t = self.catalog.asTextAndType(
                        value,
                        translate_cb=self.translate_cb if localize else None,
                        nestedTyping=True)
                    value = str(value)
        if attributes:
            attributes = dict(attributes)
            if self.forcedTagAttr and self.forcedTagAttr in attributes:
                tagName = attributes.pop(self.forcedTagAttr)
            if tagName == '__flatten__':
                return value
            if self.omitUnknownTypes:
                _safe_types = (
                    str, int, float, datetime.date, datetime.time,
                    datetime.datetime, bool, type(None), list, tuple, dict, Decimal,
                )
                attributes = dict([
                    (k, v) for k, v in attributes.items()
                    if isinstance(v, _safe_types) or (
                        callable(v) and (
                            hasattr(v, 'is_rpc') or hasattr(v, '__safe__') or
                            (hasattr(v, '__name__') and v.__name__.startswith('rpc_'))
                        )
                    )
                ])
            else:
                attributes = dict([(k, v) for k, v in attributes.items()])
            if self.typeattrs:
                attributes = ' '.join([
                    '%s=%s' % (lbl, saxutils.quoteattr(
                        self.catalog.asTypedText(
                            val,
                            translate_cb=self.translate_cb)))
                    for lbl, val in attributes.items()
                ])
            else:
                attributes = ' '.join([
                    '%s=%s' % (lbl, saxutils.quoteattr(
                        self.catalog.asText(
                            val, translate_cb=self.translate_cb)))
                    for lbl, val in attributes.items()
                    if val is not False
                ])

        originalTag = tagName
        if not tagName:
            tagName = '_none_'
        if ':' in originalTag and originalTag.split(':')[0] not in (namespaces or []):
            tagName = tagName.replace(':', '_')
        tagName = re.sub(r'[^\w.]', '_', originalTag).replace('__', '_')
        if tagName[0].isdigit():
            tagName = '_' + tagName

        if tagName != originalTag:
            result = '<%s _tag=%s' % (
                tagName, saxutils.quoteattr(saxutils.escape(originalTag)))
        else:
            result = '<%s' % tagName

        if self.typevalue and t != '' and t != 'T':
            result = '%s _T="%s"' % (result, t)
        if attributes:
            result = "%s %s" % (result, attributes)

        if not xmlMode:
            if value.endswith('::HTML'):
                value = value[:-6]
            elif REGEX_XML_ILLEGAL.search(value):
                value = saxutils.escape(value)

        if not value and tagName in self.self_closed_tags:
            result = '%s/>' % result
        else:
            result = '%s>%s</%s>' % (result, value, tagName)

        return result


# ---------------------------------------------------------------------------
# XmlOutputBag — streaming writer
# ---------------------------------------------------------------------------

class XmlOutputBag:
    """Context-manager streaming XML writer for large Bag data.

    Requires bagcls to be passed (typically the wrapper's Bag class).

    Usage:
        with XmlOutputBag('output.xml', bagcls=Bag) as b:
            for item in collection:
                b.addItemBag('element', item.getValue(), attr=True)
        result = b.content
    """

    def __init__(self, filepath=None, output=None, docHeader=True, encoding='UTF-8',
                 omitRoot=False, counter=None, typeattrs=False, typevalue=False,
                 bagcls=None):
        self.filepath = filepath
        self.docHeader = docHeader
        self.omitRoot = omitRoot
        self.counter = counter
        self.encoding = encoding
        self.typeattrs = typeattrs
        self.typevalue = typevalue
        self.bagcls = bagcls
        if not output:
            if filepath:
                output = open(filepath, 'wt', encoding='utf-8')
            else:
                output = io.StringIO()
        self.output = output

    def __enter__(self):
        if self.docHeader:
            if self.docHeader is True:
                docHeader = "<?xml version='1.0' encoding='" + self.encoding + "'?>\n"
            else:
                docHeader = self.docHeader
            self.output.write(docHeader)
        if not self.omitRoot:
            if self.counter is not None:
                root = '<GenRoBag len="%s">' % self.counter
            else:
                root = '<GenRoBag>'
            self.output.write(root)
        return self

    def addItemBag(self, label, value, _attributes=None, **kwargs):
        tempbag = self.bagcls()
        tempbag.addItem(label, value, _attributes=_attributes, **kwargs)
        bagxml = BagToXml().build(tempbag, typeattrs=self.typeattrs,
                                  typevalue=self.typevalue,
                                  unresolved=True, omitRoot=True,
                                  docHeader=False, pretty=False)
        self.output.write(bagxml)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.omitRoot:
            self.output.write('</GenRoBag>')
        if not self.filepath:
            self.content = self.output.getvalue()
        self.output.close()
