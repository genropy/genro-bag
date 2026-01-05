# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML serialization classes for Bag.

This module provides classes for serializing and deserializing Bag
hierarchies to/from XML format.

Classes:
    BagXmlSerializer - serialize Bag to XML (values as strings)
    BagXmlParser - parse XML to Bag (auto-detects legacy format with _T types)
"""

from __future__ import annotations

import datetime
import html
import os
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from xml import sax
from xml.sax import saxutils

from genro_tytx import from_tytx

if TYPE_CHECKING:
    from .bag import Bag


# Regex for sanitizing XML tag names
_INVALID_XML_TAG_CHARS = re.compile(r'[^\w.]', re.ASCII)


# =============================================================================
# SERIALIZERS
# =============================================================================


class BagXmlSerializer:
    """XML serializer for Bag.

    Converts a Bag hierarchy into an XML document. All values are
    converted to strings without type information.

    Example:
        >>> from genro_bag import Bag
        >>> from genro_bag.bag_xml import BagXmlSerializer
        >>>
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> bag['count'] = 42
        >>>
        >>> xml = BagXmlSerializer.serialize(bag)
        '<name>test</name><count>42</count>'
    """

    def __init__(
        self,
        bag: Bag,
        encoding: str = 'UTF-8',
        doc_header: bool | str | None = None,
        pretty: bool = False,
        self_closed_tags: list[str] | None = None,
    ):
        """Initialize the serializer.

        Args:
            bag: The Bag to serialize.
            encoding: XML encoding (default UTF-8).
            doc_header: XML declaration:
                - None/False: No declaration
                - True: Auto-generate with encoding
                - str: Custom declaration string
            pretty: If True, format with indentation.
            self_closed_tags: List of tag names to self-close when empty.
                If None, all empty tags are self-closed.
        """
        self.bag = bag
        self.encoding = encoding
        self.doc_header = doc_header
        self.pretty = pretty
        self.self_closed_tags = self_closed_tags

    @classmethod
    def serialize(
        cls,
        bag: Bag,
        filename: str | None = None,
        encoding: str = 'UTF-8',
        doc_header: bool | str | None = None,
        pretty: bool = False,
        self_closed_tags: list[str] | None = None,
    ) -> str | None:
        """Serialize Bag to XML string.

        Args:
            bag: The Bag to serialize.
            filename: Optional file path to write to. If provided, returns None.
            encoding: XML encoding (default UTF-8).
            doc_header: XML declaration.
            pretty: If True, format with indentation.
            self_closed_tags: List of tag names to self-close when empty.

        Returns:
            XML string if filename is None, else None (written to file).
        """
        instance = cls(
            bag=bag,
            encoding=encoding,
            doc_header=doc_header,
            pretty=pretty,
            self_closed_tags=self_closed_tags,
        )
        result = instance._serialize()

        if filename:
            result_bytes = result.encode(encoding)
            with open(filename, 'wb') as f:
                f.write(result_bytes)
            return None

        return result

    def _serialize(self) -> str:
        """Main serialization logic."""
        content = self._bag_to_xml(self.bag, namespaces=[])

        # Add XML declaration
        if self.doc_header is True:
            content = f"<?xml version='1.0' encoding='{self.encoding}'?>\n{content}"
        elif isinstance(self.doc_header, str):
            content = f'{self.doc_header}\n{content}'

        # Pretty print
        if self.pretty:
            content = self._prettify(content)

        return content

    def _prettify(self, xml_str: str) -> str:
        """Format XML with indentation."""
        from xml.dom.minidom import parseString

        try:
            result = parseString(xml_str).toprettyxml(indent="  ")
            # Remove the xml declaration added by toprettyxml
            if result.startswith('<?xml'):
                result = result.split('\n', 1)[1] if '\n' in result else ''
            return result
        except Exception:
            # If parsing fails (e.g., multiple roots), wrap temporarily
            wrapped = f"<_root_>{xml_str}</_root_>"
            pretty_xml = parseString(wrapped).toprettyxml(indent="  ")
            # Extract content between _root_ tags
            start = pretty_xml.find('<_root_>') + 8
            end = pretty_xml.rfind('</_root_>')
            return pretty_xml[start:end].strip()

    def _bag_to_xml(self, bag: Bag, namespaces: list[str]) -> str:
        """Convert Bag to XML string."""
        parts = []
        for node in bag:
            parts.append(self._node_to_xml(node, namespaces))
        return ''.join(parts)

    def _node_to_xml(self, node: Any, namespaces: list[str]) -> str:
        """Convert a BagNode to XML string."""
        from .bag import Bag

        # Extract local namespaces from this node's attributes
        local_namespaces = self._extract_namespaces(node.attr)
        current_namespaces = namespaces + local_namespaces

        tag, original_tag = self._sanitize_tag(node.label, current_namespaces)

        # Build attributes string
        attrs_parts = []
        if original_tag is not None:
            attrs_parts.append(f'_tag={saxutils.quoteattr(html.escape(original_tag))}')

        if node.attr:
            for k, v in node.attr.items():
                if v is not None and v is not False:
                    attrs_parts.append(f'{k}={saxutils.quoteattr(str(v))}')

        attrs_str = ' ' + ' '.join(attrs_parts) if attrs_parts else ''

        # Handle value
        value = node.value

        if isinstance(value, Bag):
            inner = self._bag_to_xml(value, current_namespaces)
            if inner:
                return f'<{tag}{attrs_str}>{inner}</{tag}>'
            # Empty Bag
            if self.self_closed_tags is None or tag in self.self_closed_tags:
                return f'<{tag}{attrs_str}/>'
            return f'<{tag}{attrs_str}></{tag}>'

        # Scalar value
        if value is None or value == '':
            if self.self_closed_tags is None or tag in self.self_closed_tags:
                return f'<{tag}{attrs_str}/>'
            return f'<{tag}{attrs_str}></{tag}>'

        text = html.escape(str(value))
        return f'<{tag}{attrs_str}>{text}</{tag}>'

    @staticmethod
    def _sanitize_tag(tag: str, namespaces: list[str]) -> tuple[str, str | None]:
        """Sanitize tag name for XML.

        Args:
            tag: The tag name to sanitize.
            namespaces: List of known namespace prefixes.

        Returns:
            (sanitized_tag, original_tag_or_none)
            original is None if no sanitization was needed.
        """
        if not tag:
            return '_none_', ''

        # If tag has a known namespace prefix, keep it as-is
        if ':' in tag:
            prefix = tag.split(':')[0]
            if prefix in namespaces:
                return tag, None

        sanitized = _INVALID_XML_TAG_CHARS.sub('_', tag).replace('__', '_')

        if sanitized[0].isdigit():
            sanitized = '_' + sanitized

        if sanitized != tag:
            return sanitized, tag
        return sanitized, None

    @staticmethod
    def _extract_namespaces(attrs: dict | None) -> list[str]:
        """Extract namespace prefixes from attributes (xmlns:prefix)."""
        if not attrs:
            return []
        return [k[6:] for k in attrs if k.startswith('xmlns:')]


# =============================================================================
# PARSERS
# =============================================================================


class BagXmlParser(sax.handler.ContentHandler):
    """XML parser for Bag (SAX handler).

    Parses XML and reconstructs a Bag hierarchy. Automatically detects
    and handles legacy GenRoBag format:
    - Decodes `_T` attribute for value types
    - Decodes `::TYPE` suffix in attribute values (TYTX encoding)
    - Handles `<GenRoBag>` root wrapper element
    - Supports array types (A*)

    For plain XML without type markers, values remain as strings.

    Example:
        >>> from genro_bag.bag_xml import BagXmlParser
        >>>
        >>> # Plain XML
        >>> xml = '<root><name>test</name></root>'
        >>> bag = BagXmlParser.parse(xml)
        >>> bag['root']['name']
        'test'
        >>>
        >>> # Legacy GenRoBag format
        >>> xml = '<GenRoBag><count _T="L">42</count></GenRoBag>'
        >>> bag = BagXmlParser.parse(xml)
        >>> bag['count']
        42
    """

    def __init__(
        self,
        empty: Callable[[], Any] | None = None,
        attr_in_value: bool = False,
    ):
        """Initialize the parser.

        Args:
            empty: Factory function for empty element values.
            attr_in_value: If True, store attributes as __attributes sub-bag.
        """
        super().__init__()
        self.empty = empty
        self.attr_in_value = attr_in_value

    @classmethod
    def parse(
        cls,
        source: str | bytes,
        empty: Callable[[], Any] | None = None,
        attr_in_value: bool = False,
    ) -> Bag:
        """Parse XML to Bag.

        Args:
            source: XML string or bytes to parse.
            empty: Factory function for empty element values.
            attr_in_value: If True, store attributes as __attributes sub-bag.

        Returns:
            Deserialized Bag with XML structure.
        """
        from .bag import Bag

        if isinstance(source, bytes):
            source = source.decode()

        # Replace environment variables (GNR_*)
        for k in os.environ:
            if k.startswith('GNR_'):
                source = source.replace(f'{{{k}}}', os.environ[k])

        handler = cls(
            empty=empty,
            attr_in_value=attr_in_value,
        )
        sax.parseString(source, handler)

        result = handler.bags[0][0]
        if handler.format == 'GenRoBag':
            result = result['GenRoBag']
        if result is None:
            result = Bag()
        return result

    def startDocument(self) -> None:
        from .bag import Bag
        self.bags: list[tuple[Any, dict]] = [(Bag(), None)]
        self.value_list: list[str] = []
        self.format = ''
        self.curr_type: str | None = None
        self.curr_array: str | None = None

    def _get_value(self, dtype: str | None = None) -> str:
        """Get accumulated character data as string."""
        if self.value_list:
            if self.value_list[0] == '\n':
                self.value_list[:] = self.value_list[1:]
            if self.value_list and self.value_list[-1] == '\n':
                self.value_list.pop()
        value = ''.join(self.value_list)
        if dtype != 'BAG':
            value = saxutils.unescape(value)
        return value

    def _decode_attrs(self, attributes: Any) -> dict:
        """Decode attributes, trying TYTX format."""
        return {str(k): from_tytx(saxutils.unescape(v)) for k, v in attributes.items()}

    def _decode_value_with_type(self, value: str, type_code: str | None) -> Any:
        """Decode element value using type code."""
        if not value:
            if type_code and type_code != 'T':
                return from_tytx(f'::{type_code}')
            return value

        if type_code and type_code != 'T':
            try:
                return from_tytx(f'{value}::{type_code}')
            except Exception:
                return None
        return value

    def startElement(self, tag_label: str, attributes: Any) -> None:
        from .bag import Bag
        attrs = self._decode_attrs(attributes)

        if len(self.bags) == 1:
            # First element - detect format
            if tag_label.lower() == 'genrobag':
                self.format = 'GenRoBag'
            else:
                self.format = 'xml'
            self.bags.append((Bag(), attrs))
        else:
            if self.format == 'GenRoBag':
                self.curr_type = None
                if '_T' in attrs:
                    self.curr_type = attrs.pop('_T')
                elif 'T' in attrs:
                    self.curr_type = attrs.pop('T')

                if not self.curr_array:
                    new_item: Any = Bag()
                    if self.curr_type and self.curr_type.startswith('A'):
                        self.curr_array = tag_label
                        new_item = []
                    self.bags.append((new_item, attrs))
            else:
                # Plain XML format
                if ''.join(self.value_list).strip():
                    value = self._get_value()
                    if value:
                        self.bags[-1][0].set_item('_', value)
                self.bags.append((Bag(), attrs))

        self.value_list = []

    def characters(self, s: str) -> None:
        self.value_list.append(s)

    def endElement(self, tag_label: str) -> None:
        value = self._get_value(dtype=self.curr_type)
        self.value_list = []
        dest = self.bags[-1][0]

        if self.format == 'GenRoBag' and value:
            value = self._decode_value_with_type(value, self.curr_type)

        if self.curr_array:
            # Handle array
            if self.curr_array != tag_label:
                # Array content
                if value == '':
                    value = self._decode_value_with_type('', self.curr_type)
                dest.append(value)
            else:
                # Array enclosure
                self.curr_array = None
                curr, attrs = self.bags.pop()
                self._set_into_parent(tag_label, curr, attrs)
        else:
            curr, attrs = self.bags.pop()
            if value or value == 0 or value == datetime.time(0, 0):
                if curr:
                    if isinstance(value, str):
                        value = value.strip()
                    if value:
                        curr.set_item('_', value)
                else:
                    curr = value

            if not curr and curr != 0 and curr != datetime.time(0, 0):
                if self.empty:
                    curr = self.empty()
                else:
                    curr = self._decode_value_with_type('', self.curr_type)

            self._set_into_parent(tag_label, curr, attrs)

    def _set_into_parent(self, tag_label: str, curr: Any, attrs: dict) -> None:
        """Add node to parent bag."""
        dest = self.bags[-1][0]

        # Use _tag attribute as label if present
        if '_tag' in attrs:
            tag_label = attrs.pop('_tag')

        # Handle duplicate labels (always active - Bag doesn't allow duplicates)
        dup_manager = getattr(dest, '__dupmanager', None)
        if dup_manager is None:
            dup_manager = {}
            setattr(dest, '__dupmanager', dup_manager)
        cnt = dup_manager.get(tag_label, 0)
        dup_manager[tag_label] = cnt + 1
        if cnt:
            tag_label = f'{tag_label}_{cnt}'

        if attrs:
            if self.attr_in_value:
                from .bag import Bag
                # Store attributes as structured data
                if isinstance(curr, Bag):
                    curr['__attributes'] = Bag(attrs)
                else:
                    value = curr
                    curr = Bag()
                    curr['__attributes'] = Bag(attrs)
                    if value:
                        curr['__content'] = value
                dest.set_item(tag_label, curr)
            else:
                dest.set_item(tag_label, curr, _attributes=attrs)
        else:
            dest.set_item(tag_label, curr)
