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
    """Mixin providing population, copy, pickle and update methods for Bag.

    Supports fill_from with multiple sources (dict, list, file path, XML/JSON
    string, another Bag), plus deepcopy, pickle, and update semantics.
    """

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

        Atomic semantics (issue #44):
            The new content is built into an offline orphan Bag first; the
            node containers are then swapped atomically. If the source fails
            to parse, self stays unchanged — never partially populated. When
            self is attached with backref, observers see a single upd_value
            event with oldvalue = orphan Bag carrying the previous content.

        Args:
            source: Data source.
            transport: Force transport for file loading ('xml', 'json', 'msgpack').

        Returns:
            Self for method chaining.
        """
        if source is None:
            return self

        # 1. Build the new content offline in an orphan Bag (no events emitted
        #    since the new bag has no parent and no backref).
        new_bag = self.__class__()
        self._populate_into(new_bag, source, transport=transport)

        # 2. Orphan the current nodes: detach them from self before the swap.
        #    BagNode.orphaned() clears _parent_bag and recursively clear_backref
        #    on any nested Bag value — mirrors the JS legacy helper.
        for node in list(self._nodes):
            node.orphaned()

        # 3. Swap the containers atomically.
        old_nodes = self._nodes
        self._nodes = new_bag._nodes
        new_bag._nodes = old_nodes

        # 4. Adopt the new nodes through the parent_bag setter, which
        #    propagates set_backref recursively to nested Bag values when
        #    self has backref. For orphan self this is a plain re-pointer.
        for node in self._nodes:
            node.parent_bag = self

        # 5. Place the old nodes inside new_bag as a navigable snapshot.
        #    new_bag is orphan (no backref, no parent), so assigning directly
        #    to _parent_bag is enough and avoids firing any event.
        for node in new_bag._nodes:
            node._parent_bag = new_bag

        # 6. Emit a single atomic upd_value event on the parent when attached.
        if self.backref and self.parent is not None and self.parent_node is not None:
            self.parent._on_node_changed(
                self.parent_node,
                [self.parent_node.label],
                evt="upd_value",
                oldvalue=new_bag,
            )

        return self

    def _populate_into(
        self, target: Bag, source: Any, transport: str | None = None
    ) -> None:
        """Dispatch source decoding and populate target in place.

        Target can be self (default populate path) or an offline orphan Bag
        (atomic fill_from path): the helpers that actually write nodes
        operate on `target`, leaving self untouched.
        """
        if safe_is_instance(source, _IS_BAG):
            self._fill_from_bag(source, target)
        elif isinstance(source, dict):
            self._fill_from_dict(source, target)
        elif isinstance(source, list):
            self._fill_from_list(source, target)
        elif isinstance(source, bytes):
            self._populate_into(target, source.decode("utf-8").strip(), transport)
        elif isinstance(source, Path):
            self._fill_from_file(str(source), target, transport=transport)
        elif isinstance(source, str):
            stripped = source.strip()
            if stripped.startswith("<"):
                loaded = self.__class__.from_xml(stripped)
                self._fill_from_bag(loaded, target)
            elif stripped.startswith("{") or stripped.startswith("["):
                loaded = self.__class__.from_json(stripped)
                self._fill_from_bag(loaded, target)
            else:
                self._fill_from_file(source, target, transport=transport)
        else:
            raise TypeError(
                f"fill_from: unsupported source type {type(source).__name__}"
            )

    def _fill_from_list(self, data: list, target: Bag) -> None:
        """Populate target from a list. Items become numbered nodes."""
        target.clear()
        for i, item in enumerate(data):
            if isinstance(item, dict):
                item = self.__class__(item)
            target.set_item(str(i), item)

    def _fill_from_file(
        self, path: str, target: Bag, transport: str | None = None
    ) -> None:
        """Load bag contents from a file into target.

        Detects transport from file extension (unless transport is specified):
        - .bag.json: TYTX JSON format
        - .bag.mp: TYTX MessagePack format
        - .xml: XML format (with auto-detect for legacy GenRoBag)

        Args:
            path: Path to the file to load.
            target: Bag to populate.
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
            self._fill_from_bag(loaded, target)

        elif transport == "msgpack":
            with open(path, "rb") as f:
                data_bytes = f.read()
            loaded = cls.from_tytx(data_bytes, transport="msgpack")
            self._fill_from_bag(loaded, target)

        elif transport == "xml":
            with open(path, encoding="utf-8") as f:
                data = f.read()
            loaded = cls.from_xml(data)
            self._fill_from_bag(loaded, target)

    def _fill_from_bag(self, other: Bag, target: Bag) -> None:
        """Copy nodes from another Bag into target.

        Clears target's current contents first and copies all nodes from the
        source Bag.

        Args:
            other: Source Bag to copy from.
            target: Bag to populate.
        """
        target.clear()
        for node in other:
            # Deep copy the value if it's a Bag
            value = node.value
            if safe_is_instance(value, _IS_BAG):
                value = value.deepcopy()
            target.set_item(node.label, value, **dict(node.attr))

    def _fill_from_dict(
        self, data: dict[str, Any], target: Bag
    ) -> None:
        """Populate target from a dictionary.

        Clears target's current contents first and creates nodes from dict items.
        Nested dicts are converted to nested Bags.

        Args:
            data: Dict where keys become labels and values become node values.
            target: Bag to populate.
        """
        target.clear()
        for key, value in data.items():
            if isinstance(value, dict):
                value = self.__class__(value)
            target.set_item(key, value)

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
