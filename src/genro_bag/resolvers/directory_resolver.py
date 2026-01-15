# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Directory and file resolvers - mount filesystem as navigable Bag nodes.

This module provides resolvers to compose hybrid Bags that mix in-memory data,
filesystem content, and other resolvers. The key concept is "mounting": you can
attach a DirectoryResolver to any path in a Bag, and that path becomes a lazy
gateway to a filesystem directory.

Core Concept - Hybrid Bags::

    bag = Bag()
    bag['config'] = {'host': 'localhost'}           # in-memory data
    bag['templates'] = DirectoryResolver('/app/templates', ext='html')
    bag['schemas'] = DirectoryResolver('/app/schemas', ext='xml')

When you access bag['templates']:
- You get the keys (files and subdirectories) without loading content
- Accessing a subdirectory creates a new lazy Bag for that level
- Accessing a file triggers its processor (based on extension)

Lazy Loading:
    Nothing is loaded until accessed. A DirectoryResolver for a directory with
    1000 files only reads the directory listing. Each file's content is loaded
    only when that specific node is accessed.

Processors - Interpreting File Content:
    The ``ext`` parameter maps file extensions to processors. Processors determine
    what value a file node has when accessed:

    - ``processor_txt``: Returns raw bytes (TxtDocResolver)
    - ``processor_xml``: Parses XML/bag.json/bag.mp as navigable Bag (SerializedBagResolver)
    - ``processor_directory``: Creates nested DirectoryResolver (recursive lazy mount)
    - ``processor_default``: Returns None (node has only attributes, no value)

    Custom processors can transform file content in any way::

        def csv_processor(path):
            with open(path) as f:
                return [line.split(',') for line in f]

        bag['data'] = DirectoryResolver('/data', ext='csv', processors={'csv': csv_processor})

Extension Mapping:
    The ``ext`` parameter supports mapping extensions to processor names::

        ext='txt'           # .txt files use processor_txt
        ext='txt,md'        # both use their default processors
        ext='dat:txt'       # .dat files use processor_txt
        ext='cfg:xml'       # .cfg files parsed as XML Bag

Resolvers in this module:
    - DirectoryResolver: Mounts a directory as lazy Bag
    - TxtDocResolver: Loads file content as raw bytes
    - SerializedBagResolver: Loads XML/bag.json/bag.mp as Bag
"""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime

from ..bag import Bag
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
        read_only: If True, value is not stored in node._value. Default True,
            but effectively False because cache_time=500 forces read_only=False.
            Set cache_time=0 if you need true read_only behavior.

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
        read_only: If True, value is not stored in node._value. Default True,
            but effectively False because cache_time=500 forces read_only=False.
            Set cache_time=0 if you need true read_only behavior.
        format: Force format ('xml', 'json', 'msgpack'). If None, detect from extension.

    Example:
        >>> resolver = SerializedBagResolver('/path/to/data.bag.json')
        >>> bag = resolver()
        >>> bag['config.host']
        'localhost'
        >>>
        >>> # Force XML format for non-.xml extension
        >>> resolver = SerializedBagResolver('/path/to/schema.xsd', format='xml')
    """

    class_kwargs = {"cache_time": 500, "read_only": True, "format": None}
    class_args = ["path"]

    def load(self):
        """Load and return the Bag from the serialized file."""
        return Bag().fill_from(self._kw["path"], format=self._kw["format"])


