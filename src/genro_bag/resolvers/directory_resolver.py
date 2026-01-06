# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Directory and file resolvers - lazily load filesystem content as Bag."""

from __future__ import annotations

import fnmatch
import os
import re
from datetime import datetime

from ..resolver import BagResolver


class TxtDocResolver(BagResolver):
    """Resolver that lazily loads file content as raw bytes.

    Despite the name "TxtDoc", this resolver reads files in binary mode
    and returns bytes, not decoded text. This preserves the original
    encoding and allows handling of any file type.

    Parameters (class_args):
        path: Filesystem path to the file.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 500.
        read_only: If True, resolver acts as pure getter. Default True.

    Returns:
        bytes: Raw file content. Caller must decode if text is needed.

    Example:
        >>> resolver = TxtDocResolver('/path/to/file.txt')
        >>> content = resolver()  # returns bytes
        >>> text = content.decode('utf-8')  # decode to string
    """

    class_kwargs = {"cache_time": 500, "read_only": True}
    class_args = ["path"]

    def load(self):
        """Load and return the file content as raw bytes.

        Returns:
            bytes: The complete file content in binary form.
        """
        with open(self._kw["path"], mode="rb") as f:
            return f.read()


class SerializedBagResolver(BagResolver):
    """Resolver that lazily loads a Bag from a serialized file.

    Supports all formats recognized by Bag.fill_from():
    - .xml: XML format (with auto-detect for legacy GenRoBag)
    - .bag.json: TYTX JSON format
    - .bag.mp: TYTX MessagePack format

    Parameters (class_args):
        path: Filesystem path to the serialized Bag file.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 500.
        read_only: If True, resolver acts as pure getter. Default True.

    Example:
        >>> resolver = SerializedBagResolver('/path/to/data.bag.json')
        >>> bag = resolver()
        >>> bag['config.host']
        'localhost'
    """

    class_kwargs = {"cache_time": 500, "read_only": True}
    class_args = ["path"]

    def load(self):
        """Load and return the Bag from the serialized file."""
        from ..bag import Bag

        return Bag(self._kw["path"])


