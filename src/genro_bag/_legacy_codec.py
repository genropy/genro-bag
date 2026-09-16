# Copyright 2004-2007 Softwell S.r.l. and GenroPy contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Operation-local codec for the historical GenRoBag XML and JSON wires.

The XML behavior is selectively adapted from GenroPy's
``gnr.core.gnrbagxml`` and the in-repository compatibility prototype.  The
catalog itself remains an optional GenroPy dependency and is never copied or
mutated here.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml import sax
from xml.sax import saxutils
from xml.sax.handler import ContentHandler

_INVALID_XML_TAG_CHARS = re.compile(r"[^\w.]", re.ASCII)
_KNOWN_ATTRIBUTE_TYPES = (
    bytes,
    str,
    int,
    float,
    datetime.date,
    datetime.time,
    datetime.datetime,
    bool,
    type(None),
    list,
    tuple,
    dict,
    Decimal,
)


class LegacyCodecDependencyError(ImportError):
    """Raised when a legacy operation has neither a catalog nor GenroPy."""


def legacy_catalog(catalog: Any = None) -> Any:
    if catalog is not None:
        return catalog
    try:
        from gnr.core.gnrclasses import GnrClassCatalog
    except ImportError as exc:
        raise LegacyCodecDependencyError(
            "Legacy XML/JSON requires an injected GenroPy catalog or the "
            "optional 'gnr.core.gnrclasses' package"
        ) from exc
    return GnrClassCatalog()


def _is_bag(value: Any) -> bool:
    from .bag import Bag

    return isinstance(value, Bag)


def legacy_to_json(
    bag: Any,
    *,
    typed: bool = True,
    nested: bool = False,
    catalog: Any = None,
) -> str | list[dict[str, Any]]:
    converter = legacy_catalog(catalog)
    result = [_legacy_node_to_json(node, typed, converter) for node in bag]
    if nested:
        return result
    if typed:
        return converter.toTypedJSON(result)
    return converter.toJson(result)


def _legacy_node_to_json(
    node: Any, typed: bool, catalog: Any
) -> dict[str, Any]:
    # Historical JSON resolves the node and has no resolver metadata.  This is
    # deliberately distinct from unresolved legacy XML and modern JSON.
    value = node.get_value()
    if _is_bag(value):
        value = [_legacy_node_to_json(child, typed, catalog) for child in value]
    return {"label": node.label, "value": value, "attr": dict(node.attr)}


def legacy_from_json(
    bag_class: type,
    source: str | dict | list | Any,
    *,
    list_joiner: str | None = None,
    catalog: Any = None,
) -> Any:
    converter = legacy_catalog(catalog)
    if isinstance(source, str):
        source = json.loads(source)
    if not isinstance(source, (list, dict)):
        source = {"value": source}
    result = _legacy_json_value(bag_class, source, list_joiner, converter)
    return result if _is_bag(result) else bag_class({"value": result})


def _legacy_json_value(
    bag_class: type,
    value: Any,
    list_joiner: str | None,
    catalog: Any,
    parent_key: str | None = None,
) -> Any:
    if isinstance(value, str):
        return catalog.fromTypedText(value)
    if isinstance(value, list):
        if not value:
            return bag_class()
        if list_joiner and all(
            isinstance(item, str) and not catalog.isTypedText(item) for item in value
        ):
            return list_joiner.join(value)
        result = bag_class()
        for index, item in enumerate(value):
            if isinstance(item, dict) and "label" in item:
                label = item["label"]
                child = _legacy_json_value(
                    bag_class, item.get("value"), list_joiner, catalog, label
                )
                attrs = {
                    key: _legacy_json_value(bag_class, attr, None, catalog)
                    for key, attr in (item.get("attr") or {}).items()
                }
                node = result.set_item(label, child, _attributes=attrs)
                node.xml_tag = label
            else:
                label = f"{parent_key or 'r'}_{index}"
                child = _legacy_json_value(
                    bag_class, item, list_joiner, catalog, parent_key
                )
                result.set_item(label, child)
        return result
    if isinstance(value, dict):
        if not value:
            return bag_class()
        result = bag_class()
        for key, child in value.items():
            result.set_item(
                key,
                _legacy_json_value(bag_class, child, list_joiner, catalog, key),
            )
        return result
    return value