class DirectoryResolver(BagResolver):
    """Resolver that lazily loads a filesystem directory as a Bag.

    When resolved, scans a directory and creates a Bag where each entry
    (file or subdirectory) becomes a node. Subdirectories are represented
    as nested DirectoryResolvers, enabling lazy recursive traversal.

    Parameters (class_args):
        path: Filesystem path to the directory to scan.
        relocate: Prefix for building rel_path attribute in nodes. When you
            traverse into subdirectories, this prefix is propagated and extended.
            Default is empty string.

            Example: DirectoryResolver('/app/data', relocate='mydata')
            - For file /app/data/config.xml:
              - abs_path = '/app/data/config.xml' (real filesystem path)
              - rel_path = 'mydata/config.xml' (logical path from relocate)
            - For subdir /app/data/sub/:
              - Child resolver gets relocate='mydata/sub'
              - Files inside get rel_path='mydata/sub/filename'

            This lets you present a "virtual" path independent of where the
            directory is actually mounted on the filesystem.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 500.
        read_only: If True, value is not stored in node._value. Default True,
            but effectively False because cache_time=500 forces read_only=False.
            Set cache_time=0 if you need true read_only behavior.
        invisible: If True, includes hidden files (starting with '.'). Default False.
        ext: Comma-separated list of extensions to process, with optional
            processor mapping. Format: 'ext1,ext2:processor,ext3'.
            Default 'xml'. Use empty string for all extensions.
        include: Comma-separated glob patterns for files to include.
            Empty string means include all (subject to exclude).
        exclude: Comma-separated glob patterns for files to exclude.
        callback: Optional function called for each entry with nodeattr dict.
            Return False to skip the entry.
        caption: Controls caption attribute generation. Default None.
            - None: No caption attribute added
            - True: Auto-generate caption (underscores to spaces, capitalize)
            - callable: Called with filename, returns caption string
        dropext: If True, omit extension from node labels. Default False.
        processors: Dict mapping extension names to handler functions.
            Use False as value to disable processing for an extension.
        follow_symlinks: If False (default), symlinks pointing outside the
            base directory are skipped for security. Set to True only if
            you trust the directory content and need to follow symlinks.

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
        - caption: Human-readable caption (only if caption parameter is set)

    Processors:
        Processors determine how file content is loaded when a node is accessed.
        Each processor is a method or callable that receives a file path and returns
        a value (or a resolver for lazy loading).

        Built-in processors:
        - processor_directory: Returns a nested DirectoryResolver (lazy recursion)
        - processor_txt: Returns a TxtDocResolver (lazy bytes loading)
        - processor_xml: Returns a SerializedBagResolver (lazy Bag parsing)
        - processor_default: Sniffs content - if XML returns SerializedBagResolver,
          otherwise None. This auto-detects XML files regardless of extension
          (xsd, rng, xslt, svg, etc.)

        Custom processors can be provided via the 'processors' parameter::

            def csv_processor(path):
                with open(path) as f:
                    return [line.split(',') for line in f]

            resolver = DirectoryResolver('/data', ext='csv', processors={'csv': csv_processor})

        Processors can also convert formats. Example with RNC to XML (requires rnc2rng)::

            def rnc_processor(path):
                import rnc2rng
                rng_xml = rnc2rng.dumps(rnc2rng.load(path))
                return Bag().fill_from(rng_xml, format='xml')

            resolver = DirectoryResolver('/schemas', ext='rnc', processors={'rnc': rnc_processor})

        To disable a built-in processor, set it to False::

            resolver = DirectoryResolver('/data', ext='txt', processors={'txt': False})

    Extension Mapping:
        The 'ext' parameter controls which extensions are processed and how:
        - 'txt' -> uses processor_txt (method name = processor_{ext})
        - 'txt:xml' -> maps .txt files to processor_xml
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
        "ext": "xml",
        "include": "",
        "exclude": "",
        "callback": None,
        "caption": None,
        "dropext": False,
        "processors": None,
        "follow_symlinks": False,
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
        base_realpath = os.path.realpath(self._kw["path"])
        for fname in directory:
            # skip journal files and files starting with # (reserved for index syntax)
            if fname.startswith("#") or fname.endswith("#") or fname.endswith("~"):
                continue
            fullpath = os.path.join(self._kw["path"], fname)

            # Security check: prevent symlink escape attacks
            # Verify that resolved path is still within the base directory
            if not self._kw["follow_symlinks"]:
                real_fullpath = os.path.realpath(fullpath)
                if (
                    not real_fullpath.startswith(base_realpath + os.sep)
                    and real_fullpath != base_realpath
                ):
                    # Path escapes base directory via symlink - skip it
                    continue

            relpath = os.path.join(self._kw["relocate"], fname)
            add_it = True
            if os.path.isdir(fullpath):
                ext = "directory"
                if self._kw["exclude"]:
                    add_it = self._filter(fname, exclude=self._kw["exclude"])
            else:
                if self._kw["include"] or self._kw["exclude"]:
                    add_it = self._filter(
                        fname,
                        include=self._kw["include"],
                        exclude=self._kw["exclude"],
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
                nodeattr = {
                    "file_name": fname,
                    "file_ext": ext,
                    "rel_path": relpath,
                    "abs_path": fullpath,
                    "mtime": mtime,
                    "atime": atime,
                    "ctime": ctime,
                    "size": size,
                }
                caption_opt = self._kw["caption"]
                if caption_opt is True:
                    nodeattr["caption"] = fname.replace("_", " ").strip().capitalize()
                elif callable(caption_opt):
                    nodeattr["caption"] = caption_opt(fname)
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

    def _filter(self, name, include="", exclude=""):
        """Filter filename by include/exclude glob patterns.

        Uses fnmatch for glob-style pattern matching with '*' and '?' wildcards.

        Args:
            name: Filename to check.
            include: Comma-separated glob patterns. If set, file must match
                at least one pattern to be included.
            exclude: Comma-separated glob patterns. If file matches any
                pattern, it is excluded.

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

    def processor_default(self, path):
        """Default processor for unrecognized file types.

        Called when no specific processor is found for a file extension.
        Sniffs file content: if it looks like XML, uses processor_xml.
        Otherwise returns None (node has only attributes, no value).

        Args:
            path: Absolute path to the file.

        Returns:
            SerializedBagResolver if file is XML, None otherwise.
        """
        if self._is_xml_file(path):
            # Force XML format since extension is not .xml
            kwargs = self._instance_kwargs()
            kwargs["path"] = path
            kwargs["format"] = "xml"
            return SerializedBagResolver(**kwargs)
        return None

    def _is_xml_file(self, path):
        """Check if file looks like XML by sniffing first bytes.

        Args:
            path: Absolute path to the file.

        Returns:
            bool: True if file appears to be XML.
        """
        try:
            with open(path, "rb") as f:
                start = f.read(100).lstrip()
            return start.startswith(b"<?xml") or start.startswith(b"<")
        except OSError:
            return False

    def _instance_kwargs(self):
        """Return kwargs for creating child resolvers.

        Creates a copy of current resolver's kwargs to pass to child
        resolvers (subdirectories, file resolvers). This ensures children
        inherit settings like cache_time, include/exclude patterns, etc.

        Returns:
            dict: Copy of self._kw suitable for child resolver initialization.
        """
        return dict(self._kw)
