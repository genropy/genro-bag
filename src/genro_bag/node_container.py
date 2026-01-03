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

"""NodeContainer: Ordered container for BagNodes with positional insert and reordering."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class NodeContainer:
    """Ordered container for BagNodes with positional insert and reordering.

    NodeContainer combines dict-like access with list-like ordering. Elements can be
    accessed by label, numeric index, or '#n' string index. Supports positional
    insertion and element reordering without removal.

    Note:
        This class is tightly coupled with BagNode. It assumes elements have
        `.label` and `.attr` attributes (as BagNode does). This is intentional:
        NodeContainer is designed specifically to hold BagNodes and is not meant
        to be a general-purpose container.

    Internal structure:
        _dict: maps label -> value (for O(1) lookup by label)
        _list: contains values in order (for O(1) access by index)
    """

    def __init__(self, data: dict[str, Any] | None = None):
        """Create a NodeContainer.

        Args:
            data: Optional dict to initialize from.
        """
        self._dict: dict[str, Any] = {}
        self._list: list[Any] = []

        if data:
            for key, value in data.items():
                self._dict[key] = value
                self._list.append(value)

    def index(self, label: str) -> int:
        """Return the index of a label in this container.

        Args:
            label: The label or index syntax to look up.

        Returns:
            Index position (0-based), or -1 if not found.
        """
        import re
        if label in self._dict:
            return next((i for i, node in enumerate(self._list) if node.label == label), -1)
        if m := re.match(r'^#(\d+)$', label):
            idx = int(m.group(1))
            return idx if idx < len(self._list) else -1
        if '=' in label:
            attr, value = label[1:].split('=', 1)
            if attr:
                return next((i for i, node in enumerate(self._list) if node.attr.get(attr) == value), -1)
            else:
                return next((i for i, node in enumerate(self._list) if node._value == value), -1)

    def _parse_position(self, position: str | int | None) -> int:
        """Parse position syntax and return insertion index.

        Args:
            position: Position specification. Supported formats:
                - None or '>': append at end
                - '<': insert at beginning
                - int: insert at this index (clamped to valid range)
                - '#n': insert at index n
                - '<label': insert before label
                - '>label': insert after label
                - '<#n': insert before index n
                - '>#n': insert after index n

        Returns:
            Index where to insert (always valid for list.insert).
        """
        if position is None or position == '>':
            return len(self._list)

        if isinstance(position, int):
            return max(0, min(position, len(self._list)))

        if position == '<':
            return 0

        if position.startswith('#'):
            try:
                return max(0, min(int(position[1:]), len(self._list)))
            except ValueError:
                return len(self._list)

        if position.startswith('<'):
            ref = position[1:]
            if ref.startswith('#'):
                try:
                    return max(0, min(int(ref[1:]), len(self._list)))
                except ValueError:
                    return len(self._list)
            idx = self.index(ref)
            return idx if idx >= 0 else len(self._list)

        if position.startswith('>'):
            ref = position[1:]
            if ref.startswith('#'):
                try:
                    return max(0, min(int(ref[1:]) + 1, len(self._list)))
                except ValueError:
                    return len(self._list)
            idx = self.index(ref)
            return idx + 1 if idx >= 0 else len(self._list)

        return len(self._list)

    def __getitem__(self, key: str | int) -> Any:
        """Get item by label, index, or '#n'."""
        if isinstance(key, int):
            if 0 <= key < len(self._list):
                return self._list[key]
            return None

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                if 0 <= idx < len(self._list):
                    return self._list[idx]
            except ValueError:
                pass
            return None

        return self._dict.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item. For positional insert, use set()."""
        if key in self._dict:
            old_value = self._dict[key]
            idx = self._list.index(old_value)
            self._list[idx] = value
            self._dict[key] = value
        else:
            self._dict[key] = value
            self._list.append(value)

    def __delitem__(self, key: str | int) -> None:
        """Delete item by label, index, or '#n'."""
        if isinstance(key, int):
            if 0 <= key < len(self._list):
                value = self._list[key]
                del self._dict[value.label]
                self._list.remove(value)
            return

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                if 0 <= idx < len(self._list):
                    value = self._list[idx]
                    del self._dict[value.label]
                    self._list.remove(value)
            except ValueError:
                pass
            return

        if key in self._dict:
            value = self._dict[key]
            del self._dict[key]
            self._list.remove(value)

    def __contains__(self, key: str | int) -> bool:
        """Check if key exists."""
        if isinstance(key, int):
            return 0 <= key < len(self._list)

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                return 0 <= idx < len(self._list)
            except ValueError:
                return False

        return key in self._dict

    def __len__(self) -> int:
        """Return number of elements."""
        return len(self._list)

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys in order."""
        return (v.label for v in self._list)

    def get(self, key: str | int, default: Any = None) -> Any:
        """Get item with default.

        Note: Cannot distinguish between 'key not found' and 'value is None'.
        If the stored value is None, default will be returned instead.
        """
        result = self[key]
        return result if result is not None else default

    def set(self, key: str, value: Any, _position: str | int | None = '>') -> None:
        """Set item with optional position.

        Args:
            key: The label.
            value: The value.
            _position: Position specification (>, <, #n, <label, >label, etc.)
        """
        if key in self._dict:
            old_value = self._dict[key]
            idx = self._list.index(old_value)
            self._list[idx] = value
            self._dict[key] = value
        else:
            idx = self._parse_position(_position)
            self._dict[key] = value
            self._list.insert(idx, value)

    def _parse_what(self, what: str | int | list) -> list[Any]:
        """Parse 'what' argument for move/clone into list of values.

        Args:
            what: Can be label, index, '#n', comma-separated string, or list.

        Returns:
            List of values in their current order.
        """
        refs: list[str | int] = []

        if isinstance(what, list):
            refs = what
        elif isinstance(what, int):
            refs = [what]
        elif isinstance(what, str) and ',' in what:
            refs = [r.strip() for r in what.split(',')]
        else:
            refs = [what]

        values = []
        for ref in refs:
            value = self[ref]
            if value is not None and value not in values:
                values.append(value)

        return sorted(values, key=lambda x: self._list.index(x))

    def move(self, what: str | int | list, position: str) -> None:
        """Move element(s) to a new position.

        Args:
            what: Element(s) to move. Can be label, index, '#n',
                  comma-separated string, or list of references.
            position: Destination using _position syntax.
        """
        values = self._parse_what(what)

        for value in values:
            self._list.remove(value)

        target_idx = self._parse_position(position)

        for i, value in enumerate(values):
            self._list.insert(target_idx + i, value)

    def pop(self, key: str | int, *default: Any) -> Any:
        """Remove and return item.

        Args:
            key: Label, index, or '#n'.
            default: Optional default if not found.

        Returns:
            The value, or default if provided and not found.
        """
        value = self[key]

        if value is not None:
            del self._dict[value.label]
            self._list.remove(value)
            return value

        if default:
            return default[0]

        return None

    def clear(self) -> None:
        """Remove all elements."""
        self._dict.clear()
        self._list.clear()

    def keys(self, iter: bool = False) -> list[str] | Iterator[str]:
        """Return keys in order.

        Args:
            iter: If True, return iterator instead of list.

        Returns:
            List or iterator of keys.
        """
        if iter:
            return (v.label for v in self._list)
        return [v.label for v in self._list]

    def values(self, iter: bool = False) -> list[Any] | Iterator[Any]:
        """Return values in order.

        Args:
            iter: If True, return iterator instead of list.

        Returns:
            List or iterator of values.
        """
        if iter:
            return (v for v in self._list)
        return list(self._list)

    def items(self, iter: bool = False) -> list[tuple[str, Any]] | Iterator[tuple[str, Any]]:
        """Return (key, value) pairs in order.

        Args:
            iter: If True, return iterator instead of list.

        Returns:
            List or iterator of (key, value) tuples.
        """
        if iter:
            return ((v.label, v) for v in self._list)
        return [(v.label, v) for v in self._list]

    def update(self, other: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Update from dict or kwargs.

        Existing keys: overwrite value, preserve position.
        New keys: append at end.
        """
        items = {}
        if other:
            items.update(other)
        items.update(kwargs)

        for key, value in items.items():
            if key in self._dict:
                old_value = self._dict[key]
                idx = self._list.index(old_value)
                self._list[idx] = value
                self._dict[key] = value
            else:
                self._dict[key] = value
                self._list.append(value)

    def clone(self, selector: str | list | Callable[[str, Any], bool] | None = None) -> NodeContainer:
        """Create a clone with selected elements.

        Args:
            selector: Can be:
                - None: clone all
                - str: comma-separated references ('a,b,#2')
                - list: list of references ([1, 'b', '#2'])
                - callable: function(key, value) -> bool

        Returns:
            New NodeContainer with selected elements in original order.
        """
        result = NodeContainer()

        if selector is None:
            for value in self._list:
                result._dict[value.label] = value
                result._list.append(value)
        elif callable(selector):
            for value in self._list:
                if selector(value.label, value):
                    result._dict[value.label] = value
                    result._list.append(value)
        else:
            for value in self._parse_what(selector):
                result._dict[value.label] = value
                result._list.append(value)

        return result