def legacy_to_xml(
    bag: Any,
    *,
    filename: str | os.PathLike[str] | Any | None = None,
    encoding: str = "UTF-8",
    catalog: Any = None,
    typeattrs: bool = True,
    typevalue: bool = True,
    add_bag_type_attr: bool = True,
    output_encoding: str | None = None,
    unresolved: bool = False,
    autocreate: bool = False,
    doc_header: bool | str | None = None,
    self_closed_tags: list[str] | None = None,
    translate_cb: Any = None,
    omit_unknown_types: bool = False,
    omit_root: bool = False,
    forced_tag_attr: str | None = None,
    pretty: bool | str = False,
) -> str:
    writer = _LegacyXmlWriter(
        catalog=legacy_catalog(catalog),
        typeattrs=typeattrs,
        typevalue=typevalue,
        add_bag_type_attr=add_bag_type_attr,
        output_encoding=output_encoding,
        unresolved=unresolved,
        self_closed_tags=self_closed_tags or [],
        translate_cb=translate_cb,
        omit_unknown_types=omit_unknown_types,
        forced_tag_attr=forced_tag_attr,
        indent=(pretty if isinstance(pretty, str) else "\t") if pretty else None,
    )
    body = writer.bag_block(bag, [], depth=0 if omit_root else 1)
    if omit_root:
        xml = body
    elif pretty and body:
        xml = f"<GenRoBag>\n{body}\n</GenRoBag>"
    else:
        xml = f"<GenRoBag>{body}</GenRoBag>"
    header = ""
    if doc_header is not False:
        header = doc_header or f"<?xml version='1.0' encoding='{encoding}'?>\n"
    result = (header or "") + xml
    result = result.encode(encoding, "replace").decode(encoding)
    if filename is not None:
        payload = result.encode(encoding)
        if hasattr(filename, "write"):
            filename.write(payload)
        else:
            path = os.fspath(filename)
            if autocreate:
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
            with open(path, "wb") as stream:
                stream.write(payload)
    return result


