# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SchemaBuilder - Builder for creating builder schemas programmatically.

This module provides a specialized builder for constructing schemas that will
be used by other builders. Instead of creating HTML elements or domain objects,
SchemaBuilder creates schema definition nodes.

The schema it produces can be assigned to a builder's _schema class attribute,
or serialized to MessagePack for later loading.

Example:
    from genro_bag import Bag
    from genro_bag.builders import SchemaBuilder

    # Create a schema for HTML-like elements
    schema = Bag(builder=SchemaBuilder())

    # Define elements
    schema.item('div', sub_tags='div,span,p,a')
    schema.item('span', sub_tags='span,a')
    schema.item('p', sub_tags='span,a')
    schema.item('a')
    schema.void('br')
    schema.void('hr')
    schema.void('img')

    # Save to MessagePack file
    schema.builder.compile('path/to/schema.msgpack')

    # Use the schema in a builder class
    class MyHtmlBuilder(BagBuilderBase):
        _schema = schema  # The schema built above
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

    Creates schema nodes with the structure expected by BagBuilderBase:
    - node.label = element name
    - node.value = None (or Bag for complex cases)
    - node.attr = {handler, sub_tags, sub_tags_order, call_args_validations, leaf, ...}

    Usage:
        schema = Bag(builder=SchemaBuilder())
        schema.item('div', sub_tags='span,p')
        schema.void('br')
    """

    @element()
    def item(
        self,
        target: Bag,
        tag: str,
        name: str,
        sub_tags: str = "",
        sub_tags_order: str = "",
        handler: str | None = None,
        **attr: Any,
    ) -> BagNode:
        """Define a schema item (element definition).

        Args:
            target: The schema Bag.
            tag: Always 'item' (from decorator).
            name: Element name (e.g., 'div', 'span').
            sub_tags: Allowed sub-tags with cardinality (e.g., 'div,span[:1]').
            sub_tags_order: Ordering constraint (e.g., 'header>body>footer').
            handler: Method name to handle this element (e.g., '_el_div').
            **attr: Additional attributes (e.g., attrs for XSD validation).

        Returns:
            The created schema node.
        """
        return self.child(
            target,
            name,  # Use element name as tag
            sub_tags=sub_tags,
            sub_tags_order=sub_tags_order,
            handler=handler,
            **attr,
        )

    @element()
    def void(
        self,
        target: Bag,
        tag: str,
        name: str,
        handler: str | None = None,
        **attr: Any,
    ) -> BagNode:
        """Define a void (self-closing) element.

        Void elements have no sub-tags (leaf=True, sub_tags='').

        Args:
            target: The schema Bag.
            tag: Always 'void' (from decorator).
            name: Element name (e.g., 'br', 'hr', 'img').
            handler: Method name to handle this element.
            **attr: Additional attributes.

        Returns:
            The created schema node.
        """
        return self.child(
            target,
            name,
            sub_tags="",  # Empty sub_tags spec = leaf
            leaf=True,
            handler=handler,
            **attr,
        )

    @element()
    def group(
        self,
        target: Bag,
        tag: str,
        name: str,
        members: str,
        **attr: Any,
    ) -> BagNode:
        """Define a group of elements (for =ref references).

        Groups are not elements themselves but provide a way to define
        sets of elements that can be referenced in sub_tags specs.

        Args:
            target: The schema Bag.
            tag: Always 'group' (from decorator).
            name: Group name (e.g., 'flow', 'phrasing').
            members: Comma-separated member elements.
            **attr: Additional attributes.

        Returns:
            The created schema node.

        Note:
            To use a group in sub_tags spec, reference it with = prefix:
            schema.element('div', sub_tags='=flow')
        """
        return self.child(
            target,
            name,
            node_label=f"_group_{name}",  # Prefix to avoid collision with elements
            members=members,
            _is_group=True,
            **attr,
        )

    def compile(self, destination: str | Path) -> None:
        """Compile the schema to MessagePack file.

        Serializes the schema Bag to a MessagePack file for later loading
        by builders that use pre-compiled schemas.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self.bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)
