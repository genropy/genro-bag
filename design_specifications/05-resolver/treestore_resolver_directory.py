# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Directory resolver for lazy filesystem traversal.

This module provides resolvers for lazy loading of filesystem hierarchies,
compatible with Genropy's DirectoryResolver from gnrbag.py.

The DirectoryResolver enables lazy traversal of directory structures:
- Directories become branch nodes with their own DirectoryResolver
- Files become leaf nodes with optional content resolvers
- File metadata (mtime, size, etc.) stored in node attributes

Example:
    Basic usage::

        from genro_treestore import TreeStore
        from genro_treestore.resolvers import DirectoryResolver

        store = TreeStore()
        store.set_item('docs')
        store.set_resolver('docs', DirectoryResolver('/path/to/docs'))

        # Lazy traversal - directories resolved on access
        store['docs.subdir.readme_txt']

        # Access file metadata
        node = store.get_node('docs.subdir.readme_txt')
        print(node.attr['abs_path'])  # /path/to/docs/subdir/readme.txt
        print(node.attr['mtime'])     # datetime of last modification

    With filtering::

        # Only include Python files, exclude __pycache__
        resolver = DirectoryResolver(
            '/path/to/project',
            include='*.py',
            exclude='__pycache__'
        )

    Custom file processors::

        def process_json(path):
            with open(path) as f:
                return json.load(f)

        resolver = DirectoryResolver(
            '/path/to/data',
            ext='json',
            processors={'json': process_json}
        )
