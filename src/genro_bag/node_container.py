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

    def _get_label(self, value: Any) -> str | None:
        """Get label for a value by searching _dict.

        Args:
            value: The value to find.

        Returns:
            The label, or None if not found.
        """
        for k, v in self._dict.items():
            if v is value:
                return k
        return None

    def _resolve_key(self, key: str | int) -> str | None:
        """Resolve a key to a label.

        Args:
            key: Can be label (str), index (int), or '#n' (str).

        Returns:
            The label string, or None if not found.
        """
        if isinstance(key, int):
            if 0 <= key < len(self._list):
                return self._get_label(self._list[key])
            return None

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                if 0 <= idx < len(self._list):
                    return self._get_label(self._list[idx])
            except ValueError:
                pass
            return None

        return key if key in self._dict else None

    def _resolve_index(self, key: str | int) -> int:
        """Resolve a key to an index.

        Args:
            key: Can be label (str), index (int), or '#n' (str).

        Returns:
            The index, or -1 if not found.
        """
        if isinstance(key, int):
            return key if 0 <= key < len(self._list) else -1

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                return idx if 0 <= idx < len(self._list) else -1
            except ValueError:
                return -1

        if key in self._dict:
            value = self._dict[key]
            try:
                return self._list.index(value)
            except ValueError:
                return -1
        return -1

    def _parse_position(self, position: str | int | None) -> int:
        """Parse position syntax and return insertion index.

        Args:
            position: Position specification.

        Returns:
            Index where to insert.
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
            idx = self._resolve_index(ref)
            return idx if idx >= 0 else len(self._list)

        if position.startswith('>'):
            ref = position[1:]
            if ref.startswith('#'):
                try:
                    return max(0, min(int(ref[1:]) + 1, len(self._list)))
                except ValueError:
                    return len(self._list)
            idx = self._resolve_index(ref)
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
                label = self._get_label(value)
                if label:
                    del self._dict[label]
                self._list.remove(value)
            return

        if isinstance(key, str) and key.startswith('#'):
            try:
                idx = int(key[1:])
                if 0 <= idx < len(self._list):
                    value = self._list[idx]
                    label = self._get_label(value)
                    if label:
                        del self._dict[label]
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
        return (self._get_label(v) for v in self._list)

    def get(self, key: str | int, default: Any = None) -> Any:
        """Get item with default."""
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
            label = self._get_label(value)
            if label:
                del self._dict[label]
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
            return (self._get_label(v) for v in self._list)
        return [self._get_label(v) for v in self._list]

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
            return ((self._get_label(v), v) for v in self._list)
        return [(self._get_label(v), v) for v in self._list]

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
                label = self._get_label(value)
                result._dict[label] = value
                result._list.append(value)
        elif callable(selector):
            for value in self._list:
                label = self._get_label(value)
                if selector(label, value):
                    result._dict[label] = value
                    result._list.append(value)
        else:
            values = self._parse_what(selector)
            for value in values:
                label = self._get_label(value)
                result._dict[label] = value
                result._list.append(value)

        return result
