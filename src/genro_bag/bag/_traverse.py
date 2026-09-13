# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagTraverse mixin - hierarchical path traversal engine for Bag.

Provides the core _htraverse mechanism that resolves dot-separated paths
like 'a.b.c' into (container, label) tuples using synchronous resolver loads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag.bag._exceptions import BagException

if TYPE_CHECKING:
    from genro_bag.bag._core import Bag
    from genro_bag.bagnode import BagNode


class BagTraverse:
    """Mixin providing hierarchical path traversal for Bag.

    Resolves dot-separated paths (e.g. 'a.b.c') into (container, label) tuples,
    triggering synchronous resolver loads when requested.
    """

    _nodes: Any
    parent: Any

    def _htraverse_before(self, path: str | list) -> tuple[Bag | None, list[str]]:
        """Parse path and handle #parent navigation.

        First phase of path traversal: converts path to list, handles '../' alias,
        and processes any leading #parent segments.

        Args:
            path: Dot-separated path like 'a.b.c' or list ['a', 'b', 'c'].

        Returns:
            Tuple of (curr, pathlist) where:
                - curr: Starting Bag (may have moved up via #parent), or None
                - pathlist: Remaining path segments to process
        """
        curr: Bag | None = self  # type: ignore[assignment]

        if isinstance(path, str):
            path = path.replace("../", "#parent.")
            if "\\." in path:
                path = path.replace("\\.", chr(1))
                pathlist = [x.strip().replace(chr(1), "\\.") for x in path.split(".") if x.strip()]
            else:
                pathlist = [x.strip() for x in path.split(".") if x.strip()]
        else:
            pathlist = list(path)

        # handle parent reference #parent at the beginning
        while pathlist and pathlist[0] == "#parent" and curr is not None:
            pathlist.pop(0)
            curr = curr.parent

        return curr, pathlist

    def _htraverse(
        self, path: str | list, write_mode: bool = False, static: bool = True
    ) -> tuple[Any, str]:
        """Traverse a hierarchical path synchronously.

        Args:
            path: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            write_mode: If True, create intermediate Bags for missing segments.
                        Forces static=True (no resolver triggers during write).
            static: If True, don't trigger resolvers during traversal.

        Returns:
            Tuple of (container, label).
        """
        if write_mode:
            static = True

        # Fast path: single segment — no traversal needed
        if isinstance(path, str) and "." not in path:
            return self, path

        curr, pathlist = self._htraverse_before(path)
        if curr is None:
            return None, ""
        if not pathlist:
            return curr, ""

        def finalize(result: tuple[Bag, list[str]]) -> tuple[Any, str | None]:
            """Finalize traversal: handle empty path or create intermediate nodes."""
            curr, pathlist = result
            if not write_mode:
                if len(pathlist) > 1:
                    return None, ""
                return curr, pathlist[0]
            # Write mode: create intermediate nodes
            while len(pathlist) > 1:
                label = pathlist.pop(0)
                if label.startswith("#"):
                    raise BagException("Not existing index in #n syntax")
                new_bag = curr.__class__()
                curr._nodes.set(label, new_bag, parent_bag=curr, _reason="autocreate")
                curr = new_bag
            return curr, pathlist[0]

        result = self._traverse_inner(curr, pathlist, write_mode, static)
        return finalize(result)  # type: ignore[return-value]

    def _get_new_curr(self, node: BagNode, value: Any, write_mode: bool) -> Bag | None:
        """Get next curr for traversal, creating Bag if needed in write_mode."""
        if hasattr(value, "_htraverse"):
            return value  # type: ignore[no-any-return, return-value]
        if write_mode:
            new_bag = self.__class__()
            node.set_value(new_bag, _reason="autocreate")
            return new_bag  # type: ignore[return-value]
        return None

    def _traverse_inner(
        self, curr: Bag, pathlist: list, write_mode: bool, static: bool
    ) -> tuple[Bag, list[Any]] | Any:
        """Traverse path segments synchronously.

        Args:
            curr: Starting Bag position.
            pathlist: Path segments to traverse.
            write_mode: If True, replace non-Bag values with Bags during traversal.
            static: If True, don't trigger resolvers.

        Returns:
            Tuple of (container, remaining_path).
        """
        while len(pathlist) > 1 and hasattr(curr, "_nodes"):
            segment = pathlist[0]  # read without removing

            # Inner #parent: walk up to parent Bag, same behaviour as
            # _htraverse_before applies for leading segments. Without this
            # branch the lookup below would fail (no node named "#parent")
            # and the traversal would break, regressing vs the legacy
            # gnr/core/gnrbag.py recursive _htraverse.
            if segment == "#parent":
                if curr.parent is None:
                    break
                pathlist.pop(0)
                curr = curr.parent
                continue

            node = curr._nodes.get(segment)
            if not node:
                break

            value = node.get_value(static=static)

            new_curr = self._get_new_curr(node, value, write_mode)
            if new_curr is None:
                break
            pathlist.pop(0)
            curr = new_curr

        return (curr, pathlist)