"""

from __future__ import annotations

import fnmatch
import os
import re
from datetime import datetime
from typing import Any, Callable

from genro_toolbox import smartasync

from .base import TreeStoreResolver
from ..store import TreeStore


class DirectoryResolver(TreeStoreResolver):
    """Resolver for lazy loading of filesystem directory contents.

    Loads directory contents on demand, creating a TreeStore where:
    - Subdirectories become branch nodes with their own DirectoryResolver
    - Files become leaf nodes (value=None by default, or processed content)
    - File metadata stored in node attributes

    Compatible with Genropy's DirectoryResolver API.

    Attributes:
        path: Absolute path to the directory.
        relocate: Relative path prefix for rel_path attribute.
        invisible: If True, include hidden files (starting with '.').
        ext: Comma-separated list of extensions to process (e.g., 'xml,json').
            Format: 'ext' or 'ext:processor_name'.
        include: Glob pattern for files to include (e.g., '*.py').
        exclude: Glob pattern for files/dirs to exclude (e.g., '__pycache__').
        callback: Optional callback(nodeattr) -> bool to filter nodes.
        dropext: If True, don't include extension in node labels.
        processors: Dict mapping extension to processor function.

    Example:
        Basic directory listing::

            resolver = DirectoryResolver('/home/user/docs')
            store.set_item('docs')
            store.set_resolver('docs', resolver)

            # Access triggers lazy load
            for label in store['docs'].keys():
                node = store.get_node(f'docs.{label}')
                print(f"{label}: {node.attr['file_ext']}")

        With XML processing::

            resolver = DirectoryResolver(
                '/path/to/config',
                ext='xml',
                processors={'xml': lambda p: parse_xml(p)}
            )
    """

    __slots__ = (
        "path",
        "relocate",
        "invisible",
        "ext",
        "include",
        "exclude",
        "callback",
        "dropext",
        "processors",
    )

    def __init__(
        self,
        path: str,
        relocate: str = "",
        *,
        cache_time: int = 500,
        read_only: bool = True,
        invisible: bool = False,
        ext: str = "",
        include: str = "",
        exclude: str = "",
        callback: Callable[[dict], bool | None] | None = None,
        dropext: bool = False,
        processors: dict[str, Callable[[str], Any] | bool] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the directory resolver.

        Args:
            path: Absolute path to the directory to resolve.
            relocate: Relative path prefix for rel_path attribute.
                Used to maintain relative paths when nested.
            cache_time: Cache duration in seconds. Default 500 (like Bag).
            read_only: If True, resolved value not stored in node._value.
            invisible: If True, include hidden files (starting with '.').
            ext: Comma-separated extensions to process. Format:
                'xml' or 'xml:processor_name,json:processor_name'.
            include: Glob pattern for files to include (e.g., '*.py,*.txt').
            exclude: Glob pattern for files/dirs to exclude.
            callback: Function called with nodeattr dict for each entry.
                Return False to skip the entry, None/True to include.
            dropext: If True, don't include extension in node labels.
            processors: Dict mapping extension/processor_name to:
                - Callable[[str], Any]: Function to process file, returns value
                - False: Skip files with this extension
                - None: Use default processor (returns None)
            **kwargs: Additional arguments for TreeStoreResolver.
        """
        super().__init__(cache_time=cache_time, read_only=read_only, **kwargs)

        self.path = path
        self.relocate = relocate
        self.invisible = invisible
        self.ext = ext
        self.include = include
        self.exclude = exclude
        self.callback = callback
        self.dropext = dropext
        self.processors = processors or {}

        # Store args for serialization
        self._init_args = (path, relocate)
        self._init_kwargs = {
            "invisible": invisible,
            "ext": ext,
            "include": include,
            "exclude": exclude,
            "dropext": dropext,
            # Note: callback and processors not serializable
        }

    @property
    def instance_kwargs(self) -> dict[str, Any]:
        """Get kwargs for creating child DirectoryResolvers."""
        return {
            "cache_time": self.cache_time,
            "read_only": self.read_only,
            "invisible": self.invisible,
            "ext": self.ext,
            "include": self.include,
            "exclude": self.exclude,
            "callback": self.callback,
            "dropext": self.dropext,
            "processors": self.processors,
        }

    @smartasync
    async def load(self) -> TreeStore:
        """Load directory contents into a TreeStore.

        Returns:
            TreeStore containing directory entries as nodes.
            Subdirectories have DirectoryResolver attached.
            Files have metadata in attributes.
        """
        # Parse extensions mapping: 'xml' or 'xml:processor_name'
        extensions: dict[str, str] = {}
        if self.ext:
            for ext_spec in self.ext.split(","):
                parts = ext_spec.strip().split(":")
                ext_name = parts[0]
                processor_name = parts[1] if len(parts) > 1 else parts[0]
                extensions[ext_name] = processor_name
        extensions["directory"] = "directory"

        result = TreeStore()

        # List directory contents
        try:
            directory = sorted(os.listdir(self.path))
        except OSError:
            directory = []

        # Filter hidden files
        if not self.invisible:
            directory = [x for x in directory if not x.startswith(".")]

        for fname in directory:
            # Skip editor backup/journal files
            if fname.startswith("#") or fname.endswith("#") or fname.endswith("~"):
                continue

            nodecaption = fname
            fullpath = os.path.join(self.path, fname)
            relpath = os.path.join(self.relocate, fname)
            add_it = True

            if os.path.isdir(fullpath):
                ext = "directory"
                if self.exclude:
                    add_it = self._filter_match(fname, exclude=self.exclude)
            else:
                if self.include or self.exclude:
                    add_it = self._filter_match(fname, include=self.include, exclude=self.exclude)
                fname_base, ext = os.path.splitext(fname)
                ext = ext[1:]  # Remove leading dot
                fname = fname_base

            if not add_it:
                continue

            # Create label
            label = self._make_label(fname, ext)

            # Get processor
            processor_name = extensions.get(ext.lower())
            handler = self.processors.get(processor_name) if processor_name else None

            if handler is False:
                continue  # Skip this extension

            if handler is None:
                # Try method-based processor
                handler = getattr(self, f"processor_{processor_name}", None)
            if handler is None:
                handler = self.processor_default

            # Get file stats
            try:
                stat = os.stat(fullpath)
                mtime = datetime.fromtimestamp(stat.st_mtime)
                atime = datetime.fromtimestamp(stat.st_atime)
                ctime = datetime.fromtimestamp(stat.st_ctime)
                size = stat.st_size
            except OSError:
                mtime = atime = ctime = size = None

            # Build caption (like Bag)
            caption = fname.replace("_", " ").strip()
            m = re.match(r"(\d+) (.*)", caption)
            if m:
                caption = f"!!{int(m.group(1))} {m.group(2).capitalize()}"
            else:
                caption = caption.capitalize()

            # Build node attributes
            nodeattr = {
                "file_name": fname,
                "file_ext": ext,
                "rel_path": relpath,
                "abs_path": fullpath,
                "mtime": mtime,
                "atime": atime,
                "ctime": ctime,
                "nodecaption": nodecaption,
                "caption": caption,
                "size": size,
            }

            # Apply callback filter
            if self.callback:
                cb_result = self.callback(nodeattr)
                if cb_result is False:
                    continue

            # Process and add item
            value = handler(fullpath)
            result.set_item(label, _attributes=nodeattr)

            # If handler returned a resolver, set it
            if isinstance(value, TreeStoreResolver):
                result.set_resolver(label, value)
            elif value is not None:
                result.get_node(label)._value = value

        return result

    def _make_label(self, name: str, ext: str) -> str:
        """Create node label from filename and extension.

        Args:
            name: Filename without extension.
            ext: File extension (without dot).

        Returns:
            Label safe for use as TreeStore key.
        """
        if ext != "directory" and not self.dropext:
            name = f"{name}_{ext}"
        return name.replace(".", "_")

    def _filter_match(
        self,
        name: str,
        include: str = "",
        exclude: str = "",
    ) -> bool:
        """Check if filename matches include/exclude patterns.

        Args:
            name: Filename to check.
            include: Comma-separated glob patterns to include.
            exclude: Comma-separated glob patterns to exclude.

        Returns:
            True if file should be included, False otherwise.
        """
        # Check exclude first
        if exclude:
            for pattern in exclude.split(","):
                pattern = pattern.strip()
                if fnmatch.fnmatch(name, pattern):
                    return False

        # Check include
        if include:
            for pattern in include.split(","):
                pattern = pattern.strip()
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False  # Didn't match any include pattern

        return True  # No include filter, passed exclude

    def processor_directory(self, path: str) -> DirectoryResolver:
        """Process a subdirectory by creating a new DirectoryResolver.

        Args:
            path: Absolute path to the subdirectory.

        Returns:
            DirectoryResolver for the subdirectory.
        """
        new_relocate = os.path.join(self.relocate, os.path.basename(path))
        return DirectoryResolver(path, new_relocate, **self.instance_kwargs)

    def processor_default(self, path: str) -> None:
        """Default processor for files - returns None.

        Args:
            path: Absolute path to the file.

        Returns:
            None (file path stored in attributes).
        """
        return None

    def __repr__(self) -> str:
        return f"DirectoryResolver({self.path!r}, cache_time={self.cache_time})"


class TxtDocResolver(TreeStoreResolver):
    """Resolver that loads text file contents.

    Compatible with Genropy's TxtDocResolver.

    Attributes:
        path: Absolute path to the text file.

    Example:
        >>> resolver = TxtDocResolver('/path/to/file.txt')
        >>> node.resolver = resolver
        >>> content = node.value  # Reads file contents
    """

    __slots__ = ("path",)

    def __init__(
        self,
        path: str,
        *,
        cache_time: int = 500,
        read_only: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the text document resolver.

        Args:
            path: Absolute path to the text file.
            cache_time: Cache duration in seconds. Default 500.
            read_only: If True, resolved value not stored in node._value.
            **kwargs: Additional arguments for TreeStoreResolver.
        """
        super().__init__(cache_time=cache_time, read_only=read_only, **kwargs)
        self.path = path
        self._init_args = (path,)

    @smartasync
    async def load(self) -> bytes:
        """Load and return the file contents as bytes.

        Returns:
            File contents as bytes.
        """
        with open(self.path, mode="rb") as f:
            return f.read()

    def __repr__(self) -> str:
        return f"TxtDocResolver({self.path!r})"
