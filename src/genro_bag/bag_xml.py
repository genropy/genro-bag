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

        # Pretty print (before adding header)
        if self.pretty:
            content = self._prettify(content)

        # Add XML declaration
        if self.doc_header is True:
            content = f"<?xml version='1.0' encoding='{self.encoding}'?>\n{content}"
        elif isinstance(self.doc_header, str):
            content = f'{self.doc_header}\n{content}'

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
            attrs_parts.append(f'_tag={saxutils.quoteattr(original_tag)}')

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

        text = saxutils.escape(str(value))
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
            return '_none_', None

        # If tag has a known namespace prefix, keep it as-is
        if ':' in tag:
            prefix = tag.split(':')[0]
            if prefix in namespaces:
                return tag, None

        sanitized = re.sub(r'_+', '_', _INVALID_XML_TAG_CHARS.sub('_', tag))

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
        raise_on_error: bool = False,
    ):
        """Initialize the parser.

        Args:
            empty: Factory function for empty element values.
            raise_on_error: If True, raise on TYTX conversion errors.
                If False (default), use '**INVALID::{type}**' placeholder.
        """
        super().__init__()
        self.empty = empty
        self.raise_on_error = raise_on_error

    @classmethod
    def parse(
        cls,
        source: str | bytes,
        empty: Callable[[], Any] | None = None,
        raise_on_error: bool = False,
    ) -> Bag:
        """Parse XML to Bag.

        Args:
            source: XML string or bytes to parse.
            empty: Factory function for empty element values.
            raise_on_error: If True, raise on TYTX conversion errors.
                If False (default), use '**INVALID::{type}**' placeholder.

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

        handler = cls(empty=empty, raise_on_error=raise_on_error)
        sax.parseString(source, handler)

        result = handler.bags[0][0]
        if handler.legacy_mode:
            result = result['GenRoBag']
        if result is None:
            result = Bag()
        return result

    def startDocument(self) -> None:
        from .bag import Bag
        self.bags: list[tuple[Any, dict, str | None]] = [(Bag(), None, None)]
        self.value_list: list[str] = []
        self.legacy_mode: bool = False

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

    def startElement(self, tag_label: str, attributes: Any) -> None:
        from .bag import Bag
        attrs = {str(k): from_tytx(saxutils.unescape(v)) for k, v in attributes.items()}
        curr_type: str | None = None

        if len(self.bags) == 1:
            # First element - detect legacy format
            self.legacy_mode = tag_label.lower() == 'genrobag'
        else:
            if self.legacy_mode:
                curr_type = attrs.pop('_T', None)
            elif ''.join(self.value_list).strip():
                # Plain XML - handle mixed content
                value = self._get_value()
                if value:
                    self.bags[-1][0].set_item('_', value)

        self.bags.append((Bag(), attrs, curr_type))

        self.value_list = []

    def characters(self, s: str) -> None:
        self.value_list.append(s)

    def endElement(self, tag_label: str) -> None:
        curr, attrs, curr_type = self.bags.pop()
        value = self._get_value(dtype=curr_type)
        self.value_list = []

        if self.legacy_mode and value and curr_type and curr_type != 'T':
            try:
                value = from_tytx(f'{value}::{curr_type}')
            except Exception:
                if self.raise_on_error:
                    raise
                value = f'**INVALID::{curr_type}**'

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
            elif curr_type and curr_type != 'T':
                try:
                    curr = from_tytx(f'::{curr_type}')
                except Exception:
                    if self.raise_on_error:
                        raise
                    curr = f'**INVALID::{curr_type}**'
            else:
                curr = ''

        self._set_into_parent(tag_label, curr, attrs)

    def _set_into_parent(self, tag_label: str, curr: Any, attrs: dict) -> None:
        """Add node to parent bag."""
        dest = self.bags[-1][0]

        # Use _tag attribute as label if present
        tag_label = attrs.pop('_tag', tag_label)

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
            dest.set_item(tag_label, curr, _attributes=attrs)
        else:
            dest.set_item(tag_label, curr)
