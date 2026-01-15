# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagQuery mixin - query and iteration methods for Bag.

This module provides the BagQuery mixin class with methods for querying,
iterating, and aggregating Bag contents.

Methods provided:
    - query(): Main query method with filtering, deep traversal, limit
    - digest(): Backward-compatible alias for query()
    - columns(): Return query result as columns
    - sum(): Sum values or attributes
    - walk(): Depth-first tree traversal
    - get_nodes(): Get filtered list of nodes
    - get_node_by_attr(): Find node by attribute value
    - get_node_by_value(): Find node by value content
    - keys(), values(), items(): Dict-like iteration
    - is_empty(): Check if bag is empty
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bag import Bag
    from .bagnode import BagNode


class BagQuery:
    """Mixin class providing query and iteration methods for Bag.

    This mixin is inherited by Bag and provides all query-related functionality.
    It assumes the presence of _nodes (BagNodeContainer) attribute.
    """

    # Type hints for attributes provided by Bag
    _nodes: Any

    def keys(self, iter: bool = False) -> list[str] | Iterator[str]:
        """Return node labels in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iterkeys() from Python 2 - use keys(iter=True) instead.
        """
        return self._nodes.keys(iter=iter)  # type: ignore[no-any-return]

    def values(self, iter: bool = False) -> list[Any] | Iterator[Any]:
        """Return node values in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces itervalues() from Python 2 - use values(iter=True) instead.
        """
        return self._nodes.values(iter=iter)  # type: ignore[no-any-return]

    def items(self, iter: bool = False) -> list[tuple[str, Any]] | Iterator[tuple[str, Any]]:
        """Return (label, value) tuples in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iteritems() from Python 2 - use items(iter=True) instead.
        """
        return self._nodes.items(iter=iter)  # type: ignore[no-any-return]

    def get_nodes(self, condition: Callable[[BagNode], bool] | None = None) -> list[BagNode]:
        """Get the actual list of nodes contained in the Bag.

        The get_nodes method works as the filter of a list.

        Args:
            condition: Optional callable that takes a BagNode and returns bool.

        Returns:
            List of BagNodes, optionally filtered by condition.
        """
        if not condition:
            return list(self._nodes)
        return [n for n in self._nodes if condition(n)]

    def get_node_by_attr(self, attr: str, value: Any) -> BagNode | None:
        """Return the first BagNode with the requested attribute value.

        Search strategy (hybrid depth-first with level priority):
        1. First checks all direct children of current Bag
        2. Then recursively searches into sub-Bags (depth-first)

        This means a match at the current level is always found before
        descending into nested Bags, but once descent begins, it proceeds
        depth-first through the subtree before checking siblings.

        Args:
            attr: Attribute name to search.
            value: Attribute value to match.

        Returns:
            BagNode if found, None otherwise.
        """
        # Import here to avoid circular import
        from .bag import Bag

        sub_bags = []
        for node in self._nodes:
            if node.has_attr(attr, value):
                return node  # type: ignore[no-any-return]
            if isinstance(node.value, Bag):
                sub_bags.append(node)

        for node in sub_bags:
            found = node.value.get_node_by_attr(attr, value)
            if found:
                return found  # type: ignore[no-any-return]

        return None

    def get_node_by_value(self, key: str, value: Any) -> BagNode | None:
        """Return the first BagNode whose value contains key=value.

        Searches only direct children (not recursive).
        The node's value must be dict-like (Bag or dict).

        Args:
            key: Key to look for in node.value.
            value: Value to match.

        Returns:
            BagNode if found, None otherwise.
        """
        for node in self._nodes:
            node_value = node.value
            if node_value and node_value.get(key) == value:
                return node  # type: ignore[no-any-return]
        return None

    def is_empty(self, zero_is_none: bool = False, blank_is_none: bool = False) -> bool:
        """Check if the Bag is empty.

        A node is considered non-empty if:
        - It has a resolver (even if static value is None, the resolver
          represents potential content that can be loaded)
        - It has a non-None static value (unless zero_is_none/blank_is_none apply)

        This method never triggers resolver I/O - it only checks static values
        and resolver presence.

        Args:
            zero_is_none: If True, treat 0 values as empty.
            blank_is_none: If True, treat blank strings as empty.

        Returns:
            True if Bag is empty according to criteria, False otherwise.
        """
        if len(self._nodes) == 0:
            return True

        for node in self._nodes:
            # A node with a resolver is not empty (has potential content)
            if node._resolver is not None:
                return False
            v = node.get_value(static=True)
            if v is None:
                continue
            if zero_is_none and v == 0:
                continue
            if blank_is_none and v == "":
                continue
            return False

        return True

    def walk(
        self, callback: Callable[[BagNode], Any] | None = None, static: bool = True, **kwargs
    ) -> Iterator[tuple[str, BagNode]] | Any:
        """Walk the tree depth-first.

        Two modes of operation:

        1. **Generator mode** (no callback): Returns a generator yielding
           (path, node) tuples for all nodes in the tree. Always uses static
           mode (no resolver triggering). This is the recommended approach.

        2. **Legacy callback mode**: Calls callback(node, **kwargs) for each
           node. Supports early exit (if callback returns truthy value),
           _pathlist and _indexlist kwargs for path tracking.

        Args:
            callback: If None, return generator of (path, node) tuples.
                If provided, call callback(node, **kwargs) for each node.
            static: If True (default), don't trigger resolvers during traversal.
                If False, resolvers may be triggered to compute nested Bag values.
                Ignored in generator mode (always static).
            **kwargs: Passed to callback. Special keys:
                - _pathlist: list of labels from root (auto-updated by walk)
                - _indexlist: list of indices from root (auto-updated by walk)

        Returns:
            Generator of (path, node) if callback is None.
            If callback provided: value returned by callback if truthy, else None.

        Examples:
            >>> # Generator mode (modern, recommended)
            >>> for path, node in bag.walk():
            ...     print(f"{path}: {node.value}")

            >>> # Early exit with generator
            >>> for path, node in bag.walk():
            ...     if node.get_attr('id') == 'target':
            ...         found = node
            ...         break

            >>> # Legacy callback mode with path tracking
            >>> def my_cb(node, _pathlist=None, **kw):
            ...     print('.'.join(_pathlist))
            >>> bag.walk(my_cb, _pathlist=[])
        """
        # Import here to avoid circular import
        from .bag import Bag

        if callback is not None:
            # Legacy callback mode
            for idx, node in enumerate(self._nodes):
                kw = dict(kwargs)
                if "_pathlist" in kwargs:
                    kw["_pathlist"] = kwargs["_pathlist"] + [node.label]
                if "_indexlist" in kwargs:
                    kw["_indexlist"] = kwargs["_indexlist"] + [idx]

                result = callback(node, **kw)
                if result:
                    return result

                value = node.get_value(static=static)
                if isinstance(value, Bag):
                    result = value.walk(callback, static=static, **kw)
                    if result:
                        return result
            return None

        # Generator mode - always uses static=True to avoid triggering resolvers
        def _walk_gen(bag: Bag, prefix: str) -> Iterator[tuple[str, BagNode]]:
            for node in bag._nodes:
                path = f"{prefix}.{node.label}" if prefix else node.label
                yield path, node
                value = node.get_value(static=True)
                if isinstance(value, Bag):
                    yield from _walk_gen(value, path)

        return _walk_gen(self, "")  # type: ignore[arg-type]

    def query(
        self,
        what: str | list | None = None,
        condition: Callable[[BagNode], bool] | None = None,
        iter: bool = False,
        deep: bool = False,
        leaf: bool = True,
        branch: bool = True,
        limit: int | None = None,
    ) -> list | Iterator:
        """Query Bag elements, extracting specified data.

        Args:
            what: String of special keys separated by comma, or list of keys.
                Special keys:
                - '#k': label of each item
                - '#v': value of each item
                - '#v.path': inner values of each item
                - '#__v': static value (bypassing resolver)
                - '#a': all attributes of each item
                - '#a.attrname': specific attribute for each item
                - '#p': path (full path from root, useful with deep=True)
                - '#n': node (the BagNode itself)
                - callable: custom function applied to each node
            condition: Optional callable filter (receives BagNode, returns bool).
            iter: If True, return a generator instead of a list.
            deep: If True, traverse recursively (depth-first) instead of first level only.
            leaf: If True (default), include leaf nodes (non-Bag values).
            branch: If True (default), include branch nodes (Bag values).
            limit: Maximum number of results to return. None means no limit.

        Returns:
            List of tuples, or generator if iter=True.

        Examples:
            >>> bag.query('#k,#a.createdOn,#a.createdBy')
            [('letter_to_mark', '10-7-2003', 'Jack'), ...]

            >>> # Recursive path list (like getIndex)
            >>> bag.query('#p', deep=True)
            ['a', 'b', 'b.c', 'b.d']

            >>> # Only leaves (like getLeaves)
            >>> bag.query('#p,#v', deep=True, branch=False)

            >>> # Only branches
            >>> bag.query('#p', deep=True, leaf=False)

            >>> # First matching node (like findNodeByAttr)
            >>> bag.query('#n', deep=True, condition=lambda n: n.get_attr('id') == '123', limit=1)

            >>> # Recursive iterator
            >>> for path, val in bag.query('#p,#v', deep=True, iter=True):
            ...     print(f"{path} = {val}")
        """
        # Import here to avoid circular import
        from .bag import Bag

        if not what:
            what = "#k,#v,#a"
        if isinstance(what, str):
            if ":" in what:
                where, what = what.split(":")
                obj = self[where]  # type: ignore[index]
            else:
                obj = self
            whatsplit = [x.strip() for x in what.split(",")]
        else:
            whatsplit = what
            obj = self

        def _extract_value(node: BagNode, w: str, path: str, is_deep: bool) -> Any:
            """Extract a single value from a node based on what specifier."""
            if w == "#k":
                return node.label
            elif w == "#p":
                return path
            elif w == "#n":
                return node
            elif callable(w):
                return w(node)
            elif w == "#v":
                v = node.static_value
                # With deep=True, Bag values return None (content comes in later iterations)
                return None if is_deep and isinstance(v, Bag) else v
            elif w.startswith("#v."):
                inner_path = w.split(".", 1)[1]
                return node.value[inner_path] if hasattr(node.value, "get_item") else None
            elif w == "#__v":
                return node.static_value
            elif w.startswith("#a"):
                attr = w.split(".", 1)[1] if "." in w else None
                return node.get_attr(attr)
            else:
                return node.value[w] if hasattr(node.value, "__getitem__") else None

        def _should_include(node: BagNode) -> bool:
            """Check if node should be included based on leaf/branch filters."""
            is_branch = isinstance(node.static_value, Bag)
            if is_branch and not branch:
                return False
            if not is_branch and not leaf:
                return False
            return condition is None or condition(node)

        def _iter_digest() -> Iterator:
            """Generator that yields tuples for each node."""
            count = 0
            if deep:
                # Use walk() for recursive traversal
                for path, node in obj.walk():
                    if _should_include(node):
                        if len(whatsplit) == 1:
                            yield _extract_value(node, whatsplit[0], path, True)
                        else:
                            yield tuple(_extract_value(node, w, path, True) for w in whatsplit)
                        count += 1
                        if limit is not None and count >= limit:
                            return
            else:
                # First level only
                for node in obj._nodes:
                    if _should_include(node):
                        path = node.label
                        if len(whatsplit) == 1:
                            yield _extract_value(node, whatsplit[0], path, False)
                        else:
                            yield tuple(_extract_value(node, w, path, False) for w in whatsplit)
                        count += 1
                        if limit is not None and count >= limit:
                            return

        if iter:
            return _iter_digest()

        return list(_iter_digest())

    def digest(
        self,
        what: str | list | None = None,
        condition: Callable[[BagNode], bool] | None = None,
        as_columns: bool = False,
    ) -> list:
        """Return a list of tuples with keys/values/attributes (backward compatible).

        This is an alias for query() with iter=False, deep=False for backward
        compatibility. Use query() for new code.

        Args:
            what: String of special keys separated by comma, or list of keys.
            condition: Optional callable filter (receives BagNode, returns bool).
            as_columns: If True, return list of lists (transposed).

        Returns:
            List of tuples (or list of lists if as_columns=True).
        """
        result = self.query(what, condition, iter=False, deep=False)
        if as_columns:
            if not result:
                what_str = what if isinstance(what, str) else "#k,#v,#a"
                whatsplit = [x.strip() for x in what_str.split(",")]
                return [[] for _ in whatsplit]
            result_list = list(result)  # type: ignore[arg-type]
            if result_list and isinstance(result_list[0], tuple):
                return [list(col) for col in zip(*result_list, strict=False)]
            return [result_list]
        return list(result)  # type: ignore[arg-type]

    def columns(self, cols: str | list, attr_mode: bool = False) -> list:
        """Return digest result as columns.

        Args:
            cols: Column names as comma-separated string or list.
            attr_mode: If True, prefix columns with '#a.' for attribute access.

        Returns:
            List of lists (columns).
        """
        if isinstance(cols, str):
            cols = cols.split(",")
        mode = ""
        if attr_mode:
            mode = "#a."
        what = ",".join([f"{mode}{col}" for col in cols])
        return self.digest(what, as_columns=True)

    def sort(self, key: str | Callable = "#k:a") -> Any:
        """Sort nodes in place.

        Args:
            key: Sort specification string or callable.
                If callable, used directly as key function for sort.
                If string, format is 'criterion:mode' or multiple 'c1:m1,c2:m2'.

                Criteria:
                - '#k': sort by label
                - '#v': sort by value
                - '#a.attrname': sort by attribute
                - 'fieldname': sort by field in value (if value is dict/Bag)

                Modes:
                - 'a': ascending, case-insensitive (default)
                - 'A': ascending, case-sensitive
                - 'd': descending, case-insensitive
                - 'D': descending, case-sensitive

        Returns:
            Self (for chaining).

        Examples:
            >>> bag.sort('#k')           # by label ascending
            >>> bag.sort('#k:d')         # by label descending
            >>> bag.sort('#v:A')         # by value ascending, case-sensitive
            >>> bag.sort('#a.name:a')    # by attribute 'name'
            >>> bag.sort('field:d')      # by field in value
            >>> bag.sort('#k:a,#v:d')    # multi-level sort
            >>> bag.sort(lambda n: n.value)  # custom key function
        """

        def sort_key(value: Any, case_insensitive: bool) -> tuple:
            """Create sort key handling None and case sensitivity."""
            if value is None:
                return (1, "")  # None values sort last
            if case_insensitive and isinstance(value, str):
                return (0, value.lower())
            return (0, value)

        if callable(key):
            self._nodes._list.sort(key=key)
        else:
            levels = key.split(",")
            levels.reverse()  # process in reverse for stable multi-level sort
            for level in levels:
                if ":" in level:
                    what, mode = level.split(":", 1)
                else:
                    what = level
                    mode = "a"
                what = what.strip()
                mode = mode.strip()

                reverse = mode in ("d", "D")
                case_insensitive = mode in ("a", "d")

                if what.lower() == "#k":
                    self._nodes._list.sort(
                        key=lambda n: sort_key(n.label, case_insensitive), reverse=reverse
                    )
                elif what.lower() == "#v":
                    self._nodes._list.sort(
                        key=lambda n: sort_key(n.value, case_insensitive), reverse=reverse
                    )
                elif what.lower().startswith("#a."):
                    attrname = what[3:]
                    self._nodes._list.sort(
                        key=lambda n, attr=attrname: sort_key(n.get_attr(attr), case_insensitive),
                        reverse=reverse,
                    )
                else:
                    # Sort by field in value
                    self._nodes._list.sort(
                        key=lambda n, field=what: sort_key(
                            n.value[field] if n.value else None, case_insensitive
                        ),
                        reverse=reverse,
                    )
        return self

    def sum(
        self,
        what: str = "#v",
        condition: Callable[[BagNode], bool] | None = None,
        deep: bool = False,
    ) -> float | list[float]:
        """Sum values or attributes.

        Args:
            what: What to sum (same syntax as query).
                - '#v': sum values
                - '#a.attrname': sum attribute
                - '#v,#a.price': multiple sums (returns list)
            condition: Optional callable filter (receives BagNode, returns bool).
            deep: If True, recursively sum through nested Bags.

        Returns:
            Sum as float, or list of floats if multiple what specs.

        Examples:
            >>> bag.sum()                    # sum all values
            >>> bag.sum('#a.price')          # sum 'price' attribute
            >>> bag.sum('#v,#a.qty')         # [sum_values, sum_qty]
            >>> bag.sum('#v', condition=lambda n: n.get_attr('active'))  # filtered sum
            >>> bag.sum('#a.qty', deep=True)  # recursive sum (replaces summarizeAttributes)
        """
        if "," in what:
            return [
                sum(v or 0 for v in self.query(w.strip(), condition, deep=deep))
                for w in what.split(",")
            ]
        return sum(v or 0 for v in self.query(what, condition, deep=deep))
