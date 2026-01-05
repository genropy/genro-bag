# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag serialization module.

This module provides functions to serialize and deserialize Bag
hierarchies to/from various formats:

- **TYTX**: Type-preserving format with JSON or MessagePack transport
- **JSON**: JSON format with optional type preservation

TYTX Transports:
    - 'json': JSON string (.bag.json extension)
    - 'msgpack': Binary MessagePack (.bag.mp extension)

For XML serialization, see bag_xml module or use Bag.to_xml() / Bag.from_xml().

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

import json
from collections.abc import Iterator
from typing import Literal

from .bag import Bag


def node_flattener(
    bag: Bag,
    path_registry: dict[int, str] | None = None,
) -> Iterator[tuple[str | int | None, str, str | None, any, dict]]:
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


# ==================== JSON Serialization ====================


def _node_to_json(node: any, typed: bool) -> dict:
    """Convert a BagNode to JSON-serializable dict."""
    value = node.value
    if isinstance(value, Bag):
        value = [_node_to_json(n, typed) for n in value.nodes]
    return {"label": node.label, "value": value, "attr": dict(node.attr) if node.attr else {}}


def to_json(
    bag: Bag,
    typed: bool = True,
) -> str:
    """Serialize Bag to JSON string.

    Each node becomes {"label": ..., "value": ..., "attr": {...}}.
    Nested Bags have value as a list of child nodes.

    Args:
        bag: The Bag to serialize.
        typed: If True, encode types for date/datetime/Decimal (TYTX).

    Returns:
        JSON string representation.

    Example:
        >>> bag = Bag()
        >>> bag['name'] = 'test'
        >>> to_json(bag)
        '[{"label": "name", "value": "test", "attr": {}}]'
    """
    result = [_node_to_json(node, typed) for node in bag.nodes]

    if typed:
        from genro_tytx import to_tytx as tytx_encode
        return tytx_encode(result)
    return json.dumps(result)


def from_json(
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

    Example:
        >>> from_json('{"name": "test", "count": 42}')
        Bag with keys ['name', 'count']
    """

    if isinstance(source, str):
        from genro_tytx import from_tytx as tytx_decode
        source = tytx_decode(source)

    if not isinstance(source, (list, dict)):
        # Wrap scalar in a dict
        source = {"value": source}

    return _from_json_recursive(source, list_joiner)


def _from_json_recursive(
    data: dict | list | any,
    list_joiner: str | None = None,
    parent_key: str | None = None,
) -> Bag | any:
    """Recursively convert JSON data to Bag."""
    if isinstance(data, list):
        if not data:
            return Bag()

        # Check if list items have 'label' key (Bag node format)
        if isinstance(data[0], dict) and 'label' in data[0]:
            result = Bag()
            for item in data:
                label = item.get('label')
                value = _from_json_recursive(item.get('value'), list_joiner)
                attr = item.get('attr', {})
                result.set_item(label, value, _attributes=attr)
            return result

        # String list with joiner
        if list_joiner and all(isinstance(r, str) for r in data):
            return list_joiner.join(data)

        # Generic list -> Bag with prefix from parent key
        result = Bag()
        prefix = parent_key if parent_key else 'r'
        for n, v in enumerate(data):
            result.set_item(f'{prefix}_{n}', _from_json_recursive(v, list_joiner))
        return result

    if isinstance(data, dict):
        if not data:
            return Bag()
        result = Bag()
        for k, v in data.items():
            result.set_item(k, _from_json_recursive(v, list_joiner, parent_key=k))
        return result

    # Scalar value
    return data
