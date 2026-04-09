# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagTraverse mixin - hierarchical path traversal engine for Bag.

Provides the core _htraverse mechanism that resolves dot-separated paths
like 'a.b.c' into (container, label) tuples, handling both sync and async
contexts transparently.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from genro_toolbox import smartawait, smartcontinuation, smartsplit

if TYPE_CHECKING:
    from genro_bag.bag._core import Bag
    from genro_bag.bagnode import BagNode


class BagTraverse:
    """Mixin providing hierarchical path traversal for Bag."""

    _nodes: Any
    parent: Any

    @property
    def in_async_context(self) -> bool:
        """Whether we are currently running inside an async context."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

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
        curr: Bag | None = cast("Bag", self)

        if isinstance(path, str):
            path = path.replace("../", "#parent.")
            pathlist = [x for x in smartsplit(path, ".") if x]
        else:
            pathlist = list(path)

        # handle parent reference #parent at the beginning
        while pathlist and pathlist[0] == "#parent" and curr is not None:
            pathlist.pop(0)
            curr = curr.parent

        return curr, pathlist

    def _htraverse(
        self, path: str | list, write_mode: bool = False, static: bool = True
    ) -> tuple[Any, str | None]:
        """Traverse a hierarchical path - unified sync/async version.

        Single method that handles both sync and async contexts:
        - In sync context: returns tuple directly
        - In async context with static=False: may return coroutine

        Args:
            path: Path as dot-separated string 'a.b.c' or list ['a', 'b', 'c'].
            write_mode: If True, create intermediate Bags for missing segments.
                        Forces static=True (no resolver triggers during write).
            static: If True, don't trigger resolvers during traversal.

        Returns:
            Tuple of (container, label) OR coroutine that resolves to tuple.
        """
        from genro_bag.bag._core import BagException

        if write_mode:
            static = True
        curr, pathlist = self._htraverse_before(path)
        if curr is None:
            return None, None
        if not pathlist:
            return curr, ""

        def finalize(result: tuple[Bag, list[str]]) -> tuple[Any, str | None]:
            """Finalize traversal: handle empty path or create intermediate nodes."""
            curr, pathlist = result
            if not write_mode:
                if len(pathlist) > 1:
                    return None, None
                return curr, pathlist[0]
            # Write mode: create intermediate nodes
            while len(pathlist) > 1:
                label = pathlist.pop(0)
                if label.startswith("#"):
                    raise BagException("Not existing index in #n syntax")
                new_bag = curr.__class__()
                curr._nodes.set(label, new_bag, parent_bag=curr)
                curr = new_bag
            return curr, pathlist[0]

        result = self._traverse_inner(curr, pathlist, write_mode, static)
        return cast(tuple[Any, str | None], smartcontinuation(result, finalize))

    def _is_coroutine(self, value: Any, _in_async: bool | None = None) -> bool:
        """Check if value is a coroutine (only possible in async context).

        Args:
            value: The value to check.
            _in_async: Pre-computed async context flag. If None, checks dynamically.
        """
        if _in_async is None:
            _in_async = self.in_async_context
        return _in_async and asyncio.iscoroutine(value)

    def _get_new_curr(self, node: BagNode, value: Any, write_mode: bool) -> Bag | None:
        """Get next curr for traversal, creating Bag if needed in write_mode."""
        if hasattr(value, "_htraverse"):
            return cast("Bag", value)
        if write_mode:
            new_bag = cast("Bag", self.__class__())
            node.set_value(new_bag)
            return new_bag
        return None

    def _traverse_inner(
        self, curr: Bag, pathlist: list, write_mode: bool, static: bool
    ) -> tuple[Bag, list[Any]] | Any:
        """Traverse path segments - unified sync/async version.

        Args:
            curr: Starting Bag position.
            pathlist: Path segments to traverse.
            write_mode: If True, replace non-Bag values with Bags during traversal.
            static: If True, don't trigger resolvers.

        Returns:
            Tuple of (container, remaining_path) OR coroutine.
        """
        in_async = self.in_async_context
        while len(pathlist) > 1 and hasattr(curr, "_nodes"):
            segment = pathlist[0]  # read without removing
            node = curr._nodes.get(segment)
            if not node:
                break

            value = node.get_value(static=static)

            if not self._is_coroutine(value, _in_async=in_async):
                new_curr = self._get_new_curr(node, value, write_mode)
                if new_curr is None:
                    break
                pathlist.pop(0)  # traversal succeeded, now remove
                curr = new_curr
                continue

            # coroutine case
            pathlist.pop(0)  # remove before creating continuation
            remaining = pathlist[:]

            async def cont(
                value=value,
                node=node,
                curr=curr,
                segment=segment,
                remaining=remaining,
            ):
                resolved = await value
                new_curr = self._get_new_curr(node, resolved, write_mode)
                if new_curr is None:
                    return (curr, [segment] + remaining)
                return await smartawait(
                    self._traverse_inner(new_curr, remaining, write_mode, static)
                )

            return cont()

        return (curr, pathlist)
