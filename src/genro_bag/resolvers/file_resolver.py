# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""File resolver — lazy file loading with format detection.

Load files on demand into a Bag, detecting format from extension::

    from genro_bag import Bag
    from genro_bag.resolvers import FileResolver

    bag = Bag()
    bag['style'] = FileResolver('style.css')
    bag['style']  # reads file content as string

    bag['data'] = FileResolver('products.json', as_bag=True)
    bag['data']   # parses JSON and returns a Bag

    bag['contacts'] = FileResolver('contacts.csv')
    bag['contacts']  # parses CSV, returns Bag of records

Supported formats:
- .bag.json, .bag.mp, .xml  -> Bag (via fill_from)
- .json                     -> dict/list/scalar (Bag if as_bag=True)
- .csv                      -> Bag of records (rows as nodes with column attrs)
- .css, .txt, .html, .md    -> text string
- (other)                   -> text string (fallback)

With ``cache_time=0`` (default) the file is re-read on every access.
With ``cache_time=N`` the content is cached for N seconds.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any

from ..bag._core import Bag
from ..resolver import BagResolver


class FileResolver(BagResolver):
    """Resolver that lazily loads a file with format detection by extension."""

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": True,
        "as_bag": None,
        "base_path": None,
        "encoding": "utf-8",
        "csv_delimiter": ",",
        "csv_has_header": True,
    }
    class_args: list[str] = ["path"]
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag",
        "base_path", "encoding", "csv_delimiter", "csv_has_header",
    }

    def load(self) -> Any:
        """Load file content based on extension."""
        path = self._resolve_path()
        if not os.path.isfile(path):
            raise FileNotFoundError(f"FileResolver: file not found: {path}")
        fmt = self._detect_format(path)
        loader = _FORMAT_DISPATCH.get(fmt)
        if loader is not None:
            return loader(self, path)
        return self._load_text(path)

    def _resolve_path(self) -> str:
        """Resolve file path, applying base_path for relative paths."""
        path: str = self.kw["path"]
        if not os.path.isabs(path):
            base: str = self.kw.get("base_path") or os.getcwd()
            path = os.path.join(base, path)
        return path

    def _detect_format(self, path: str) -> str:
        """Detect format from file extension. Returns canonical suffix key."""
        if path.endswith(".bag.json"):
            return ".bag.json"
        if path.endswith(".bag.mp"):
            return ".bag.mp"
        _, ext = os.path.splitext(path)
        return ext.lower()

    def _load_bag_serialized(self, path: str) -> Bag:
        """Load native Bag formats via fill_from."""
        return Bag().fill_from(path)

    def _load_json(self, path: str) -> Any:
        """Parse JSON file. Result type depends on content and as_bag."""
        encoding = self.kw.get("encoding", "utf-8")
        with open(path, encoding=encoding) as f:
            raw = f.read()
        if self.kw.get("as_bag"):
            return Bag.from_json(raw)
        return json.loads(raw)

    def _load_csv(self, path: str) -> Bag:
        """Parse CSV file, return Bag of records."""
        encoding = self.kw.get("encoding", "utf-8")
        delimiter = self.kw.get("csv_delimiter", ",")
        has_header = self.kw.get("csv_has_header", True)
        result = Bag()
        with open(path, encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            if has_header:
                headers = next(reader, None)
                if headers is None:
                    return result
            else:
                headers = None
            for i, row in enumerate(reader):
                if headers:
                    attrs = dict(zip(headers, row, strict=False))
                else:
                    attrs = {f"c{j}": val for j, val in enumerate(row)}
                result.set_item(f"r{i}", None, _attributes=attrs)
        return result

    def _load_text(self, path: str) -> str:
        """Load file as text string."""
        encoding = self.kw.get("encoding", "utf-8")
        with open(path, encoding=encoding) as f:
            return f.read()


_FORMAT_DISPATCH: dict[str, Any] = {
    ".bag.json": FileResolver._load_bag_serialized,
    ".bag.mp": FileResolver._load_bag_serialized,
    ".xml": FileResolver._load_bag_serialized,
    ".json": FileResolver._load_json,
    ".csv": FileResolver._load_csv,
    ".css": FileResolver._load_text,
    ".txt": FileResolver._load_text,
    ".html": FileResolver._load_text,
    ".md": FileResolver._load_text,
}
