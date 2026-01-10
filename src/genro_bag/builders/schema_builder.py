# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SchemaBuilder - Builder for creating builder schemas programmatically.

This module provides a specialized builder for constructing schemas that will
be used by other builders. Instead of creating HTML elements or domain objects,
SchemaBuilder creates schema definition nodes.

The schema it produces can be assigned to a builder's _schema class attribute,
or serialized to MessagePack for later loading.

Schema Structure Specification
==============================

**STATUS: IN FASE DI IMPLEMENTAZIONE**

The schema uses a hierarchical path convention to distinguish between
real elements and abstract base definitions:

Path Prefixes:
    - ``el.*`` : Real elements (usable by the builder)
    - ``ab.*`` : Abstract elements (only for inheritance, not directly usable)

Inheritance:
    Elements can inherit attributes from other elements using ``inherits_from``.
    This avoids repetition when many elements share the same ``sub_tags``.

Example with inheritance::

    from genro_bag import Bag
    from genro_bag.builders import SchemaBuilder

    schema = Bag(builder=SchemaBuilder)

    # Define abstract base elements
    schema.item('ab.flow', sub_tags='el.p,el.div,el.span,el.ul,el.ol')
    schema.item('ab.phrasing', sub_tags='el.span,el.a,el.em,el.strong')

    # Define real elements inheriting from abstracts
    schema.item('el.div', inherits_from='ab.flow')
    schema.item('el.section', inherits_from='ab.flow')
    schema.item('el.article', inherits_from='ab.flow')
    schema.item('el.p', inherits_from='ab.phrasing')
    schema.item('el.span', inherits_from='ab.phrasing')

    # Void elements (no children allowed)
    schema.item('el.br', sub_tags='')
    schema.item('el.hr', sub_tags='')
    schema.item('el.img', sub_tags='')

    # Save to MessagePack
    schema.builder.compile('path/to/schema.msgpack')

Builder Lookup:
    When a builder looks up an element, it searches only in ``el.*``.
    Abstract elements (``ab.*``) are used only for inheritance resolution.

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

from .base_builder import BagBuilderBase, element

if TYPE_CHECKING:
    from ..bag import Bag
    from ..bagnode import BagNode


class SchemaBuilder(BagBuilderBase):
    """Builder for creating builder schemas.

    See module docstring for full specification (including el.*/ab.* convention
    and inherits_from attribute).

    Creates schema nodes with the structure expected by BagBuilderBase:
    - node.label = element name (e.g., 'div' or 'el.div')
    - node.value = None
    - node.attr = {sub_tags, sub_tags_order, inherits_from, ...}

    Usage:
        schema = Bag(builder=SchemaBuilder)
        schema.item('el.div', inherits_from='ab.flow')
        schema.item('ab.flow', sub_tags='el.p,el.span')
        schema.item('el.br', sub_tags='')  # void element
    """

    @element()
    def item(self, target: Bag, tag: str, value=None, **attr: Any) -> BagNode:
        """Define a schema item (element definition).

        Args:
            target: The schema Bag.
            value: Element name (e.g., 'div', 'span').
            **attr: Additional attributes (sub_tags, sub_tags_order, handler, etc.).

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
