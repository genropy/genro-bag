# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagQuery mixin - query and iteration methods for Bag.

This module provides the BagQuery mixin class with methods for querying,
iterating, and aggregating Bag contents.

Methods provided:
    - query(): Main query method with filtering, deep traversal, limit
    - digest(): Backward-compatible alias for query()
    - columns(): Return query result as columns
    - sum(): Sum values or attributes
    - for_each(): Callback traversal; traverse(): Node iterator
    - get_nodes(): Get filtered list of nodes
    - get_node_by_attr(): Find node by attribute value
    - get_node_by_value(): Find node by value content
    - keys(), values(), items(): Dict-like iteration
    - is_empty(): Check if bag is empty
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from numbers import Number
from typing import TYPE_CHECKING, Any

from genro_toolbox import safe_is_instance

if TYPE_CHECKING:
    from genro_bag.bagnode import BagNode, BagNodeContainer

_IS_BAG = "genro_bag.bag._core.Bag"


class BagQuery:
    """Mixin providing query, iteration and aggregation methods for Bag.

    Includes depth-first traversal, query/digest (filtering with deep
    option), dict-like keys/values/items, and node lookup by attr or value.
    """

    _nodes: BagNodeContainer

    if TYPE_CHECKING:
        def __getitem__(self, key: str) -> Any: ...

    def keys(self, iter: bool = False) -> list[str] | Iterator[str]:
        """Return node labels in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iterkeys() from Python 2 - use keys(iter=True) instead.
        """
        return self._nodes.keys(iter=iter)

    def values(self, iter: bool = False) -> list[Any] | Iterator[Any]:
        """Return node values in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces itervalues() from Python 2 - use values(iter=True) instead.
        """
        return self._nodes.values(iter=iter)

    def items(self, iter: bool = False) -> list[tuple[str, Any]] | Iterator[tuple[str, Any]]:
        """Return (label, value) tuples in order.

        Args:
            iter: If True, return a generator instead of a list.

        Note:
            Replaces iteritems() from Python 2 - use items(iter=True) instead.
        """
        return self._nodes.items(iter=iter)

    def get_nodes(self, condition: Callable[[BagNode], bool] | None = None) -> list[BagNode]:
        """Return a new list containing the Bag's current nodes.

        List mutations do not change the Bag structure; the nodes themselves
        are shared. Later insertions/removals are not reflected in this list.

        Args:
            condition: Optional callable that takes a BagNode and returns bool.

        Returns:
            List of BagNodes, optionally filtered by condition.
        """
        if not condition:
            return list(self._nodes)
        return [n for n in self._nodes if condition(n)]

    def get_node_by_attr(
        self, attr: str, value: Any, deep_first: bool = False
    ) -> BagNode | None:
        """Find an attribute match, preferring the current level by default.

        With deep_first=True, visit each node's subtree before its next sibling.
        With False, check all siblings before descending into their subtrees.
        None as value searches for attribute presence, as in has_attr().
        """
        sub_bags = []
        for node in self._nodes:
            if node.has_attr(attr, value):
                return node
            child = node.value
            if safe_is_instance(child, _IS_BAG):
                if deep_first:
                    found = child.get_node_by_attr(attr, value, deep_first=True)
                    if found is not None:
                        return found
                else:
                    sub_bags.append(child)
        for child in sub_bags:
            found = child.get_node_by_attr(attr, value, deep_first=False)
            if found is not None:
                return found
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
            if node_value:
                found = (node_value.get_item(key) if safe_is_instance(node_value, _IS_BAG)
                         else node_value.get(key))
                if found == value:
                    return node
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

    def for_each(self, callback, static=True, deep=False, **kwargs):
        """Visit nodes using a callback, optionally descending into child Bags.

        None continues into children; falsey non-None results skip children;
        a truthy result stops the entire visit and is returned. Path/index
        tracking kwargs include the current node. Exceptions propagate.
        """
        if not callable(callback):
            raise TypeError("for_each requires a callable")

        def visit(bag, context):
            for index, node in enumerate(bag._nodes):
                kw = dict(context)
                if "_pathlist" in context:
                    kw["_pathlist"] = context["_pathlist"] + [node.label]
                if "_indexlist" in context:
                    kw["_indexlist"] = context["_indexlist"] + [index]
                result = callback(node, **kw)
                if result:
                    return result
                if result is None and deep:
                    value = node.get_value(static=static)
                    if safe_is_instance(value, _IS_BAG):
                        result = visit(value, kw)
                        if result:
                            return result
            return None

        return visit(self, kwargs)

    def _iter_nodes_with_paths(self, static=True, prefix=""):
        """Stream path/node pairs for internal query and serialization use."""
        for node in self._nodes:
            path = f"{prefix}.{node.label}" if prefix else node.label
            yield path, node
            value = node.get_value(static=static)
            if safe_is_instance(value, _IS_BAG):
                yield from value._iter_nodes_with_paths(static=static, prefix=path)

    def traverse(self) -> Iterator[BagNode]:
        """Yield original nodes depth-first, parent before children.

        Matches legacy Python traversal: values are read statically, so lazy
        resolvers are not invoked. Shared subtrees are visited at each path.
        """
        for node in self._nodes:
            yield node
            value = node.get_value(static=True)
            if safe_is_instance(value, _IS_BAG):
                yield from value.traverse()

    def get_leaves(self):
        """Return (relative path, value) pairs for non-Bag leaves.

        Resolve each node once per occurrence. Empty Bags are branches and
        produce no leaf entry. Paths do not require parent backrefs.
        """
        result = []

        def collect(bag, prefix):
            for node in bag._nodes:
                path = f"{prefix}.{node.label}" if prefix else node.label
                value = node.get_value(static=False)
                if safe_is_instance(value, _IS_BAG):
                    collect(value, path)
                else:
                    result.append((path, value))

        collect(self, "")
        return result

    def query(
        self,
        what: str | list | None = None,
        condition: Callable[[BagNode], bool] | None = None,
        iter: bool = False,
        deep: bool = False,
        leaf: bool = True,
        branch: bool = True,
        limit: int | None = None,
        static: bool = True,
    ) -> list | Iterator:
        """Query Bag elements, extracting specified data.

        Args:
            what: String of special keys separated by comma, or list of keys.
                Special keys:
                - '#k': label of each item
                - '#v': value of each item
                - '#v.path': inner values of each item
                - '#__v': static value (always bypasses resolver)
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
            static: If True (default), don't trigger resolvers during traversal.
                If False, resolvers may be triggered to compute values.

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
        if not what:
            what = "#k,#v,#a"
        if isinstance(what, str):
            if ":" in what:
                where, what = what.split(":")
                obj = self[where]
            else:
                obj = self
            whatsplit = [x.strip() for x in what.split(",")]
        else:
            whatsplit = what
            obj = self

        def _extract_value(node: BagNode, w: str, path: str,
                           is_deep: bool, read_value: Callable[[], Any]) -> Any:
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
                value = read_value()
                return None if is_deep and safe_is_instance(value, _IS_BAG) else value
            elif w.startswith("#v."):
                inner_path = w.split(".", 1)[1]
                value = read_value()
                return value[inner_path] if hasattr(value, "get_item") else None
            elif w == "#__v":
                return node.static_value
            elif w.startswith("#a"):
                attr = w.split(".", 1)[1] if "." in w else None
                return node.get_attr(attr)
            else:
                value = read_value()
                return value[w] if hasattr(value, "__getitem__") else None

        def _iter_digest() -> Iterator:
            """Stream query results, resolving each visited node at most once."""
            count = 0

            def visit(bag, prefix):
                nonlocal count
                for node in bag._nodes:
                    path = f"{prefix}.{node.label}" if prefix else node.label
                    loaded = False
                    value = None

                    def read_value(node=node):
                        nonlocal loaded, value
                        if not loaded:
                            value = node.get_value(static=static)
                            loaded = True
                        return value

                    included = (leaf and branch) or (
                        branch if safe_is_instance(read_value(), _IS_BAG) else leaf)
                    if included and (condition is None or condition(node)):
                        if len(whatsplit) == 1:
                            yield _extract_value(node, whatsplit[0], path, deep, read_value)
                        else:
                            yield tuple(_extract_value(node, w, path, deep, read_value)
                                        for w in whatsplit)
                        count += 1
                        if limit is not None and count >= limit:
                            return

                    if deep:
                        child = read_value()
                        if safe_is_instance(child, _IS_BAG):
                            yield from visit(child, path)
                            if limit is not None and count >= limit:
                                return

            yield from visit(obj, "")

        if iter:
            return _iter_digest()

        return list(_iter_digest())

    def digest(
        self,
        what: str | list | None = None,
        condition: Callable[[BagNode], bool] | None = None,
        as_columns: bool = False,
        **kwargs: Any,
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
        if "asColumns" in kwargs:
            as_columns = kwargs.pop("asColumns")
        if kwargs:
            unexpected = next(iter(kwargs))
            raise TypeError(f"digest() got an unexpected keyword argument {unexpected!r}")

        result = self.query(what, condition, iter=False, deep=False)
        if as_columns:
            if not result:
                what_str = what if isinstance(what, str) else "#k,#v,#a"
                whatsplit = [x.strip() for x in what_str.split(",")]
                return [[] for _ in whatsplit]
            result_list = list(result)
            if result_list and isinstance(result_list[0], tuple):
                return [list(col) for col in zip(*result_list, strict=False)]
            return [result_list]
        return list(result)

    def columns(self, cols: str | list, attr_mode: bool = False, **kwargs: Any) -> list:
        """Return digest result as columns.

        Args:
            cols: Column names as comma-separated string or list.
            attr_mode: If True, prefix columns with '#a.' for attribute access.

        Returns:
            List of lists (columns).
        """
        if "attrMode" in kwargs:
            attr_mode = kwargs.pop("attrMode")
        if kwargs:
            unexpected = next(iter(kwargs))
            raise TypeError(f"columns() got an unexpected keyword argument {unexpected!r}")

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
                return (-1, "")  # None first ascending, last descending
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
                        key=lambda n, attr=attrname: sort_key(n.get_attr(attr), case_insensitive),  # type: ignore[misc]
                        reverse=reverse,
                    )
                else:
                    # Sort by field in value
                    self._nodes._list.sort(
                        key=lambda n, field=what: sort_key(  # type: ignore[misc]
                            n.value[field] if n.value else None, case_insensitive
                        ),
                        reverse=reverse,
                    )
        return self

    def sum(
        self,
        what: str = "#v",
        strict: bool = False,
        condition: Callable[[BagNode], bool] | None = None,
    ) -> float | None | list[float | None]:
        """Sum selected values at the current level, without recursive traversal.

        Args:
            what: Query criterion, or comma-separated criteria for multiple sums.
            strict: Return None for a criterion containing None or an empty string.
                Otherwise those values contribute zero. Non-numeric values are ignored
                unless strict, which raises TypeError. Zero and False are valid.
            condition: Optional callable filter receiving a BagNode.

        Returns:
            A sum (or None in strict mode), or a list for multiple criteria.

        Examples:
            >>> bag.sum('#v', True)
            >>> bag.sum('#a.price', condition=lambda n: n.get_attr('active'))
        """
        if strict is not None and not isinstance(strict, bool):
            raise TypeError("sum strict must be a boolean; pass condition as the third argument")
        if condition is not None and not callable(condition):
            raise TypeError("sum condition must be callable; deep is no longer supported")

        def total(criterion: str) -> Any:
            result = 0
            missing = False
            for value in self.query(criterion, condition):
                if value is None or (isinstance(value, str) and value == ""):
                    missing = True
                    continue
                if not isinstance(value, Number):
                    if strict:
                        raise TypeError(f"sum encountered non-numeric value: {type(value).__name__}")
                    continue
                result += value
            return None if strict and missing else result

        if "," in what:
            return [total(criterion.strip()) for criterion in what.split(",")]
        return total(what)