class _LegacyXmlWriter:
    def __init__(
        self,
        *,
        catalog: Any,
        typeattrs: bool,
        typevalue: bool,
        add_bag_type_attr: bool,
        output_encoding: str | None,
        unresolved: bool,
        self_closed_tags: list[str],
        translate_cb: Any,
        omit_unknown_types: bool,
        forced_tag_attr: str | None,
        indent: str | None = None,
    ) -> None:
        self.catalog = catalog
        self.typeattrs = typeattrs
        self.typevalue = typevalue
        self.add_bag_type_attr = add_bag_type_attr
        self.output_encoding = output_encoding
        self.unresolved = unresolved
        self.self_closed_tags = self_closed_tags
        self.translate_cb = translate_cb
        self.omit_unknown_types = omit_unknown_types
        self.forced_tag_attr = forced_tag_attr
        self.indent = indent

    def bag_block(
        self, bag: Any, namespaces: list[str], depth: int = 0, preserve_space: bool = False
    ) -> str:
        parts = []
        pretty = self.indent is not None and not preserve_space
        for node in bag:
            part = self.node_block(node, namespaces, depth, preserve_space)
            if part and pretty:
                tag = (node.attr.get(self.forced_tag_attr)
                       if self.forced_tag_attr else None) or node.xml_tag or node.label
                if tag != "__flatten__":
                    part = self.indent * depth + part
            if part or not pretty:
                parts.append(part)
        return ("" if preserve_space else "\n").join(parts)

    def node_block(
        self, node: Any, namespaces: list[str], depth: int = 0, preserve_space: bool = False
    ) -> str:
        attrs = dict(node.attr)
        if "__forbidden__" in attrs:
            return ""
        current_namespaces = namespaces + [
            key[6:] for key in attrs if key.startswith("xmlns:")
        ]
        tag = node.xml_tag or node.label
        preserve_space = self.indent is not None and (
            preserve_space or attrs.get("xml:space") == "preserve"
        )
        effective_tag = (attrs.get(self.forced_tag_attr) if self.forced_tag_attr else None) or tag
        child_depth = depth if effective_tag == "__flatten__" else depth + 1

        if (
            self.unresolved
            and node.resolver is not None
            and not getattr(node.resolver, "_xmlEager", None)
        ):
            if not attrs.get("_resolver_name"):
                attrs["_resolver"] = json.dumps(node.resolver.resolverSerialize())
            value = node.get_value(static=True)
            content = (self.bag_block(value, current_namespaces, child_depth, preserve_space)
                       if _is_bag(value) else "")
            return self.build_tag(tag, content, attrs, xml_mode=True, namespaces=current_namespaces,
                                  depth=depth, preserve_space=preserve_space)

        value = node.get_value()
        if _is_bag(value) and bool(value):
            return self.build_tag(
                tag,
                self.bag_block(value, current_namespaces, child_depth, preserve_space),
                attrs,
                xml_mode=True,
                localize=False,
                namespaces=current_namespaces,
                depth=depth,
                preserve_space=preserve_space,
            )
        return self.build_tag(tag, value, attrs, namespaces=current_namespaces)

    def build_tag(
        self,
        tag_name: str,
        value: Any,
        attributes: dict[str, Any] | None = None,
        type_code: str = "",
        xml_mode: bool = False,
        localize: bool = True,
        namespaces: list[str] | None = None,
        depth: int = 0,
        preserve_space: bool = False,
    ) -> str:
        namespaces = namespaces or []
        if not type_code and value != "":
            if _is_bag(value):
                if self.add_bag_type_attr:
                    value, type_code = "", "BAG"
                else:
                    value = ""
            else:
                value, type_code = self.catalog.asTextAndType(
                    value,
                    translate_cb=self.translate_cb if localize else None,
                    nestedTyping=True,
                )
        value = str(value)
        attrs = dict(attributes or {})
        if self.forced_tag_attr and self.forced_tag_attr in attrs:
            tag_name = str(attrs.pop(self.forced_tag_attr))
        if tag_name == "__flatten__":
            return value
        if self.omit_unknown_types:
            attrs = {
                key: item
                for key, item in attrs.items()
                if isinstance(item, _KNOWN_ATTRIBUTE_TYPES)
                or (
                    callable(item)
                    and (
                        hasattr(item, "is_rpc")
                        or hasattr(item, "__safe__")
                        or getattr(item, "__name__", "").startswith("rpc_")
                    )
                )
            }
        if self.typeattrs:
            attrs_text = " ".join(
                f"{key}={saxutils.quoteattr(self.catalog.asTypedText(item, translate_cb=self.translate_cb, nestedTyping=True))}"
                for key, item in attrs.items()
            )
        else:
            attrs_text = " ".join(
                f"{key}={saxutils.quoteattr(self.catalog.asText(item, translate_cb=self.translate_cb))}"
                for key, item in attrs.items()
                if item is not False
            )

        original_tag = tag_name
        if not tag_name:
            tag_name = "_none_"
        if ":" not in tag_name or tag_name.split(":", 1)[0] not in namespaces:
            tag_name = re.sub(r"_+", "_", _INVALID_XML_TAG_CHARS.sub("_", tag_name))
        if tag_name[0].isdigit():
            tag_name = "_" + tag_name
        tag_attrs = ""
        if tag_name != original_tag:
            tag_attrs = f" _tag={saxutils.quoteattr(saxutils.escape(original_tag))}"
        if self.typevalue and type_code not in ("", "T"):
            tag_attrs += f' _T="{type_code}"'
        if attrs_text:
            tag_attrs += f" {attrs_text}"

        if not xml_mode:
            if value.endswith("::HTML"):
                value = value[:-6]
            elif any(char in value for char in "<>&"):
                value = saxutils.escape(value)
            if self.output_encoding:
                value = value.encode(self.output_encoding, "ignore").decode("utf-8")
        if not value and tag_name in self.self_closed_tags:
            return f"<{tag_name}{tag_attrs}/>"
        if xml_mode and value and self.indent is not None and not preserve_space:
            return f"<{tag_name}{tag_attrs}>\n{value}\n{self.indent * depth}</{tag_name}>"
        return f"<{tag_name}{tag_attrs}>{value}</{tag_name}>"


@dataclass
class _XmlFrame:
    tag: str
    attrs: dict[str, Any]
    type_code: str | None
    value: Any
    text: list[str] = field(default_factory=list)


