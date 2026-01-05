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

from collections.abc import Iterator
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
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
