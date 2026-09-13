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
from typing import TYPE_CHECKING, Any, Literal
from xml.dom.minidom import parseString
from xml.sax import saxutils

from genro_tytx import to_tytx as tytx_encode

from genro_bag._resolver_wire import encode_attrs, encode_resolver, has_nested_resolver
from genro_bag.bag._exceptions import BagSerializationError

if TYPE_CHECKING:
    from genro_bag.bagnode import BagNode

# Regex for sanitizing XML tag names
_INVALID_XML_TAG_CHARS = re.compile(r"[^\w.]", re.ASCII)


class BagSerializer:
    """Mixin providing serialization instance methods for Bag.

    Supports to_xml (with optional pretty-print), to_tytx (compact typed
    text format), and to_json output formats.
    """

    if TYPE_CHECKING:
        def __iter__(self) -> Iterator[BagNode]: ...
        def walk(self, callback: Any = None, static: bool = True, **kw: Any) -> Iterator[tuple[str, BagNode]]: ...

    # ==================== to_xml ====================

    def to_xml(
        self,
        filename: str | None = None,
        encoding: str = "UTF-8",
        doc_header: bool | str | None = None,
        pretty: bool = False,
        self_closed_tags: list[str] | None = None,
        sign_key: str | None = None,
        expires_in: int | None = None,
        *,
        legacy_mode: bool = False,
        catalog: Any = None,
        typeattrs: bool = True,
        typevalue: bool = True,
        unresolved: bool = False,
        add_bag_type_attr: bool = True,
        output_encoding: str | None = None,
        autocreate: bool = False,
        translate_cb: Any = None,
        omit_unknown_types: bool = False,
        omit_root: bool = False,
        forced_tag_attr: str | None = None,
    ) -> str | None:
        """Serialize to XML format.

        All values are converted to strings without type information.
        For type-preserving serialization, use to_tytx() instead.

        Resolvers travel as ``::RSLV:`` marked strings: a node's own resolver
        becomes a ``_resolver`` attribute, one held in an attribute replaces
        that attribute's value.

        Args:
            filename: If provided, write to file. If None, return XML string.
            encoding: XML encoding (default 'UTF-8').
            doc_header: XML declaration (True for auto, False/None for none, str for custom).
            pretty: If True, format with indentation.
            self_closed_tags: List of tags to self-close when empty.
            sign_key: Secret key. When given, resolver payloads are signed —
                use it whenever the XML may come back from an untrusted party.
            expires_in: Lifetime in seconds for the signatures.

        Returns:
            XML string if filename is None, else None.

        Raises:
            BagSerializationError: If a resolver cannot be written as JSON.

        Example:
            >>> bag = Bag()
            >>> bag['name'] = 'test'
            >>> bag['count'] = 42
            >>> bag.to_xml()
            '<name>test</name><count>42</count>'
        """
        if legacy_mode:
            if sign_key is not None or expires_in is not None:
                raise ValueError(
                    "Legacy XML does not support resolver signatures; use "
                    "modern XML/TYTX or omit sign_key and expires_in"
                )
            from genro_bag._legacy_codec import legacy_to_xml

            return legacy_to_xml(
                self,
                filename=filename,
                encoding=encoding,
                catalog=catalog,
                typeattrs=typeattrs,
                typevalue=typevalue,
                unresolved=unresolved,
                add_bag_type_attr=add_bag_type_attr,
                output_encoding=output_encoding,
                autocreate=autocreate,
                doc_header=doc_header,
                self_closed_tags=self_closed_tags,
                translate_cb=translate_cb,
                omit_unknown_types=omit_unknown_types,
                omit_root=omit_root,
                forced_tag_attr=forced_tag_attr,
                pretty=pretty,
            )

        content = self._bag_to_xml(
            namespaces=[],
            self_closed_tags=self_closed_tags,
            sign_key=sign_key,
            expires_in=expires_in,
        )

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

    def _bag_to_xml(
        self,
        namespaces: list[str],
        self_closed_tags: list[str] | None = None,
        sign_key: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """Convert Bag to XML string."""
        parts = []
        for node in self:
            parts.append(
                self._node_to_xml(node, namespaces, self_closed_tags, sign_key, expires_in)
            )
        return "".join(parts)

    def _node_to_xml(
        self,
        node: Any,
        namespaces: list[str],
        self_closed_tags: list[str] | None = None,
        sign_key: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """Convert a BagNode to XML string."""
        # Extract local namespaces from this node's attributes
        local_namespaces = self._extract_namespaces(node.attr)
        current_namespaces = namespaces + local_namespaces

        # Use xml_tag (from parsing), or node_tag (semantic type), or label (unique key)
        xml_tag = node.xml_tag or node.node_tag or node.label
        tag, original_tag = self._sanitize_tag(xml_tag, current_namespaces)

        # Build attributes string
        attrs_parts = []
        if original_tag is not None:
            attrs_parts.append(f"_tag={saxutils.quoteattr(original_tag)}")

        where = f"node {node.label!r}"
        if node.resolver is not None:
            payload = encode_resolver(node.resolver, sign_key, expires_in, where)
            attrs_parts.append(f"_resolver={saxutils.quoteattr(payload)}")

        for k, v in encode_attrs(node.attr, sign_key, expires_in, where).items():
            if v is not None:
                attrs_parts.append(f"{k}={saxutils.quoteattr(str(v))}")

        attrs_str = " " + " ".join(attrs_parts) if attrs_parts else ""

        # Handle value
        value = node.get_value(static=True)

        # Check if value is a Bag (using duck typing to avoid import)
        if hasattr(value, "_bag_to_xml"):
            inner = value._bag_to_xml(current_namespaces, self_closed_tags, sign_key, expires_in)
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
        sign_key: str | None = None,
        expires_in: int | None = None,
    ) -> str | bytes | None:
        """Serialize a Bag to TYTX format.

        Converts the entire Bag hierarchy into a flat list of row tuples,
        then encodes it using TYTX which preserves Python types (Decimal,
        date, datetime, time) in the wire format.

        Resolvers travel as ``::RSLV:`` marked strings, in the value slot
        for a node's own resolver, in place of the attribute value for one
        held in an attribute.

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
            sign_key: Secret key. When given, resolver payloads are signed —
                use it whenever the data may come back from an untrusted party.
            expires_in: Lifetime in seconds for the signatures.

        Returns:
            If filename is None: serialized data (str or bytes).
            If filename is provided: None (data written to file).

        Raises:
            ImportError: If genro-tytx package is not installed.
            BagSerializationError: If a resolver cannot be written as JSON,
                or, with sign_key, if a Bag nested in a plain container
                value (node value or attribute) carries a resolver — that
                path goes through the type registry and cannot be signed.
        """
        if compact:
            paths: dict[int, str] = {}
            rows = list(
                self._node_flattener(
                    path_registry=paths, sign_key=sign_key, expires_in=expires_in
                )
            )
            paths_str = {str(k): v for k, v in paths.items()}
            data = {"rows": rows, "paths": paths_str}
        else:
            rows = list(self._node_flattener(sign_key=sign_key, expires_in=expires_in))
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
        sign_key: str | None = None,
        expires_in: int | None = None,
    ) -> Iterator[tuple[str | int | None, str, str | None, Any, dict]]:
        """Expand each node into (parent, label, tag, value, attr) tuples.

        Consumes walk() and transforms each node into a flat tuple suitable
        for TYTX serialization. Values are Python raw types - TYTX encoding
        is done later by the serializer.

        Special value markers:
            - "::<suffix>" for registered Bag branches ("::X" for ordinary Bags)
            - "::NN" for None values
            - "::RSLV:<payload>" for a node's own resolver

        Args:
            path_registry: Optional dict to enable compact mode.
                - If None: parent is path string (normal mode)
                - If dict: parent is numeric code, dict populated with
                  {code: full_path} mappings for branches
            sign_key: Secret key for signing resolver payloads.
            expires_in: Lifetime in seconds for the signatures.

        Yields:
            tuple: (parent, label, tag, value, attr) where:
                - parent: path string or int code (None for root-level)
                - label: node's label
                - tag: node's tag or None
                - value: "::<suffix>" for Bag branches, "::NN" for None, "::RSLV:..." for a
                  resolver, else raw value
                - attr: dict of node attributes, resolvers encoded
        """
        compact = path_registry is not None
        if compact:
            path_to_code: dict[str, int] = {}
            code_counter = 0

        for path, node in self.walk():
            parent_path = path.rsplit(".", 1)[0] if "." in path else ""
            where = f"node {path!r}"

            # Use static=True to avoid triggering resolvers during serialization
            node_value = node.get_value(static=True)

            # Value encoding - use duck typing to check for Bag.
            # The resolver wins: with one in place the static value is None,
            # which would otherwise be written as "::NN" and lose it.
            if node.resolver is not None:
                value = encode_resolver(node.resolver, sign_key, expires_in, where)
            elif hasattr(node_value, "walk") and hasattr(node_value, "_nodes"):
                value = f"::{type(node_value).__tytx_suffix__}"
            elif node_value is None:
                value = "::NN"
            else:
                # A Bag inside a plain container travels through the TYTX type
                # registry, whose hooks take no sign_key: a resolver in there
                # cannot be signed, so refuse instead of emitting it unsigned.
                if sign_key is not None and has_nested_resolver(node_value):
                    raise BagSerializationError(
                        f"{where}: a Bag nested in a plain container value "
                        "carries a resolver, which cannot be signed on this "
                        "path — move it to a Bag-valued node or drop sign_key"
                    )
                value = node_value

            attr = encode_attrs(node.attr, sign_key, expires_in, where)

            if compact:
                parent_ref = path_to_code.get(parent_path) if parent_path else None
                yield (parent_ref, node.label, node.node_tag, value, attr)

                if hasattr(node_value, "walk") and hasattr(node_value, "_nodes"):
                    path_to_code[path] = code_counter
                    assert path_registry is not None
                    path_registry[code_counter] = path
                    code_counter += 1
            else:
                yield (parent_path, node.label, node.node_tag, value, attr)

    # ==================== to_json ====================

    def to_json(
        self,
        typed: bool = True,
        sign_key: str | None = None,
        expires_in: int | None = None,
        *,
        legacy_mode: bool = False,
        nested: bool = False,
        catalog: Any = None,
    ) -> str | list[dict[str, Any]]:
        """Serialize Bag to JSON string.

        Each node becomes {"label": ..., "value": ..., "attr": {...}}.
        Nested Bags have value as a list of child nodes. A node's own
        resolver goes in a "resolver" key; one held in an attribute
        replaces that attribute's value. Both as ``::RSLV:`` strings.

        Args:
            typed: If True, encode types for date/datetime/Decimal (TYTX).
            sign_key: Secret key. When given, resolver payloads are signed —
                use it whenever the JSON may come back from an untrusted party.
            expires_in: Lifetime in seconds for the signatures.

        Returns:
            JSON string representation.

        Raises:
            BagSerializationError: If a resolver cannot be written as JSON,
                or, with sign_key, if a Bag nested in a plain container
                value (node value or attribute) carries a resolver — that
                path goes through the type registry and cannot be signed.
        """
        if legacy_mode:
            if sign_key is not None or expires_in is not None:
                raise ValueError(
                    "Legacy JSON does not support resolver signatures; use "
                    "modern JSON/TYTX or omit sign_key and expires_in"
                )
            from genro_bag._legacy_codec import legacy_to_json

            return legacy_to_json(
                self, typed=typed, nested=nested, catalog=catalog
            )

        result = [self._node_to_json_dict(node, typed, sign_key, expires_in) for node in self]

        if typed:
            return tytx_encode(result)  # type: ignore[return-value]
        return json.dumps(result)

    def _node_to_json_dict(
        self,
        node: Any,
        typed: bool,
        sign_key: str | None = None,
        expires_in: int | None = None,
    ) -> dict:
        """Convert a BagNode to JSON-serializable dict."""
        # Use static=True to avoid triggering resolvers during serialization
        value = node.get_value(static=True)
        where = f"node {node.label!r}"
        # Check if value is a Bag using duck typing
        if hasattr(value, "_nodes") and hasattr(value, "walk"):
            value = [value._node_to_json_dict(n, typed, sign_key, expires_in) for n in value]
        elif sign_key is not None and has_nested_resolver(value):
            # A Bag inside a plain container travels through the TYTX type
            # registry, whose hooks take no sign_key — same refusal as to_tytx.
            raise BagSerializationError(
                f"{where}: a Bag nested in a plain container value carries a "
                "resolver, which cannot be signed on this path — move it to "
                "a Bag-valued node or drop sign_key"
            )
        result = {
            "label": node.label,
            "value": value,
            "attr": encode_attrs(node.attr, sign_key, expires_in, where),
        }
        if node.resolver is not None:
            result["resolver"] = encode_resolver(node.resolver, sign_key, expires_in, where)
        if node.node_tag is not None:
            result["tag"] = node.node_tag
        return result
