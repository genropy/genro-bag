# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagRepr mixin - string representation methods for Bag.

Provides __str__ and to_string for human-readable Bag output.
"""

from __future__ import annotations

from typing import Any


class BagRepr:
    """Mixin providing string representation methods for Bag.

    Assumes the presence of _nodes (BagNodeContainer) attribute.
    """

    _nodes: Any

    def __str__(self, _visited: dict | None = None) -> str:
        """Return formatted representation of bag contents.

        Uses static=True to avoid triggering resolvers.
        Handles circular references by tracking visited nodes.

        Example:
            >>> bag = Bag()
            >>> bag['name'] = 'test'
            >>> bag.set_item('count', 42, dtype='int')
            >>> print(bag)
            0 - (str) name: test
            1 - (int) count: 42  <dtype='int'>
        """
        if _visited is None:
            _visited = {}

        lines = []
        for idx, node in enumerate(self._nodes):
            value = node.get_value(static=True)

            # Format attributes
            attr = "<" + " ".join(f"{k}='{v}'" for k, v in node.attr.items()) + ">"
            if attr == "<>":
                attr = ""

            if hasattr(value, "_nodes") and hasattr(value, "backref"):
                node_id = id(node)
                backref = "(*)" if value.backref else ""
                lines.append(f"{idx} - ({value.__class__.__name__}) {node.label}{backref}: {attr}")
                if node_id in _visited:
                    lines.append(f"    visited at :{_visited[node_id]}")
                else:
                    _visited[node_id] = node.label
                    inner = value.__str__(_visited)
                    lines.extend(f"    {line}" for line in inner.split("\n"))
            else:
                # Format type name
                type_name = type(value).__name__
                if type_name == "NoneType":
                    type_name = "None"
                if "." in type_name:
                    type_name = type_name.split(".")[-1]
                # Handle bytes
                if isinstance(value, bytes):
                    value = value.decode("UTF-8", "ignore")
                lines.append(f"{idx} - ({type_name}) {node.label}: {value}  {attr}")

        return "\n".join(lines)

    def to_string(self, static: bool = True, _visited: dict | None = None, _prefix: str = "", _is_last: bool = True) -> str:
        """Return ASCII tree representation of bag contents.

        Args:
            static: If False, triggers resolvers to get current values.
            _visited: Internal - tracks visited nodes for circular refs.
            _prefix: Internal - indentation prefix for nested bags.
            _is_last: Internal - whether this is the last sibling.

        Example:
            >>> bag = Bag()
            >>> bag.set_item('user', inner_bag, name='John')
            >>> print(bag.to_string())
            user [name='John']
            ├── age: 30
            └── city: Rome
        """
        if _visited is None:
            _visited = {}

        lines = []
        nodes = list(self._nodes)

        for idx, node in enumerate(nodes):
            is_last = idx == len(nodes) - 1
            value = node.get_value(static=static)

            # Format attributes
            attrs = node.attr
            attr_str = ""
            if attrs:
                attr_str = " [" + ", ".join(f"{k}={repr(v)}" for k, v in attrs.items()) + "]"

            # Tree characters
            branch = "└── " if is_last else "├── "
            child_prefix = _prefix + ("    " if is_last else "│   ")

            if hasattr(value, "_nodes") and hasattr(value, "backref"):
                node_id = id(node)
                backref = "(*)" if value.backref else ""

                if node_id in _visited:
                    lines.append(f"{_prefix}{branch}{node.label}{backref}{attr_str} → (circular ref)")
                else:
                    _visited[node_id] = node.label
                    lines.append(f"{_prefix}{branch}{node.label}{backref}{attr_str}")
                    inner = value.to_string(static=static, _visited=_visited, _prefix=child_prefix, _is_last=is_last)
                    if inner:
                        lines.append(inner)
            else:
                # Format value representation
                if value is None:
                    value_str = "None"
                elif isinstance(value, bytes):
                    value_str = value.decode("UTF-8", "ignore")
                elif isinstance(value, str) and len(value) > 50:
                    value_str = repr(value[:47] + "...")
                else:
                    value_str = repr(value) if isinstance(value, str) else str(value)

                lines.append(f"{_prefix}{branch}{node.label}: {value_str}{attr_str}")

        return "\n".join(lines)
