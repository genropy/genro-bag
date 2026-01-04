# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bag serialization functions: XML, JSON, dict conversions.

This module provides serialization and deserialization functions for Bag objects.
These are kept separate from the main Bag class to keep the core implementation clean.

Usage:
    from genro_bag.bag_serialization import to_xml, from_xml, to_json, from_json

    # Serialize
    xml_string = to_xml(bag)
    json_string = to_json(bag)

    # Deserialize
    bag = from_xml(xml_string)
    bag = from_json(json_string)

    # Dict conversion
    d = as_dict(bag)
    d = as_dict_deeply(bag)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bag import Bag


# =============================================================================
# XML Serialization
# =============================================================================

def to_xml(bag: Bag, filename: str | None = None, encoding: str = 'UTF-8',
           typeattrs: bool = True, typevalue: bool = True,
           unresolved: bool = False, autocreate: bool = False,
           translate_cb: Any = None, self_closed_tags: list | None = None,
           omit_root: bool = False, catalog: Any = None,
           omit_declaration: bool = False, pretty: bool = True) -> str:
    """Serialize Bag to XML string.

    Args:
        bag: The Bag to serialize.
        filename: Optional file path to write to.
        encoding: XML encoding (default UTF-8).
        typeattrs: Include type information in attributes.
        typevalue: Include type information for values.
        unresolved: Include unresolved resolver info.
        autocreate: Auto-create file directory.
        translate_cb: Callback for value translation.
        self_closed_tags: Tags to self-close.
        omit_root: Don't wrap in root element.
        catalog: Type catalog for serialization.
        omit_declaration: Skip XML declaration.
        pretty: Format with indentation.

    Returns:
        XML string representation.
    """
    # TODO: Implement
    raise NotImplementedError("to_xml not yet implemented")


def from_xml(source: str | bytes, catalog: Any = None, bag_cls: type | None = None,
             empty: type | None = None, allow_not_wellformed: bool = False,
             native_types: bool = False) -> Bag:
    """Deserialize XML to Bag.

    Args:
        source: XML string, bytes, or file path.
        catalog: Type catalog for deserialization.
        bag_cls: Bag class to use (default: Bag).
        empty: Class for empty values.
        allow_not_wellformed: Allow malformed XML.
        native_types: Convert to native Python types.

    Returns:
        Deserialized Bag.
    """
    # TODO: Implement
    raise NotImplementedError("from_xml not yet implemented")


# =============================================================================
# JSON Serialization
# =============================================================================

def to_json(bag: Bag, typed: bool = True, nested: bool = False) -> str:
    """Serialize Bag to JSON string.

    Args:
        bag: The Bag to serialize.
        typed: Include type information.
        nested: Use nested format.

    Returns:
        JSON string representation.
    """
    # TODO: Implement
    raise NotImplementedError("to_json not yet implemented")


def from_json(source: str, list_joiner: str | None = None) -> Bag:
    """Deserialize JSON to Bag.

    Args:
        source: JSON string.
        list_joiner: Character to join list elements.

    Returns:
        Deserialized Bag.
    """
    # TODO: Implement
    raise NotImplementedError("from_json not yet implemented")


# =============================================================================
# Dict Conversion
# =============================================================================

def as_dict(bag: Bag, ascii: bool = False, lower: bool = False) -> dict:
    """Convert Bag to dict (shallow).

    Args:
        bag: The Bag to convert.
        ascii: Convert keys to ASCII.
        lower: Convert keys to lowercase.

    Returns:
        Dict with Bag contents (nested Bags remain as Bag objects).
    """
    # TODO: Implement
    raise NotImplementedError("as_dict not yet implemented")


def as_dict_deeply(bag: Bag, ascii: bool = False, lower: bool = False) -> dict:
    """Convert Bag to dict (deep - nested Bags become dicts).

    Args:
        bag: The Bag to convert.
        ascii: Convert keys to ASCII.
        lower: Convert keys to lowercase.

    Returns:
        Dict with Bag contents (nested Bags converted to dicts).
    """
    # TODO: Implement
    raise NotImplementedError("as_dict_deeply not yet implemented")


def as_string(bag: Bag, encoding: str = 'UTF-8', mode: str = 'weak') -> str:
    """Convert Bag to string representation.

    Args:
        bag: The Bag to convert.
        encoding: String encoding.
        mode: Conversion mode ('weak' or other).

    Returns:
        String representation.
    """
    # TODO: Implement
    raise NotImplementedError("as_string not yet implemented")
