# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagParser mixin - classmethods for deserializing from various formats.

This module provides the BagParser mixin class containing from_xml, from_tytx,
and from_json classmethods. The Bag class inherits from this mixin to get
deserialization capabilities without circular imports.

All methods are classmethods. When called as Bag.from_json(data), cls is the Bag
class, so cls() creates a new Bag instance.
"""

from __future__ import annotations

import datetime
import os
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, cast
from xml import sax
from xml.sax import saxutils

from genro_tytx import from_tytx as tytx_decode

if TYPE_CHECKING:
    from .bag import Bag


# Regex for empty checks
_EMPTY_CONTENT_RE = re.compile(r"^\s*$")


class BagParser:
    """Mixin providing deserialization classmethods for Bag.

    Contains:
        - from_xml: Parse XML to Bag (SAX-based, auto-detects legacy format)
        - from_tytx: Parse TYTX format (JSON or MessagePack transport)
        - from_json: Parse JSON to Bag (with TYTX type decoding)
    """

    # ==================== from_xml ====================

    @classmethod
    def from_xml(
        cls,
        source: str | bytes,
        empty: Callable[[], Any] | None = None,
        raise_on_error: bool = False,
        tag_attribute: str | None = None,
    ) -> Bag:
        """Deserialize from XML format.

        Automatically detects and handles legacy GenRoBag format:
        - Decodes `_T` attribute for value types (L=int, R=float, D=date, etc.)
        - Decodes `::TYPE` suffix in attribute values (TYTX encoding)
        - Handles `<GenRoBag>` root wrapper element (unwraps automatically)

        For plain XML without type markers, values remain as strings.
        Supports environment variable substitution for {GNR_*} placeholders.

        Args:
            source: XML string or bytes to parse.
            empty: Factory function for empty element values. Called when an
                element has no content and no type marker.
            raise_on_error: If True, raise exceptions for type conversion errors.
                If False (default), invalid values become '**INVALID::TYPE**' markers.
            tag_attribute: If specified, use this attribute's value as the node
                label instead of the XML tag name. Dotted values create nested
                structure (e.g., 'section.elem' becomes section/elem path).

        Returns:
            Bag: Reconstructed Bag hierarchy.

        Example:
            >>> # Plain XML - each element becomes a node
            >>> bag = Bag.from_xml('<root><name>test</name></root>')
            >>> bag['root.name']
            'test'

            >>> # Legacy GenRoBag format (auto-detected by root element name)
            >>> bag = Bag.from_xml('<GenRoBag><count _T="L">42</count></GenRoBag>')
            >>> bag['count']  # GenRoBag wrapper is unwrapped automatically
            42
            >>> type(bag['count'])  # _T="L" converts to int
            <class 'int'>

            >>> # Use attribute as path (creates nested structure)
            >>> xml = '<grammar><define name="section.elem"/></grammar>'
            >>> bag = Bag.from_xml(xml, tag_attribute='name')
            >>> 'section' in bag['grammar']  # dot creates hierarchy
            True
        """
        handler = _BagXmlHandler(
            cls, empty=empty, raise_on_error=raise_on_error, tag_attribute=tag_attribute
        )
        if isinstance(source, bytes):
            source = source.decode()

        # Replace environment variables (GNR_*)
        for k in os.environ:
            if k.startswith("GNR_"):
                source = source.replace(f"{{{k}}}", os.environ[k])

        sax.parseString(source, handler)

        result = handler.bags[0][0]
        if handler.legacy_mode:
            result = result["GenRoBag"]
        if result is None:
            result = cls()
        return cast("Bag", result)

    # ==================== from_tytx ====================

    @classmethod
    def from_tytx(
        cls,
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
        parsed = tytx_decode(data, transport=transport if transport != "json" else None)
        rows = parsed["rows"]
        paths_raw = parsed.get("paths")
        code_to_path: dict[int, str] | None = (
            {int(k): v for k, v in paths_raw.items()} if paths_raw else None
        )

        bag = cls()
        path_to_bag: dict[str, Any] = {"": bag}

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
                child_bag = cls()
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

        return cast("Bag", bag)

    # ==================== from_json ====================

    @classmethod
    def from_json(
        cls,
        source: str | dict | list,
        list_joiner: str | None = None,
    ) -> Bag:
        """Deserialize JSON to Bag.

        Accepts JSON string, dict, or list. Recursively converts nested
        structures to Bag hierarchy. Uses TYTX for parsing (orjson + type decoding).

        Args:
            source: JSON string, dict or list to parse.
            list_joiner: If provided, join string lists with this separator.

        Returns:
            Deserialized Bag.
        """
        if isinstance(source, str):
            source = tytx_decode(source)

        if not isinstance(source, (list, dict)):
            # Wrap scalar in a dict
            source = {"value": source}

        return cast("Bag", cls._from_json_recursive(source, list_joiner))

    @classmethod
    def _from_json_recursive(
        cls,
        data: dict | list | Any,
        list_joiner: str | None = None,
        parent_key: str | None = None,
    ) -> Any:
        """Recursively convert JSON data to Bag."""
        if isinstance(data, list):
            if not data:
                return cls()

            # Check if list items have 'label' key (Bag node format)
            if isinstance(data[0], dict) and "label" in data[0]:
                result = cls()
                for item in data:
                    label = item.get("label")
                    value = cls._from_json_recursive(item.get("value"), list_joiner)
                    attr = item.get("attr", {})
                    result.set_item(label, value, _attributes=attr)  # type: ignore[attr-defined]
                return result

            # String list with joiner
            if list_joiner and all(isinstance(r, str) for r in data):
                return list_joiner.join(data)

            # Generic list -> Bag with prefix from parent key
            result = cls()
            prefix = parent_key if parent_key else "r"
            for n, v in enumerate(data):
                result.set_item(f"{prefix}_{n}", cls._from_json_recursive(v, list_joiner))  # type: ignore[attr-defined]
            return result

        if isinstance(data, dict):
            if not data:
                return cls()
            result = cls()
            for k, v in data.items():
                result.set_item(k, cls._from_json_recursive(v, list_joiner, parent_key=k))  # type: ignore[attr-defined]
            return result

        # Scalar value
        return data


# =============================================================================
# Internal SAX Handler for XML parsing
# =============================================================================


class _BagXmlHandler(sax.handler.ContentHandler):
    """SAX handler for parsing XML into Bag.

    Uses a stack-based approach where each XML element creates a new Bag
    that gets populated with child elements. When an element closes, it's
    added to its parent Bag.

    Attributes:
        bag_class: The Bag class to instantiate for nested structures.
        empty: Optional factory for empty element values.
        raise_on_error: If True, raise on type conversion errors.
        tag_attribute: If set, use this attribute's value as node label.
        bags: Stack of (bag, attrs, type) tuples during parsing.
        value_list: Accumulator for character data between tags.
        legacy_mode: True if parsing GenRoBag format with _T type markers.
    """

    def __init__(
        self,
        bag_class: type,
        empty: Callable[[], Any] | None = None,
        raise_on_error: bool = False,
        tag_attribute: str | None = None,
    ):
        super().__init__()
        self.bag_class = bag_class
        self.empty = empty
        self.raise_on_error = raise_on_error
        self.tag_attribute = tag_attribute

    def startDocument(self) -> None:
        """Initialize parsing state with root Bag on stack."""
        self.bags: list[tuple[Any, dict | None, str | None]] = [(self.bag_class(), None, None)]
        self.value_list: list[str] = []
        self.legacy_mode: bool = False

    def _get_value(self, dtype: str | None = None) -> str:
        """Join accumulated character data, strip newlines, unescape XML entities."""
        if self.value_list:
            if self.value_list[0] == "\n":
                self.value_list[:] = self.value_list[1:]
            if self.value_list and self.value_list[-1] == "\n":
                self.value_list.pop()
        value = "".join(self.value_list)
        if dtype != "BAG":
            value = saxutils.unescape(value)
        return value

    def startElement(self, tag_label: str, attributes: Any) -> None:
        """Push new Bag onto stack, detect legacy format on first element."""
        attrs = {str(k): tytx_decode(saxutils.unescape(v)) for k, v in attributes.items()}
        curr_type: str | None = None

        if len(self.bags) == 1:
            # First element - detect legacy format
            self.legacy_mode = tag_label.lower() == "genrobag"
        else:
            if self.legacy_mode:
                curr_type = attrs.pop("_T", None)
            elif "".join(self.value_list).strip():
                # Plain XML - handle mixed content
                value = self._get_value()
                if value:
                    self.bags[-1][0].set_item("_", value)

        self.bags.append((self.bag_class(), attrs, curr_type))

        self.value_list = []

    def characters(self, s: str) -> None:
        """Accumulate text content between tags."""
        self.value_list.append(s)

    def endElement(self, tag_label: str) -> None:
        """Pop Bag from stack, convert value if typed, add to parent."""
        curr, attrs, curr_type = self.bags.pop()
        value = self._get_value(dtype=curr_type)
        self.value_list = []

        if self.legacy_mode and value and curr_type and curr_type != "T":
            try:
                value = tytx_decode(f"{value}::{curr_type}")
            except Exception:
                if self.raise_on_error:
                    raise
                value = f"**INVALID::{curr_type}**"

        if value or value == 0 or value == datetime.time(0, 0):
            if curr:
                if isinstance(value, str):
                    value = value.strip()
                if value:
                    curr.set_item("_", value)
            else:
                curr = value

        if not curr and curr != 0 and curr != datetime.time(0, 0):
            if self.empty:
                curr = self.empty()
            elif curr_type and curr_type != "T":
                try:
                    curr = tytx_decode(f"::{curr_type}")
                except Exception:
                    if self.raise_on_error:
                        raise
                    curr = f"**INVALID::{curr_type}**"
            else:
                curr = ""

        self._set_into_parent(tag_label, curr, attrs or {})

    def _set_into_parent(self, tag_label: str, curr: Any, attrs: dict) -> None:
        """Add node to parent Bag, handling label from attrs and duplicates."""
        dest = self.bags[-1][0]

        # Use _tag attribute as label if present, keep original as xml_tag
        original_xml_tag = tag_label
        tag_label = attrs.pop("_tag", tag_label)

        # Use tag_attribute value as label if specified (creates nested structure with dots)
        if self.tag_attribute and self.tag_attribute in attrs:
            tag_label = attrs.pop(self.tag_attribute)

        # Handle duplicate labels (always active - Bag doesn't allow duplicates)
        dup_manager = getattr(dest, "__dupmanager", None)
        if dup_manager is None:
            dup_manager = {}
            setattr(dest, "__dupmanager", dup_manager)
        cnt = dup_manager.get(tag_label, 0)
        dup_manager[tag_label] = cnt + 1
        if cnt:
            tag_label = f"{tag_label}_{cnt}"

        if attrs:
            node = dest.set_item(tag_label, curr, _attributes=attrs)
        else:
            node = dest.set_item(tag_label, curr)

        # Set xml_tag for XML serialization
        node.xml_tag = original_xml_tag
