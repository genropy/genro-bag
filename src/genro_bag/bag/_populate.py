# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagPopulate mixin - initialization, population, copy and pickle for Bag.

Provides fill_from, from_url, deepcopy, pickle support, and update methods.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from genro_toolbox import safe_is_instance
from typing_extensions import Self

if TYPE_CHECKING:
    from genro_bag.bag._core import Bag

_IS_BAG = "genro_bag.bag._core.Bag"


class BagPopulate:
    """Mixin providing population, copy, pickle and update methods for Bag."""

    _nodes: Any
    _backref: Any
    parent: Any
    parent_node: Any

    if TYPE_CHECKING:
        def set_item(self, path: str, value: Any, _attributes: dict[Any, Any] | None = ..., node_position: str | int | None = ..., _updattr: bool = ..., _remove_null_attributes: bool = ..., _reason: str | None = ..., _fired: bool = ..., do_trigger: bool = ..., resolver: Any = ..., node_tag: str | None = ..., **kwargs: Any) -> Any: ...
        def set_backref(self, node: Any = ..., parent: Any = ...) -> None: ...
        def clear(self) -> None: ...
        def __iter__(self) -> Iterator: ...

    def fill_from(
        self, source: Any = None, transport: str | None = None
    ) -> Self:
        """Fill bag from a source and return self for chaining.

        Populates the bag with data from various sources:
        - None: No-op, returns self unchanged
        - dict: Keys become labels, values become node values
        - list: Items become numbered nodes (0, 1, 2, ...).
            Dict items in the list are converted to Bag.
        - Bag: Copy nodes from another Bag
        - str (file path): Load from file based on extension
        - str (XML inline): Detected by leading '<', parsed as XML
        - str (JSON inline): Detected by leading '{' or '[', parsed as JSON
        - bytes: Decoded to str, then detected as XML or JSON
        - Path: Load from file

        Existing nodes are cleared first (except when source is None).

        Args:
            source: Data source.
            transport: Force transport for file loading ('xml', 'json', 'msgpack').

        Returns:
            Self for method chaining.
        """
        if source is None:
            return self
        if safe_is_instance(source, _IS_BAG):
            self._fill_from_bag(source)
        elif isinstance(source, dict):
            self._fill_from_dict(source)
        elif isinstance(source, list):
            self._fill_from_list(source)
        elif isinstance(source, bytes):
            self.fill_from(source.decode("utf-8").strip())
        elif isinstance(source, Path):
            self._fill_from_file(str(source), transport=transport)
        elif isinstance(source, str):
            stripped = source.strip()
            if stripped.startswith("<"):
                loaded = self.__class__.from_xml(stripped)
                self._fill_from_bag(loaded)
            elif stripped.startswith("{") or stripped.startswith("["):
                loaded = self.__class__.from_json(stripped)
                self._fill_from_bag(loaded)
            else:
                self._fill_from_file(source, transport=transport)
        else:
            raise TypeError(
                f"fill_from: unsupported source type {type(source).__name__}"
            )
        return self

    def _fill_from_list(self, data: list) -> None:
        """Populate bag from a list. Items become numbered nodes."""
        self.clear()
        for i, item in enumerate(data):
            if isinstance(item, dict):
                item = self.__class__(item)
            self.set_item(str(i), item)

    def _fill_from_file(self, path: str, transport: str | None = None) -> None:
        """Load bag contents from a file.

        Detects transport from file extension (unless transport is specified):
        - .bag.json: TYTX JSON format
        - .bag.mp: TYTX MessagePack format
        - .xml: XML format (with auto-detect for legacy GenRoBag)

        Args:
            path: Path to the file to load.
            transport: Force transport ('xml', 'json', 'msgpack'). If None, detect from extension.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file extension is not recognized and format not specified.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        # Determine transport: explicit or from extension
        if transport is None:
            if path.endswith(".bag.json"):
                transport = "json"
            elif path.endswith(".bag.mp"):
                transport = "msgpack"
            elif path.endswith(".xml"):
                transport = "xml"
            else:
                raise ValueError(
                    f"Unrecognized file extension: {path}. Supported: .bag.json, .bag.mp, .xml"
                )

        # Load based on transport
        cls = self.__class__
        if transport == "json":
            with open(path, encoding="utf-8") as f:
                data = f.read()
            loaded = cls.from_tytx(data, transport="json")
            self._fill_from_bag(loaded)

        elif transport == "msgpack":
            with open(path, "rb") as f:
                data_bytes = f.read()
            loaded = cls.from_tytx(data_bytes, transport="msgpack")
            self._fill_from_bag(loaded)

        elif transport == "xml":
            with open(path, encoding="utf-8") as f:
                data = f.read()
            loaded = cls.from_xml(data)
            self._fill_from_bag(loaded)

    def _fill_from_bag(self, other: Bag) -> None:
        """Copy nodes from another Bag.

        Clears current contents and copies all nodes from the source Bag.

        Args:
            other: Source Bag to copy from.
        """
        self.clear()
        for node in other:
            # Deep copy the value if it's a Bag
            value = node.value
            if safe_is_instance(value, _IS_BAG):
                value = value.deepcopy()
            self.set_item(node.label, value, **dict(node.attr))

    def _fill_from_dict(self, data: dict[str, Any]) -> None:
        """Populate bag from a dictionary.

        Clears current contents and creates nodes from dict items.
        Nested dicts are converted to nested Bags.

        Args:
            data: Dict where keys become labels and values become node values.
        """
        self.clear()
        for key, value in data.items():
            if isinstance(value, dict):
                value = self.__class__(value)
            self.set_item(key, value)

    # -------------------- class methods --------------------------------

    @classmethod
    def from_url(cls, url: str, timeout: int = 30) -> Bag:
        """Load Bag from URL (classmethod, sync/async capable).

        Fetches content from URL and parses based on HTTP content-type header.
        Uses UrlResolver internally for DRY implementation.

        Args:
            url: HTTP/HTTPS URL to fetch.
            timeout: Request timeout in seconds. Default 30.

        Returns:
            Bag: Parsed content as Bag. Format auto-detected from content-type:
                - application/json, text/json -> from_json
                - application/xml, text/xml -> from_xml

        Raises:
            httpx.HTTPError: If HTTP request fails.
            ValueError: If content-type is not supported.

        Example:
            >>> # Sync context
            >>> bag = Bag.from_url('https://example.com/data.xml')
            >>>
            >>> # Async context
            >>> bag = await Bag.from_url('https://example.com/data.xml')
        """
        from genro_bag.resolvers import UrlResolver

        resolver = UrlResolver(url, timeout=timeout, as_bag=False)
        result = resolver()

        if asyncio.iscoroutine(result):
            async def _async_from_url():
                data = await result
                bag = cls()
                bag.fill_from(data)
                return bag
            return _async_from_url()  # type: ignore[return-value]

        bag = cls()
        bag.fill_from(result)
        return bag  # type: ignore[return-value]

    # -------------------- deepcopy --------------------------------

    def deepcopy(self) -> Self:
        """Return a deep copy of this Bag.

        Creates a new Bag with copies of all nodes. Nested Bags are
        recursively deep copied. Values are copied by reference unless
        they are Bags. Node attributes are copied as a new dict.

        Returns:
            A new Bag with copied nodes.

        Example:
            >>> bag = Bag({'a': 1, 'b': Bag({'c': 2})})
            >>> copy = bag.deepcopy()
            >>> copy['b.c'] = 3
            >>> bag['b.c']  # Original unchanged
            2
        """
        result = self.__class__()
        for node in self:
            value = node.static_value
            if safe_is_instance(value, _IS_BAG):
                value = value.deepcopy()
            result.set_item(node.label, value, _attributes=dict(node.attr))
        return result

    # -------------------- pickle support --------------------------------

    def __getstate__(self) -> dict:
        """Return state for pickling."""
        self._make_picklable()
        return self.__dict__

    def __setstate__(self, state: dict) -> None:
        """Restore state after unpickling."""
        self.__dict__.update(state)
        self._restore_from_picklable()

    def _make_picklable(self) -> None:
        """Prepare Bag for pickling (internal)."""
        if self._backref:
            self._backref = "x"
        self.parent = None
        self.parent_node = None
        for node in self:
            node._parent_bag = None
            value = node.static_value
            if safe_is_instance(value, _IS_BAG):
                value._make_picklable()

    def _restore_from_picklable(self) -> None:
        """Restore Bag from its picklable form (internal)."""
        if self._backref == "x":
            self.set_backref()
        else:
            for node in self:
                node._parent_bag = None
                value = node.static_value
                if safe_is_instance(value, _IS_BAG):
                    value._restore_from_picklable()

    # -------------------- update --------------------------------

    def update(self, source: Bag | dict, ignore_none: bool = False) -> None:
        """Update this Bag with nodes from source.

        Merges nodes from source into this Bag. For existing labels,
        updates the value and merges attributes. For new labels, adds
        the node.

        Args:
            source: A Bag or dict to merge from.
            ignore_none: If True, don't overwrite existing values with None.

        Example:
            >>> bag = Bag({'a': 1, 'b': 2})
            >>> bag.update({'a': 10, 'c': 3})
            >>> bag['a'], bag['b'], bag['c']
            (10, 2, 3)
        """
        # Normalize to list of (label, value, attr)
        items: list[tuple[Any, Any, dict[str, Any]]]
        if isinstance(source, dict):
            items = [(k, v, {}) for k, v in source.items()]
        else:
            items = list(source.query(what="#k,#v,#a"))

        for label, value, attr in items:
            if label in self._nodes:
                curr_node = self._nodes[label]
                curr_node.attr.update(attr)
                curr_value = curr_node.static_value
                if safe_is_instance(value, _IS_BAG) and safe_is_instance(curr_value, _IS_BAG):
                    curr_value.update(value, ignore_none=ignore_none)
                else:
                    if not ignore_none or value is not None:
                        curr_node.value = value
            else:
                self.set_item(label, value, _attributes=attr)