class DirectoryResolver(BagResolver):
    """Resolver that lazily loads a filesystem directory as a Bag.

    When resolved, scans a directory and creates a Bag where each entry
    (file or subdirectory) becomes a node. Subdirectories are represented
    as nested DirectoryResolvers, enabling lazy recursive traversal.

    Parameters (class_args):
        path: Filesystem path to the directory to scan.
        relocate: Base path for relative path calculation in node attributes.
            Used to track original location when directory is accessed
            from a different context.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 500.
        read_only: If True, resolver acts as pure getter. Default True.
        invisible: If True, includes hidden files (starting with '.'). Default False.
        ext: Comma-separated list of extensions to process, with optional
            processor mapping. Format: 'ext1,ext2:processor,ext3'.
            Default 'xml'. Use empty string for all extensions.
        include: Comma-separated glob patterns for files to include.
            Empty string means include all (subject to exclude).
        exclude: Comma-separated glob patterns for files to exclude.
        callback: Optional function called for each entry with nodeattr dict.
            Return False to skip the entry.
        dropext: If True, omit extension from node labels. Default False.
        processors: Dict mapping extension names to handler functions.
            Use False as value to disable processing for an extension.

    Node Attributes:
        Each node in the resulting Bag has these attributes:
        - file_name: Filename without extension
        - file_ext: File extension (or 'directory')
        - rel_path: Path relative to relocate
        - abs_path: Absolute filesystem path
        - mtime: Modification time (datetime)
        - atime: Access time (datetime)
        - ctime: Creation time (datetime)
        - size: File size in bytes
        - nodecaption: Original filename
        - caption: Human-readable caption (underscores replaced with spaces)

    Extension Mapping:
        The 'ext' parameter supports mapping extensions to processors:
        - 'txt' -> uses processor_txt
        - 'txt:custom' -> maps 'txt' extension to 'custom' processor
        - 'directory' is always mapped to processor_directory

    Example:
        >>> resolver = DirectoryResolver('/path/to/docs', ext='txt,md')
        >>> bag = resolver()  # or resolver.load()
        >>> for node in bag:
        ...     print(node.label, node.attr['abs_path'])

        >>> # With callback filter
        >>> def only_large(nodeattr):
        ...     return nodeattr['size'] > 1000
        >>> resolver = DirectoryResolver('/data', callback=only_large)

        >>> # With custom processor
        >>> def my_processor(path):
        ...     return open(path).read().upper()
        >>> resolver = DirectoryResolver('/data', processors={'txt': my_processor})
    """

    class_kwargs = {
        "cache_time": 500,
        "read_only": True,
        "invisible": False,
        "relocate": "",
        # FIXME: intercept #file# - emacs' jnl
        "ext": "xml",
        "include": "",
        "exclude": "",
        "callback": None,
        "dropext": False,
        "processors": None,
    }
    class_args = ["path", "relocate"]

    def load(self):
        """Load directory contents and return as a Bag.

        Scans the directory specified in 'path', filters entries based on
        include/exclude patterns and visibility settings, then creates a
        Bag with one node per entry.

        For each entry:
        1. Determines if it's a file or directory
        2. Applies include/exclude filters
        3. Looks up the appropriate processor based on extension
        4. Collects file metadata (size, timestamps)
        5. Calls optional callback for further filtering
        6. Creates node with value from processor and metadata as attributes

        Returns:
            Bag: A Bag containing one node per directory entry.
                Files have processor output as value (or None).
                Directories have nested DirectoryResolver as value.
        """
        from ..bag import Bag

        extensions = (
            dict([(ext.split(":") + ext.split(":"))[0:2] for ext in self._kw["ext"].split(",")])
            if self._kw["ext"]
            else {}
        )
        extensions["directory"] = "directory"
        result = Bag()
        try:
            directory = sorted(os.listdir(self._kw["path"]))
        except OSError:
            directory = []
        if not self._kw["invisible"]:
            directory = [x for x in directory if not x.startswith(".")]
        for fname in directory:
            # skip journal files
            if fname.startswith("#") or fname.endswith("#") or fname.endswith("~"):
                continue
            nodecaption = fname
            fullpath = os.path.join(self._kw["path"], fname)
            relpath = os.path.join(self._kw["relocate"], fname)
            add_it = True
            if os.path.isdir(fullpath):
                ext = "directory"
                if self._kw["exclude"]:
                    add_it = self._filter(fname, exclude=self._kw["exclude"], wildcard="*")
            else:
                if self._kw["include"] or self._kw["exclude"]:
                    add_it = self._filter(
                        fname,
                        include=self._kw["include"],
                        exclude=self._kw["exclude"],
                        wildcard="*",
                    )
                fname, ext = os.path.splitext(fname)
                ext = ext[1:]
            if add_it:
                label = self.make_label(fname, ext)
                processors = self._kw["processors"] or {}
                processname = extensions.get(ext.lower(), None)
                handler = processors.get(processname)
                if handler is not False:
                    handler = handler or getattr(
                        self, f"processor_{extensions.get(ext.lower(), 'None')}", None
                    )
                handler = handler or self.processor_default
                try:
                    stat = os.stat(fullpath)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    atime = datetime.fromtimestamp(stat.st_atime)
                    ctime = datetime.fromtimestamp(stat.st_ctime)
                    size = stat.st_size
                except OSError:
                    mtime = None
                    ctime = None
                    atime = None
                    size = None
                caption = fname.replace("_", " ").strip()
                m = re.match(r"(\d+) (.*)", caption)
                caption = (
                    f"!!{int(m.group(1))} {m.group(2).capitalize()}" if m else caption.capitalize()
                )
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
                if self._kw["callback"]:
                    cbres = self._kw["callback"](nodeattr=nodeattr)
                    if cbres is False:
                        continue
                handler_result = handler(fullpath)
                # If handler returns a resolver, set it as resolver not as value
                if isinstance(handler_result, BagResolver):
                    result.set_item(label, None, resolver=handler_result, **nodeattr)
                else:
                    result.set_item(label, handler_result, **nodeattr)
        return result

    def _filter(self, name, include="", exclude="", wildcard="*"):
        """Filter filename by include/exclude glob patterns.

        Args:
            name: Filename to check.
            include: Comma-separated glob patterns. If set, file must match
                at least one pattern to be included.
            exclude: Comma-separated glob patterns. If file matches any
                pattern, it is excluded.
            wildcard: Wildcard character for patterns. Default '*'.

        Returns:
            bool: True if file passes filter, False otherwise.
        """
        if include:
            patterns = include.split(",")
            if not any(fnmatch.fnmatch(name, p.strip()) for p in patterns):
                return False
        if exclude:
            patterns = exclude.split(",")
            if any(fnmatch.fnmatch(name, p.strip()) for p in patterns):
                return False
        return True

    def make_label(self, name, ext):
        """Create a Bag node label from filename and extension.

        The label is used as the key in the Bag. By default, includes the
        extension to avoid collisions (e.g., 'readme_txt', 'readme_md').
        Dots in names are replaced with underscores for path compatibility.

        Args:
            name: Filename without extension.
            ext: File extension (without dot) or 'directory'.

        Returns:
            str: Label suitable for use as Bag node key.
        """
        if ext != "directory" and not self._kw["dropext"]:
            name = f"{name}_{ext}"
        return name.replace(".", "_")

    def processor_directory(self, path):
        """Process a subdirectory entry.

        Creates a new DirectoryResolver for the subdirectory, enabling
        lazy recursive traversal of the filesystem tree.

        Args:
            path: Absolute path to the subdirectory.

        Returns:
            DirectoryResolver: Resolver for the subdirectory with inherited kwargs.
        """
        return DirectoryResolver(
            path,
            os.path.join(self._kw["relocate"], os.path.basename(path)),
            **self._instance_kwargs(),
        )

    def processor_txt(self, path):
        """Process a text file entry.

        Creates a TxtDocResolver for the file, enabling lazy loading
        of text content.

        Args:
            path: Absolute path to the text file.

        Returns:
            TxtDocResolver: Resolver that will load the file content as bytes.
        """
        kwargs = self._instance_kwargs()
        kwargs["path"] = path
        return TxtDocResolver(**kwargs)

    def processor_xml(self, path):
        """Process an XML file entry.

        Creates a SerializedBagResolver for the file, enabling lazy loading
        of the XML content as a Bag.

        Args:
            path: Absolute path to the XML file.

        Returns:
            SerializedBagResolver: Resolver that will parse the XML into a Bag.
        """
        kwargs = self._instance_kwargs()
        kwargs["path"] = path
        return SerializedBagResolver(**kwargs)

    # Alias for XSD and HTML - same as XML
    processor_xsd = processor_xml
    processor_html = processor_xml

    def processor_default(self, path):
        """Default processor for unrecognized file types.

        Called when no specific processor is found for a file extension.
        Returns None, meaning the node will have no value (only attributes).

        Args:
            path: Absolute path to the file.

        Returns:
            None: No value is stored for this file type.
        """
        return None

    def _instance_kwargs(self):
        """Return kwargs for creating child resolvers.

        Creates a copy of current resolver's kwargs to pass to child
        resolvers (subdirectories, file resolvers). This ensures children
        inherit settings like cache_time, include/exclude patterns, etc.

        Returns:
            dict: Copy of self._kw suitable for child resolver initialization.
        """
        return dict(self._kw)
