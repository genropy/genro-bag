# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag serialization module.

This module provides functions to serialize and deserialize Bag
hierarchies to/from various formats:

- **TYTX**: Type-preserving format with JSON or MessagePack transport
- **XML**: Standard XML with optional type preservation (legacy or TYTX suffix)
- **JSON**: JSON format with optional type preservation

TYTX Transports:
    - 'json': JSON string (.bag.json extension)
    - 'msgpack': Binary MessagePack (.bag.mp extension)

XML Formats:
    - Legacy mode (legacy=True): Uses _T attribute for types (GenRoBag format)
    - TYTX mode (legacy=False): Uses ::TYPE suffix in values

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.serialization import to_tytx, from_tytx
    >>>
    >>> bag = Bag()
    >>> bag['name'] = 'test'
    >>> bag['count'] = 42
    >>>
    >>> # TYTX serialization (JSON)
    >>> data = to_tytx(bag)
    >>> bag2 = from_tytx(data)
"""

from __future__ import annotations

import datetime
import json
import os
import re
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal
from xml.sax import saxutils

if TYPE_CHECKING:
    from .bag import Bag

# Regex for XML illegal characters that need escaping
REGEX_XML_ILLEGAL = re.compile(r'<|>|&')


def node_flattener(
    bag: Bag,
    path_registry: dict[int, str] | None = None,
) -> Iterator[tuple[str | int | None, str, str | None, Any, dict]]:
    """Expand each node into (parent, label, tag, value, attr) tuples.

    Consumes walk() and transforms each node into a flat tuple suitable
    for TYTX serialization. Values are Python raw types - TYTX encoding
    is done later by the serializer.

    Special value markers:
        - "::X" for Bag (branch nodes)
        - "::NN" for None values

    Args:
        bag: The Bag to flatten.
        path_registry: Optional dict to enable compact mode.
            - If None: parent is path string (normal mode)
            - If dict: parent is numeric code, dict populated with
              {code: full_path} mappings for branches

    Yields:
        tuple: (parent, label, tag, value, attr) where:
            - parent: path string or int code (None for root-level)
            - label: node's label
            - tag: node's tag or None
            - value: "::X" for Bag, "::NN" for None, else raw value
            - attr: dict of node attributes (copy)

    Example:
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> bag['config'] = Bag()
        >>> bag['config.host'] = 'localhost'
        >>> for row in node_flattener(bag):
        ...     print(row)
        ('', 'name', None, 'test', {})
        ('', 'config', None, '::X', {})
        ('config', 'host', None, 'localhost', {})
    """
    from .bag import Bag

    compact = path_registry is not None
    if compact:
        path_to_code: dict[str, int] = {}
        code_counter = 0

    for path, node in bag.walk():
        parent_path = path.rsplit(".", 1)[0] if "." in path else ""

        # Value encoding
        if isinstance(node.value, Bag):
            value = "::X"
        elif node.value is None:
            value = "::NN"
        else:
            value = node.value

        attr = dict(node.attr) if node.attr else {}

        if compact:
            parent_ref = path_to_code.get(parent_path) if parent_path else None
            yield (parent_ref, node.label, node.tag, value, attr)

            if isinstance(node.value, Bag):
                path_to_code[path] = code_counter
                path_registry[code_counter] = path
                code_counter += 1
        else:
            yield (parent_path, node.label, node.tag, value, attr)


def to_tytx(
    bag: Bag,
    transport: Literal["json", "msgpack"] = "json",
    filename: str | None = None,
    compact: bool = False,
) -> str | bytes | None:
    """Serialize a Bag to TYTX format.

    Converts the entire Bag hierarchy into a flat list of row tuples,
    then encodes it using TYTX which preserves Python types (Decimal,
    date, datetime, time) in the wire format.

    Args:
        bag: The Bag to serialize.
        transport: Output format:
            - 'json': JSON string (.bag.json). Human-readable, compresses well.
            - 'msgpack': Binary bytes (.bag.mp). Smallest, fastest.
        filename: Optional filename to write to. Extension is added
            automatically based on transport (.bag.json, .bag.mp).
            If None, returns the serialized data.
        compact: Serialization mode:
            - False (default): Parent paths as full strings ('a.b.c').
            - True: Parent paths as numeric codes (0, 1, 2...).

    Returns:
        If filename is None: serialized data (str or bytes).
        If filename is provided: None (data written to file).

    Raises:
        ImportError: If genro-tytx package is not installed.

    Example:
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> bag['count'] = 42
        >>>
        >>> # Get serialized string
        >>> data = to_tytx(bag)
        >>>
        >>> # Write to file (creates config.bag.json)
        >>> to_tytx(bag, filename='config')
        >>>
        >>> # MessagePack binary
        >>> to_tytx(bag, transport='msgpack', filename='data')
    """
    from genro_tytx import to_tytx as tytx_encode
    if compact:
        paths: dict[int, str] = {}
        rows = list(node_flattener(bag, path_registry=paths))
        paths_str = {str(k): v for k, v in paths.items()}
        data = {"rows": rows, "paths": paths_str}
    else:
        rows = list(node_flattener(bag))
        data = {"rows": rows}

    # genro_tytx uses transport=None for JSON
    tytx_transport = None if transport == "json" else transport
    result = tytx_encode(data, transport=tytx_transport)

    if filename:
        ext_map = {"json": ".bag.json", "msgpack": ".bag.mp"}
        ext = ext_map[transport]
        if not filename.endswith(ext):
            filename = filename + ext

        # Remove ::JS suffix for file (extension identifies format)
        if isinstance(result, str) and result.endswith("::JS"):
            result = result[:-4]

        mode = "wb" if transport == "msgpack" else "w"
        with open(filename, mode) as f:
            f.write(result)
        return None

    return result


def from_tytx(
    data: str | bytes,
    transport: Literal["json", "msgpack"] = "json",
) -> Bag:
    """Deserialize Bag from TYTX format.

    Reconstructs a complete Bag hierarchy from TYTX-encoded data.

    Args:
        data: Serialized data from to_tytx().
        transport: Input format matching how data was serialized:
            - 'json': JSON string
            - 'msgpack': Binary bytes

    Returns:
        Reconstructed Bag with all nodes, values, and attributes.

    Raises:
        ImportError: If genro-tytx package is not installed.
    """
    from genro_tytx import from_tytx as tytx_decode

    from .bag import Bag

    parsed = tytx_decode(data, transport=transport if transport != "json" else None)
    rows = parsed["rows"]
    paths_raw = parsed.get("paths")
    code_to_path: dict[int, str] | None = (
        {int(k): v for k, v in paths_raw.items()} if paths_raw else None
    )

    bag = Bag()
    path_to_bag: dict[str, Bag] = {"": bag}

    for row in rows:
        parent_ref, label, tag, value, attr = row

        # Resolve parent path
        if code_to_path is not None:
            parent_path = code_to_path.get(parent_ref, "") if parent_ref is not None else ""
        else:
            parent_path = parent_ref if parent_ref else ""

        parent_bag = path_to_bag.get(parent_path, bag)
        full_path = f"{parent_path}.{label}" if parent_path else label

        # Decode value
        if value == "::X":
            child_bag = Bag()
            parent_bag.set_item(label, child_bag, _attributes=attr)
            path_to_bag[full_path] = child_bag
        elif value == "::NN":
            parent_bag.set_item(label, None, _attributes=attr)
        else:
            parent_bag.set_item(label, value, _attributes=attr)

        # Set tag if present
        if tag:
            node = parent_bag.get_node(label)
            if node:
                node.tag = tag

    return bag


# ==================== XML Legacy Serialization ====================

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
        >>> from genro_bag.serialization import XmlLegacy
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
    ) -> Bag:
        """Deserialize XML in legacy GenRoBag format to Bag.

        Args:
            source: XML string or bytes to parse.

        Returns:
            Deserialized Bag.
        """
        # TODO: Implement
        raise NotImplementedError("XmlLegacy.from_xml not yet implemented")

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


def to_xml(
    bag: Bag,
    filename: str | None = None,
    encoding: str = "UTF-8",
    # Typing
    typed: bool = True,
    legacy: bool = False,
    # Structure
    root_tag: str = "GenRoBag",
    doc_header: bool | str | None = None,
    # Formatting
    pretty: bool = False,
    html: bool = False,
    # Callbacks
    translate_cb: Callable[[str], str] | None = None,
) -> str | None:
    """Serialize Bag to XML string.

    Converts the Bag hierarchy into an XML document. Tag names are sanitized
    to be valid XML (invalid chars replaced with '_', original saved in _tag
    attribute if different).

    Args:
        bag: The Bag to serialize.
        filename: Optional file path to write to. If provided, returns None.
            If filename ends with .html or .htm, html=True is auto-detected.
        encoding: XML encoding (default UTF-8).
        typed: Type preservation mode:
            - True (default, Genropy format): Preserve types on values and
              attributes, mark Bag nodes with type, wrap in root element.
            - False (pure XML): No type information, no wrapper root.
        legacy: Type encoding format (only when typed=True):
            - True: Use _T attribute for types (GenRoBag legacy format)
            - False: Use TYTX ::TYPE suffix in values (modern format)
        root_tag: Root element tag name (default 'GenRoBag', used only if typed=True).
        doc_header: XML declaration:
            - None/False: No declaration
            - True: Auto-generate with encoding
            - str: Custom declaration string
        pretty: If True, format with indentation.
        html: HTML output mode:
            - True: Use 'tag' attribute as XML tag name, auto-close only
              HTML void elements (br, img, meta, hr, input, link, etc.).
              Implies typed=False.
            - False (default, XML): Use label as tag name, auto-close all
              empty tags.
        translate_cb: Optional callback for translating text values.

    Returns:
        XML string if filename is None, else None (written to file).

    Example:
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> bag['count'] = 42
        >>>
        >>> # Default Genropy format (typed=True, TYTX suffix)
        >>> to_xml(bag)
        '<GenRoBag><name>test</name><count>42::L</count></GenRoBag>'
        >>>
        >>> # Legacy format (typed=True, _T attribute)
        >>> to_xml(bag, legacy=True)
        '<GenRoBag><name>test</name><count _T="L">42</count></GenRoBag>'
        >>>
        >>> # Pure XML (typed=False)
        >>> to_xml(bag, typed=False)
        '<name>test</name><count>42</count>'
        >>>
        >>> # HTML mode (auto-detect from filename)
        >>> to_xml(bag, filename='page.html')  # html=True auto-detected
    """
    # TODO: Implement
    raise NotImplementedError("to_xml not yet implemented")


def from_xml(
    source: str | bytes,
    # Type decoding
    typed: bool = True,
    legacy: bool | None = None,
    # Parsing options
    empty: Callable[[], Any] | None = None,
    attr_in_value: bool = False,
) -> Bag:
    """Deserialize XML to Bag.

    Parses XML and reconstructs a Bag hierarchy. Duplicate tag names are
    automatically handled by appending _1, _2, etc. suffixes.

    Args:
        source: XML string or bytes to parse.
        typed: If True, decode type information from values/attributes.
        legacy: Type decoding mode:
            - None: Auto-detect (look for _T attributes)
            - True: Force legacy mode (_T attribute)
            - False: Force TYTX mode (::TYPE suffix)
        empty: Factory function for empty element values.
        attr_in_value: If True, store XML attributes as structured data:
            - Creates a Bag with '__attributes' (Bag of attrs) and '__content' (value)
            - If False (default), attributes go to node.attr

    Returns:
        Deserialized Bag.

    Example:
        >>> xml = '<root><item>a</item><item>b</item></root>'
        >>> bag = from_xml(xml)
        >>> list(bag['root'].keys())
        ['item', 'item_1']
    """
    # TODO: Implement
    raise NotImplementedError("from_xml not yet implemented")


# ==================== JSON Serialization ====================


def to_json(
    bag: Bag,
    typed: bool = True,
    nested: bool = False,
) -> str:
    """Serialize Bag to JSON string.

    Args:
        bag: The Bag to serialize.
        typed: If True, include type information (TYTX encoding).
        nested: If True, use nested object format instead of flat.

    Returns:
        JSON string representation.

    Example:
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> to_json(bag)
        '[{"label": "name", "value": "test"}]'
    """
    # TODO: Implement
    raise NotImplementedError("to_json not yet implemented")


def from_json(
    source: str,
    list_joiner: str | None = None,
) -> Bag:
    """Deserialize JSON to Bag.

    Args:
        source: JSON string to parse.
        list_joiner: If provided, join list values with this string.

    Returns:
        Deserialized Bag.
    """
    # TODO: Implement
    raise NotImplementedError("from_json not yet implemented")
