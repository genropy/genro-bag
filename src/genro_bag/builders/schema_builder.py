# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SchemaBuilder - Builder for creating builder schemas programmatically.

This module provides a specialized builder for constructing schemas that will
be used by other builders. Instead of creating HTML elements or domain objects,
SchemaBuilder creates schema definition nodes.

The schema it produces can be assigned to a builder's _schema class attribute,
or serialized to MessagePack for later loading.

Schema Structure Specification
==============================

The schema uses a naming convention to distinguish between
real elements and abstract base definitions:

Naming Conventions:
    - Elements: stored by name (e.g., 'div', 'span')
    - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')

Abstracts define sub_tags for inheritance and cannot be used directly
(Python syntax prevents calling bag.@flow()).

Inheritance:
    Elements can inherit attributes from abstracts using ``inherits_from``.
    This avoids repetition when many elements share the same ``sub_tags``.

Example with inheritance::

    from genro_bag import Bag
    from genro_bag.builders import SchemaBuilder

    schema = Bag(builder=SchemaBuilder)

    # Define abstract base elements (prefixed with @)
    schema.item('@flow', sub_tags='p,div,span,ul,ol')
    schema.item('@phrasing', sub_tags='span,a,em,strong')

    # Define real elements inheriting from abstracts
    schema.item('div', inherits_from='@flow')
    schema.item('section', inherits_from='@flow')
    schema.item('article', inherits_from='@flow')
    schema.item('p', inherits_from='@phrasing')
    schema.item('span', inherits_from='@phrasing')

    # Void elements (no children allowed)
    schema.item('br', sub_tags='')
    schema.item('hr', sub_tags='')
    schema.item('img', sub_tags='')

    # Save to MessagePack
    schema.builder.compile('path/to/schema.msgpack')

Builder Lookup:
    When a builder looks up an element, it searches by name.
    Abstract elements (prefixed with '@') are used only for inheritance.

Basic Example (without inheritance)::

    from genro_bag import Bag
    from genro_bag.builders import SchemaBuilder

    schema = Bag(builder=SchemaBuilder)

    # Simple flat schema
    schema.item('div', sub_tags='div,span,p,a')
    schema.item('span', sub_tags='span,a')
    schema.item('p', sub_tags='span,a')
    schema.item('a')
    schema.item('br', sub_tags='')  # void element

    schema.builder.compile('path/to/schema.msgpack')

    # Use the schema in a builder class
    class MyHtmlBuilder(BagBuilderBase):
        schema_path = 'path/to/schema.msgpack'
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..builder import BagBuilderBase, element

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


class SchemaBuilder(BagBuilderBase):
    """Builder for creating builder schemas.

    See module docstring for full specification.

    Creates schema nodes with the structure expected by BagBuilderBase:
    - node.label = element name (e.g., 'div') or abstract (e.g., '@flow')
    - node.value = None
    - node.attr = {sub_tags, sub_tags_order, inherits_from, ...}

    Usage:
        schema = Bag(builder=SchemaBuilder)
        schema.item('@flow', sub_tags='p,span')
        schema.item('div', inherits_from='@flow')
        schema.item('br', sub_tags='')  # void element
    """

    @element()
    def item(self, target: Bag, tag: str, value=None, **attr: Any) -> BagNode:
        """Define a schema item (element definition).

        Args:
            target: The schema Bag.
            value: Element name (e.g., 'div', 'span').
            **attr: Schema attributes (sub_tags, sub_tags_order, inherits_from).

        Returns:
            The created schema node.
        """
        tag = value
        attr['node_label'] = value
        return self.child(target, tag, **attr)

    def compile(self, destination: str | Path) -> None:
        """Compile the schema to MessagePack file.

        Serializes the schema Bag to a MessagePack file for later loading
        by builders that use pre-compiled schemas.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self.bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)