class _LegacyXmlHandler(ContentHandler):
    def __init__(
        self,
        bag_class: type,
        catalog: Any,
        empty: Any = None,
        attr_in_value: str | bool | None = None,
        avoid_duplicate_label: bool | None = None,
    ) -> None:
        super().__init__()
        self.bag_class = bag_class
        self.catalog = catalog
        self.empty = empty
        self.attr_in_value = attr_in_value
        self.avoid_duplicate_label = avoid_duplicate_label

    def startDocument(self) -> None:
        self.outer = self.bag_class()
        self.frames: list[_XmlFrame] = []
        self.is_genrobag = False

    def startElement(self, tag: str, attributes: Any) -> None:
        attrs = {
            str(key): self.catalog.fromTypedText(saxutils.unescape(value))
            for key, value in attributes.items()
        }
        if not self.frames:
            self.is_genrobag = tag.lower() == "genrobag"
        type_code = attrs.pop("_T", attrs.pop("T", None)) if self.is_genrobag else None
        value = [] if type_code and type_code.startswith("A") else self.bag_class()
        self.frames.append(_XmlFrame(tag, attrs, type_code, value))

    def characters(self, content: str) -> None:
        if self.frames:
            self.frames[-1].text.append(content)

    def endElement(self, tag: str) -> None:
        frame = self.frames.pop()
        text = "".join(frame.text)
        value = self._frame_value(frame, text)
        if self.frames:
            parent = self.frames[-1]
            if isinstance(parent.value, list):
                parent.value.append(value)
            else:
                self._put(parent.value, frame.tag, value, frame.attrs)
        else:
            self._put(self.outer, frame.tag, value, frame.attrs)

    def _frame_value(self, frame: _XmlFrame, text: str) -> Any:
        if isinstance(frame.value, list):
            return frame.value
        if bool(frame.value):
            stripped = text.strip()
            if stripped:
                frame.value.set_item("_", stripped)
            return frame.value
        if frame.type_code == "BAG":
            return frame.value
        if frame.type_code and frame.type_code != "T":
            return self.catalog.fromText(text, frame.type_code)
        if text:
            return text
        return self.empty() if self.empty else ""

    def _put(
        self, target: Any, source_tag: str, value: Any, attrs: dict[str, Any]
    ) -> None:
        attrs = dict(attrs)
        desired = str(attrs.pop("_tag", source_tag))
        label = desired
        if target.get_node(label) is not None:
            suffix = 1
            template = f"{desired}_{{}}" if self.avoid_duplicate_label else f"{desired}__dup_{{}}"
            while target.get_node(template.format(suffix)) is not None:
                suffix += 1
            label = template.format(suffix)
        if self.attr_in_value and attrs:
            wrapped = self.bag_class()
            wrapped.set_item("__attributes", self.bag_class(attrs))
            if value not in (None, ""):
                wrapped.set_item("__content", value)
            value, attrs = wrapped, {}
        node = target.set_item(label, value, _attributes=attrs or None)
        node.xml_tag = desired


def legacy_from_xml(
    bag_class: type,
    source: str | bytes | os.PathLike[str] | Any,
    *,
    catalog: Any = None,
    empty: Any = None,
    attr_in_value: str | bool | None = None,
    avoid_duplicate_label: bool | None = None,
) -> Any:
    converter = legacy_catalog(catalog)
    if hasattr(source, "read"):
        source = source.read()
    elif isinstance(source, os.PathLike) or (
        isinstance(source, str) and not source.lstrip().startswith("<")
    ):
        source = Path(source).read_bytes()
    if isinstance(source, bytes):
        source = source.decode()
    if not isinstance(source, str):
        raise TypeError(f"Legacy XML source must be text, bytes, path, or stream, got {type(source).__name__}")
    for key, value in os.environ.items():
        if key.startswith("GNR_"):
            source = source.replace(f"{{{key}}}", value)

    handler = _LegacyXmlHandler(
        bag_class,
        converter,
        empty=empty,
        attr_in_value=attr_in_value,
        avoid_duplicate_label=avoid_duplicate_label,
    )
    parser = sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(sax.handler.feature_external_ges, False)
    parser.setFeature(sax.handler.feature_external_pes, False)
    parser.feed(source)
    parser.close()
    if handler.is_genrobag:
        root = handler.outer.get_item("GenRoBag", static=True)
        return root if _is_bag(root) else bag_class()
    return handler.outer
