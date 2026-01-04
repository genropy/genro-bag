# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML Legacy serialization module.

This module provides the XmlLegacy class for serializing and deserializing
Bag hierarchies to/from XML in the legacy GenRoBag format.

The legacy format uses:
- `_T` attribute for value types (e.g., `<count _T="L">42</count>`)
- `::TYPE` suffix for attribute values (TYTX encoding)
- `<GenRoBag>` as root wrapper element
"""

from __future__ import annotations

import datetime
import json
import os
import re
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from xml import sax
from xml.sax import saxutils

if TYPE_CHECKING:
    from .bag import Bag

# Regex for XML illegal characters that need escaping
REGEX_XML_ILLEGAL = re.compile(r'<|>|&')

# Serializable types for omitUnknownTypes filter
_SERIALIZABLE_TYPES = (
    bytes, str, int, float, Decimal, bool, type(None),
    datetime.date, datetime.time, datetime.datetime,
    list, tuple, dict,
)


class XmlLegacy:
    """XML serializer/deserializer in legacy GenRoBag format.

    This class replicates the original gnrbagxml.py behavior for backward
    compatibility with existing Genropy code.

    The legacy format uses:
    - `_T` attribute for value types (e.g., `<count _T="L">42</count>`)
    - `::TYPE` suffix for attribute values (TYTX encoding)
    - `<GenRoBag>` as root wrapper element

    Example:
        >>> from genro_bag import Bag
        >>> from genro_bag.xml_legacy import XmlLegacy
        >>>
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> bag['count'] = 42
        >>>
        >>> xml = XmlLegacy.to_xml(bag)
        >>> bag2 = XmlLegacy.from_xml(xml)
    """

    # ==================== Public API ====================

    @classmethod
    def to_xml(
        cls,
        bag: Bag,
        filename: str | None = None,
        encoding: str = 'UTF-8',
        catalog: Any = None,  # Ignored, uses genro_tytx
        typeattrs: bool = True,
        typevalue: bool = True,
        addBagTypeAttr: bool = True,
        output_encoding: str | None = None,
        unresolved: bool = False,
        autocreate: bool = False,
        docHeader: bool | str | None = None,
        self_closed_tags: list[str] | None = None,
        translate_cb: Callable[[str], str] | None = None,
        omitUnknownTypes: bool = False,
        omitRoot: bool = False,
        forcedTagAttr: str | None = None,
        mode4d: bool = False,
        pretty: bool = False,
    ) -> str:
        """Serialize Bag to XML in legacy GenRoBag format.

        This method replicates the original gnrbagxml.py BagToXml.build() behavior
        for backward compatibility with existing Genropy code.

        Args:
            bag: The Bag to serialize.
            filename: Optional file path to write to.
            encoding: XML encoding (default UTF-8).
            catalog: Ignored (kept for API compatibility, uses genro_tytx).
            typeattrs: If True, include type info in attributes (::TYPE suffix).
            typevalue: If True, include type info in values (_T attribute).
            addBagTypeAttr: If True, add _T="BAG" for empty Bag nodes.
            output_encoding: Optional output encoding for values.
            unresolved: If True, serialize resolver info instead of resolving.
            autocreate: If True, create directories for filename.
            docHeader: XML declaration (True=auto, str=custom, None/False=none).
            self_closed_tags: List of tag names to self-close when empty.
            translate_cb: Optional callback for translating text values.
            omitUnknownTypes: If True, omit attributes with non-serializable types.
            omitRoot: If True, omit the <GenRoBag> root wrapper.
            forcedTagAttr: If set, use this attribute's value as the XML tag name.
            mode4d: If True, enable 4D array serialization mode.
            pretty: If True, format output with indentation.

        Returns:
            XML string representation.
        """
        # Build context for nested calls
        ctx = cls._Context(
            typeattrs=typeattrs,
            typevalue=typevalue,
            addBagTypeAttr=addBagTypeAttr,
            output_encoding=output_encoding,
            unresolved=unresolved,
            self_closed_tags=self_closed_tags or [],
            translate_cb=translate_cb,
            omitUnknownTypes=omitUnknownTypes,
            forcedTagAttr=forcedTagAttr,
            mode4d=mode4d,
        )

        # Build result
        result = ''
        if docHeader is not False:
            result = docHeader if isinstance(docHeader, str) else f"<?xml version='1.0' encoding='{encoding}'?>\n"

        if omitRoot:
            result = result + cls._bag_to_xml_block(bag, ctx, namespaces=[])
        else:
            result = result + cls._build_tag(
                'GenRoBag',
                cls._bag_to_xml_block(bag, ctx, namespaces=[]),
                None,
                '',
                ctx,
                xml_mode=True,
                localize=False,
                namespaces=[],
            )

        if pretty:
            from xml.dom.minidom import parseString
            result = parseString(result).toprettyxml()
            result = result.replace('\t\n', '').replace('\t\n', '')

        result_bytes = result.encode(encoding, 'replace') if isinstance(result, str) else result

        if filename:
            if hasattr(filename, 'write'):
                filename.write(result_bytes)
            else:
                if autocreate:
                    dirname = os.path.dirname(filename)
                    if dirname and not os.path.exists(dirname):
                        os.makedirs(dirname)
                with open(filename, 'wb') as output:
                    output.write(result_bytes)

        return result_bytes.decode(encoding)

    @classmethod
    def from_xml(
        cls,
        source: str | bytes,
        empty: Callable[[], Any] | None = None,
        avoid_dup_label: bool = False,
        attr_in_value: bool = False,
    ) -> Bag:
        """Deserialize XML in legacy GenRoBag format to Bag.

        Args:
            source: XML string or bytes to parse.
            empty: Factory function for empty element values.
            avoid_dup_label: If True, append _N suffix to duplicate labels.
            attr_in_value: If True, store attributes as structured data
                with __attributes and __content keys.

        Returns:
            Deserialized Bag.
        """
        from .bag import Bag

        if isinstance(source, bytes):
            source = source.decode()

        # Replace environment variables
        for k in os.environ:
            if k.startswith('GNR_'):
                source = source.replace('{%s}' % k, os.environ[k])

        handler = _SaxImporter(
            bag_cls=Bag,
            empty=empty,
            avoid_dup_label=avoid_dup_label,
            attr_in_value=attr_in_value,
        )
        sax.parseString(source, handler)

        result = handler.bags[0][0]
        if handler.format == 'GenRoBag':
            result = result['GenRoBag']
        if result is None:
            result = Bag()
        return result

    # ==================== Internal Context ====================

    class _Context:
        """Context for XML legacy serialization."""

        __slots__ = (
            'typeattrs', 'typevalue', 'addBagTypeAttr', 'output_encoding',
            'unresolved', 'self_closed_tags', 'translate_cb', 'omitUnknownTypes',
            'forcedTagAttr', 'mode4d',
        )

        def __init__(
            self,
            typeattrs: bool,
            typevalue: bool,
            addBagTypeAttr: bool,
            output_encoding: str | None,
            unresolved: bool,
            self_closed_tags: list[str],
            translate_cb: Callable[[str], str] | None,
            omitUnknownTypes: bool,
            forcedTagAttr: str | None,
            mode4d: bool,
        ):
            self.typeattrs = typeattrs
            self.typevalue = typevalue
            self.addBagTypeAttr = addBagTypeAttr
            self.output_encoding = output_encoding
            self.unresolved = unresolved
            self.self_closed_tags = self_closed_tags
            self.translate_cb = translate_cb
            self.omitUnknownTypes = omitUnknownTypes
            self.forcedTagAttr = forcedTagAttr
            self.mode4d = mode4d

    # ==================== Private Helpers ====================

    @staticmethod
    def _is_serializable_attr(value: Any) -> bool:
        """Check if an attribute value is serializable to XML."""
        if isinstance(value, _SERIALIZABLE_TYPES):
            return True
        # Allow callable with specific markers
        if callable(value):
            if hasattr(value, 'is_rpc') or hasattr(value, '__safe__'):
                return True
            if hasattr(value, '__name__') and value.__name__.startswith('rpc_'):
                return True
        return False

    @staticmethod
    def _value_to_text_and_type(
        value: Any,
        translate_cb: Callable[[str], str] | None = None,
    ) -> tuple[str, str]:
        """Convert a value to text representation and type code.

        Returns:
            (text_value, type_code) where type_code is empty for strings.
        """
        from genro_tytx import to_tytx

        if value is None:
            return '', ''
        if isinstance(value, bool):
            text = 'y' if value else ''
            return text, 'B'
        if isinstance(value, str):
            if translate_cb:
                value = translate_cb(value)
            return value, 'T' if value else ''
        # Use genro_tytx for encoding with _force_suffix to get type on all values
        encoded = to_tytx(value, _force_suffix=True)
        if isinstance(encoded, str) and '::' in encoded:
            # Split "value::TYPE" into parts
            text, type_code = encoded.rsplit('::', 1)
            return text, type_code
        # Fallback for unknown types
        return str(value), ''

    @staticmethod
    def _value_to_typed_text(
        value: Any,
        translate_cb: Callable[[str], str] | None = None,
    ) -> str:
        """Convert a value to typed text (value::TYPE format)."""
        from genro_tytx import to_tytx

        if value is None:
            return ''
        if isinstance(value, bool):
            return ('y' if value else '') + '::B'
        if isinstance(value, str):
            if translate_cb:
                value = translate_cb(value)
            return value  # No type suffix for strings
        # Use genro_tytx for encoding with _force_suffix to get type on all values
        encoded = to_tytx(value, _force_suffix=True)
        if isinstance(encoded, str):
            return encoded
        return str(value)

    @classmethod
    def _bag_to_xml_block(cls, bag: Bag, ctx: _Context, namespaces: list[str]) -> str:
        """Convert a Bag to XML block (list of tags joined by newline)."""
        return '\n'.join([cls._node_to_xml_block(node, ctx, namespaces) for node in bag])

    @classmethod
    def _node_to_xml_block(cls, node: Any, ctx: _Context, namespaces: list[str]) -> str:
        """Convert a BagNode to XML block."""
        from .bag import Bag

        nodeattr = dict(node.attr) if node.attr else {}

        # Extract local namespaces from attributes
        local_namespaces = [k[6:] for k in nodeattr if k.startswith('xmlns:')]
        current_namespaces = namespaces + local_namespaces

        # Skip forbidden nodes
        if '__forbidden__' in nodeattr:
            return ''

        # Handle resolver
        if ctx.unresolved and node.resolver is not None and not getattr(node.resolver, '_xmlEager', None):
            if not nodeattr.get('_resolver_name') and hasattr(node.resolver, 'serialize'):
                nodeattr['_resolver'] = json.dumps(node.resolver.serialize())
            if getattr(node.resolver, 'xmlresolved', False):
                value = node.resolver()
                node._value = value
            else:
                value = ''
            if isinstance(node._value, Bag):
                value = cls._bag_to_xml_block(node._value, ctx, namespaces=current_namespaces)
            return cls._build_tag(node.label, value, nodeattr, '', ctx, xml_mode=True, namespaces=current_namespaces)

        node_value = node.value

        # Bag with children
        if isinstance(node_value, Bag) and node_value:
            return cls._build_tag(
                node.label,
                cls._bag_to_xml_block(node_value, ctx, namespaces=current_namespaces),
                nodeattr,
                '',
                ctx,
                xml_mode=True,
                localize=False,
                namespaces=current_namespaces,
            )

        # mode4d array handling
        if ctx.mode4d and node_value and isinstance(node_value, (list, tuple)):
            if node.label[:3] in ('AR_', 'AL_', 'AT_', 'AD_', 'AH_', 'AB_'):
                cls4d = node.label[:2]
            else:
                # Get type code from first element
                _, type_code = cls._value_to_text_and_type(node_value[0])
                cls4d = f'A{type_code}'
            return cls._build_tag(
                node.label,
                '\n'.join([cls._build_tag('C', c, None, '', ctx, namespaces=current_namespaces) for c in node_value]),
                nodeattr,
                cls4d,
                ctx,
                xml_mode=True,
                namespaces=namespaces,
            )

        # Regular value
        return cls._build_tag(node.label, node_value, nodeattr, '', ctx, namespaces=namespaces)

    @classmethod
    def _build_tag(
        cls,
        tag_name: str,
        value: Any,
        attributes: dict | None,
        type_code: str,
        ctx: _Context,
        xml_mode: bool = False,
        localize: bool = True,
        namespaces: list[str] | None = None,
    ) -> str:
        """Build an XML tag string."""
        from .bag import Bag

        namespaces = namespaces or []
        t = type_code

        # Determine type code if not provided
        if not t and value != '':
            if isinstance(value, Bag):
                if ctx.addBagTypeAttr:
                    value, t = '', 'BAG'
                else:
                    value = ''
            else:
                if ctx.mode4d and isinstance(value, Decimal):
                    value = float(value)
                text, t = cls._value_to_text_and_type(
                    value,
                    translate_cb=ctx.translate_cb if localize else None,
                )
                value = text
            try:
                value = str(value)
            except (AttributeError, TypeError):
                pass

        # Process attributes
        if attributes:
            attributes = dict(attributes)

            # Handle forcedTagAttr
            if ctx.forcedTagAttr and ctx.forcedTagAttr in attributes:
                tag_name = attributes.pop(ctx.forcedTagAttr)

            # Handle __flatten__
            if tag_name == '__flatten__':
                return str(value)

            # Filter unknown types
            if ctx.omitUnknownTypes:
                attributes = {k: v for k, v in attributes.items() if cls._is_serializable_attr(v)}

            # Convert attributes to string
            if ctx.typeattrs:
                attr_str = ' '.join([
                    f'{lbl}={saxutils.quoteattr(cls._value_to_typed_text(val, translate_cb=ctx.translate_cb))}'
                    for lbl, val in attributes.items()
                ])
            else:
                attr_str = ' '.join([
                    f'{lbl}={saxutils.quoteattr(str(val) if val is not None else "")}'
                    for lbl, val in attributes.items()
                    if val is not False
                ])
        else:
            attr_str = ''

        # Sanitize tag name
        original_tag = tag_name
        if not tag_name:
            tag_name = '_none_'

        if ':' in original_tag and original_tag.split(':')[0] in namespaces:
            tag_name = original_tag
        else:
            tag_name = re.sub(r'[^\w.]', '_', original_tag, flags=re.ASCII).replace('__', '_')

        if tag_name[0].isdigit():
            tag_name = '_' + tag_name

        # Build opening tag
        if tag_name != original_tag:
            result = f'<{tag_name} _tag={saxutils.quoteattr(saxutils.escape(original_tag))}'
        else:
            result = f'<{tag_name}'

        # Add type attribute
        if ctx.typevalue and t != '' and t != 'T':
            result = f'{result} _T="{t}"'

        # Add other attributes
        if attr_str:
            result = f'{result} {attr_str}'

        # Handle value and closing
        if not xml_mode:
            if not isinstance(value, str):
                value = str(value) if value is not None else ''

            # Handle ::HTML suffix
            if value.endswith('::HTML'):
                value = value[:-6]
            elif REGEX_XML_ILLEGAL.search(value):
                value = saxutils.escape(value)

            if ctx.output_encoding:
                value = value.encode(ctx.output_encoding, 'ignore').decode('utf-8')

        # Self-closing or regular close
        if not value and tag_name in ctx.self_closed_tags:
            result = f'{result}/>'
        else:
            result = f'{result}>{value}</{tag_name}>'

        return result


# ==================== SAX Importer ====================


class _SaxImporter(sax.handler.ContentHandler):
    """SAX handler for parsing legacy GenRoBag XML format."""

    def __init__(
        self,
        bag_cls: type,
        empty: Callable[[], Any] | None = None,
        avoid_dup_label: bool = False,
        attr_in_value: bool = False,
    ):
        super().__init__()
        self.bag_cls = bag_cls
        self.empty = empty
        self.avoid_dup_label = avoid_dup_label
        self.attr_in_value = attr_in_value

    def startDocument(self) -> None:
        self.bags: list[tuple[Any, dict]] = [(self.bag_cls(), None)]
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

    def _decode_attr_value(self, value: str) -> Any:
        """Decode attribute value from TYTX format."""
        from genro_tytx import from_tytx
        return from_tytx(saxutils.unescape(value))

    def _decode_value(self, value: str, type_code: str | None) -> Any:
        """Decode element value using type code."""
        from genro_tytx import from_tytx

        if not value:
            if type_code and type_code != 'T':
                # Empty value with type - decode empty string with type
                return from_tytx(f'::{type_code}')
            return value

        if type_code and type_code != 'T':
            # Has type code - decode with TYTX
            try:
                return from_tytx(f'{value}::{type_code}')
            except Exception:
                return None
        return value

    def startElement(self, tag_label: str, attributes: Any) -> None:
        # Decode attributes
        attrs = {str(k): self._decode_attr_value(v) for k, v in attributes.items()}

        if len(self.bags) == 1:
            # First element - detect format
            if tag_label.lower() == 'genrobag':
                self.format = 'GenRoBag'
            else:
                self.format = 'xml'
            self.bags.append((self.bag_cls(), attrs))
        else:
            if self.format == 'GenRoBag':
                self.curr_type = None
                if '_T' in attrs:
                    self.curr_type = attrs.pop('_T')
                elif 'T' in attrs:
                    self.curr_type = attrs.pop('T')

                if not self.curr_array:
                    new_item: Any = self.bag_cls()
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
                self.bags.append((self.bag_cls(), attrs))

        self.value_list = []

    def characters(self, s: str) -> None:
        self.value_list.append(s)

    def endElement(self, tag_label: str) -> None:
        value = self._get_value(dtype=self.curr_type)
        self.value_list = []
        dest = self.bags[-1][0]

        if self.format == 'GenRoBag' and value:
            value = self._decode_value(value, self.curr_type)

        if self.curr_array:
            # Handle array
            if self.curr_array != tag_label:
                # Array content
                if value == '':
                    value = self._decode_value('', self.curr_type)
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
                    curr = self._decode_value('', self.curr_type)

            self._set_into_parent(tag_label, curr, attrs)

    def _set_into_parent(self, tag_label: str, curr: Any, attrs: dict) -> None:
        """Add node to parent bag."""
        dest = self.bags[-1][0]

        # Use _tag attribute as label if present
        if '_tag' in attrs:
            tag_label = attrs.pop('_tag')

        # Handle duplicate labels
        if self.avoid_dup_label:
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
                # Store attributes as structured data
                if isinstance(curr, self.bag_cls):
                    curr['__attributes'] = self.bag_cls(attrs)
                else:
                    value = curr
                    curr = self.bag_cls()
                    curr['__attributes'] = self.bag_cls(attrs)
                    if value:
                        curr['__content'] = value
                dest.set_item(tag_label, curr)
            else:
                dest.set_item(tag_label, curr, _attributes=attrs)
        else:
            dest.set_item(tag_label, curr)


# Convenience function for backward compatibility
def to_xml_legacy(
    bag: Bag,
    filename: str | None = None,
    encoding: str = 'UTF-8',
    catalog: Any = None,
    typeattrs: bool = True,
    typevalue: bool = True,
    addBagTypeAttr: bool = True,
    output_encoding: str | None = None,
    unresolved: bool = False,
    autocreate: bool = False,
    docHeader: bool | str | None = None,
    self_closed_tags: list[str] | None = None,
    translate_cb: Callable[[str], str] | None = None,
    omitUnknownTypes: bool = False,
    omitRoot: bool = False,
    forcedTagAttr: str | None = None,
    mode4d: bool = False,
    pretty: bool = False,
) -> str:
    """Serialize Bag to XML in legacy GenRoBag format.

    This is a convenience wrapper around XmlLegacy.to_xml().
    See XmlLegacy.to_xml() for full documentation.
    """
    return XmlLegacy.to_xml(
        bag=bag,
        filename=filename,
        encoding=encoding,
        catalog=catalog,
        typeattrs=typeattrs,
        typevalue=typevalue,
        addBagTypeAttr=addBagTypeAttr,
        output_encoding=output_encoding,
        unresolved=unresolved,
        autocreate=autocreate,
        docHeader=docHeader,
        self_closed_tags=self_closed_tags,
        translate_cb=translate_cb,
        omitUnknownTypes=omitUnknownTypes,
        omitRoot=omitRoot,
        forcedTagAttr=forcedTagAttr,
        mode4d=mode4d,
        pretty=pretty,
    )


def from_xml_legacy(
    source: str | bytes,
    empty: Callable[[], Any] | None = None,
    avoid_dup_label: bool = False,
    attr_in_value: bool = False,
) -> Bag:
    """Deserialize XML in legacy GenRoBag format to Bag.

    This is a convenience wrapper around XmlLegacy.from_xml().
    See XmlLegacy.from_xml() for full documentation.
    """
    return XmlLegacy.from_xml(
        source=source,
        empty=empty,
        avoid_dup_label=avoid_dup_label,
        attr_in_value=attr_in_value,
    )
