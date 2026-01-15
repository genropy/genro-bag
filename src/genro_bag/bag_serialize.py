# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagSerializer mixin - instance methods for serializing to various formats.

This module provides the BagSerializer mixin class containing to_xml, to_tytx,
and to_json instance methods. The Bag class inherits from this mixin to get
serialization capabilities without circular imports.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any, Literal
from xml.dom.minidom import parseString
from xml.sax import saxutils

from genro_tytx import to_tytx as tytx_encode

# Regex for sanitizing XML tag names
_INVALID_XML_TAG_CHARS = re.compile(r"[^\w.]", re.ASCII)


class BagSerializer:
    """Mixin providing serialization instance methods for Bag.

    Contains:
        - to_xml: Serialize Bag to XML
        - to_tytx: Serialize Bag to TYTX format (JSON or MessagePack)
        - to_json: Serialize Bag to JSON format
    """

    # ==================== to_xml ====================

    def to_xml(
        self,
        filename: str | None = None,
        encoding: str = "UTF-8",
        doc_header: bool | str | None = None,
        pretty: bool = False,
        self_closed_tags: list[str] | None = None,
    ) -> str | None:
        """Serialize to XML format.

        All values are converted to strings without type information.
        For type-preserving serialization, use to_tytx() instead.

        Args:
            filename: If provided, write to file. If None, return XML string.
            encoding: XML encoding (default 'UTF-8').
            doc_header: XML declaration (True for auto, False/None for none, str for custom).
            pretty: If True, format with indentation.
            self_closed_tags: List of tags to self-close when empty.

        Returns:
            XML string if filename is None, else None.

        Example:
            >>> bag = Bag()
            >>> bag['name'] = 'test'
            >>> bag['count'] = 42
            >>> bag.to_xml()
            '<name>test</name><count>42</count>'
        """
        content = self._bag_to_xml(namespaces=[], self_closed_tags=self_closed_tags)

        # Pretty print (before adding header)
        if pretty:
            content = self._prettify_xml(content)

        # Add XML declaration
        if doc_header is True:
            content = f"<?xml version='1.0' encoding='{encoding}'?>\n{content}"
        elif isinstance(doc_header, str):
            content = f"{doc_header}\n{content}"

        if filename:
            result_bytes = content.encode(encoding)
            with open(filename, "wb") as f:
                f.write(result_bytes)
            return None

        return content

    def _prettify_xml(self, xml_str: str) -> str:
        """Format XML with indentation."""
        try:
            result = parseString(xml_str).toprettyxml(indent="  ")
            # Remove the xml declaration added by toprettyxml
            if result.startswith("<?xml"):
                result = result.split("\n", 1)[1] if "\n" in result else ""
            return result
        except Exception:
            # If parsing fails (e.g., multiple roots), wrap temporarily
            wrapped = f"<_root_>{xml_str}</_root_>"
            pretty_xml = parseString(wrapped).toprettyxml(indent="  ")
            # Extract content between _root_ tags
            start = pretty_xml.find("<_root_>") + 8
            end = pretty_xml.rfind("</_root_>")
            return pretty_xml[start:end].strip()

    def _bag_to_xml(self, namespaces: list[str], self_closed_tags: list[str] | None = None) -> str:
        """Convert Bag to XML string."""
        parts = []
        for node in self:  # type: ignore[attr-defined]
            parts.append(self._node_to_xml(node, namespaces, self_closed_tags))
        return "".join(parts)

    def _node_to_xml(
        self, node: Any, namespaces: list[str], self_closed_tags: list[str] | None = None
    ) -> str:
        """Convert a BagNode to XML string."""
        # Extract local namespaces from this node's attributes
        local_namespaces = self._extract_namespaces(node.attr)
        current_namespaces = namespaces + local_namespaces

        # Use xml_tag (from parsing), or tag (from builder), or label (unique key)
        xml_tag = node.xml_tag or node.tag or node.label
        tag, original_tag = self._sanitize_tag(xml_tag, current_namespaces)

        # Build attributes string
        attrs_parts = []
        if original_tag is not None:
            attrs_parts.append(f"_tag={saxutils.quoteattr(original_tag)}")

        if node.attr:
            for k, v in node.attr.items():
                if v is not None and v is not False:
                    attrs_parts.append(f"{k}={saxutils.quoteattr(str(v))}")

        attrs_str = " " + " ".join(attrs_parts) if attrs_parts else ""

        # Handle value
        value = node.value

        # Check if value is a Bag (using duck typing to avoid import)
        if hasattr(value, "_bag_to_xml"):
            inner = value._bag_to_xml(current_namespaces, self_closed_tags)
            if inner:
                return f"<{tag}{attrs_str}>{inner}</{tag}>"
            # Empty Bag
            if self_closed_tags is None or tag in self_closed_tags:
                return f"<{tag}{attrs_str}/>"
            return f"<{tag}{attrs_str}></{tag}>"

        # Scalar value
        if value is None or value == "":
            if self_closed_tags is None or tag in self_closed_tags:
                return f"<{tag}{attrs_str}/>"
            return f"<{tag}{attrs_str}></{tag}>"

        text = saxutils.escape(str(value))
        return f"<{tag}{attrs_str}>{text}</{tag}>"

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
            return "_none_", None

        # If tag has a known namespace prefix, keep it as-is
        if ":" in tag:
            prefix = tag.split(":")[0]
            if prefix in namespaces:
                return tag, None

        sanitized = re.sub(r"_+", "_", _INVALID_XML_TAG_CHARS.sub("_", tag))

        if sanitized[0].isdigit():
            sanitized = "_" + sanitized

        if sanitized != tag:
            return sanitized, tag
        return sanitized, None

    @staticmethod
    def _extract_namespaces(attrs: dict | None) -> list[str]:
        """Extract namespace prefixes from attributes (xmlns:prefix)."""
        if not attrs:
            return []
        return [k[6:] for k in attrs if k.startswith("xmlns:")]

    # ==================== to_tytx ====================

    def to_tytx(
        self,
        transport: Literal["json", "msgpack"] = "json",
        filename: str | None = None,
        compact: bool = False,
    ) -> str | bytes | None:
        """Serialize a Bag to TYTX format.

        Converts the entire Bag hierarchy into a flat list of row tuples,
        then encodes it using TYTX which preserves Python types (Decimal,
        date, datetime, time) in the wire format.

        Args:
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
        """
        if compact:
            paths: dict[int, str] = {}
            rows = list(self._node_flattener(path_registry=paths))
            paths_str = {str(k): v for k, v in paths.items()}
            data = {"rows": rows, "paths": paths_str}
        else:
            rows = list(self._node_flattener())
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

    def _node_flattener(
        self,
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
        """
        compact = path_registry is not None
        if compact:
            path_to_code: dict[str, int] = {}
            code_counter = 0

        for path, node in self.walk():  # type: ignore[attr-defined]
            parent_path = path.rsplit(".", 1)[0] if "." in path else ""

            # Use static=True to avoid triggering resolvers during serialization
            node_value = node.get_value(static=True)

            # Value encoding - use duck typing to check for Bag
            if hasattr(node_value, "walk") and hasattr(node_value, "_nodes"):
                value = "::X"
            elif node_value is None:
                value = "::NN"
            else:
                value = node_value

            attr = dict(node.attr) if node.attr else {}

            if compact:
                parent_ref = path_to_code.get(parent_path) if parent_path else None
                yield (parent_ref, node.label, node.tag, value, attr)

                if hasattr(node_value, "walk") and hasattr(node_value, "_nodes"):
                    path_to_code[path] = code_counter
                    path_registry[code_counter] = path  # type: ignore[index]
                    code_counter += 1
            else:
                yield (parent_path, node.label, node.tag, value, attr)

    # ==================== to_json ====================

    def to_json(
        self,
        typed: bool = True,
    ) -> str:
        """Serialize Bag to JSON string.

        Each node becomes {"label": ..., "value": ..., "attr": {...}}.
        Nested Bags have value as a list of child nodes.

        Args:
            typed: If True, encode types for date/datetime/Decimal (TYTX).

        Returns:
            JSON string representation.
        """
        result = [self._node_to_json_dict(node, typed) for node in self]  # type: ignore[attr-defined]

        if typed:
            return tytx_encode(result)  # type: ignore[return-value]
        return json.dumps(result)

    def _node_to_json_dict(self, node: Any, typed: bool) -> dict:
        """Convert a BagNode to JSON-serializable dict."""
        # Use static=True to avoid triggering resolvers during serialization
        value = node.get_value(static=True)
        # Check if value is a Bag using duck typing
        if hasattr(value, "_nodes") and hasattr(value, "walk"):
            value = [value._node_to_json_dict(n, typed) for n in value]
        return {"label": node.label, "value": value, "attr": dict(node.attr) if node.attr else {}}
