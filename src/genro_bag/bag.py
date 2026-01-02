# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag module - main container class."""

from __future__ import annotations

from typing import Any

from .node_container import NodeContainer


class Bag:
    """Hierarchical data container with XML serialization capabilities.

    A Bag is an ordered container of BagNodes, accessible by label or position.
    Nested elements can be accessed with a path of keys joined with dots.
    """

    def __init__(self, source: dict[str, Any] | None = None):
        """Create a new Bag.

        Args:
            source: Optional dict to initialize from.
        """
        self._nodes: NodeContainer = NodeContainer()
        self._backref: bool = False
        self._parent: Bag | None = None
        self._parentNode: BagNode | None = None
        self._subscribers: dict[str, dict[str, Any]] = {
            'upd': {},
            'ins': {},
            'del': {},
        }

        if source:
            self._fill_from(source)

    def _fill_from(self, source: dict[str, Any]) -> None:
        """Fill bag from a dict source.

        Args:
            source: Dict to fill from.
        """
        # TODO: implementare quando avremo BagNode
        pass


# Forward reference per type hints
from .bag_node import BagNode  # noqa: E402, F401
