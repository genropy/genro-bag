# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SerializedBagResolver - lazily loads a Bag from a serialized file."""

from __future__ import annotations

from ..resolver import BagResolver


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
        >>> bag = resolver()  # or resolver.load()
        >>> bag['config.host']
        'localhost'

        >>> # Used by DirectoryResolver for XML files
        >>> dir_resolver = DirectoryResolver('/data', ext='xml')
        >>> # When accessing an XML file, it returns SerializedBagResolver
    """

    class_kwargs = {'cache_time': 500, 'read_only': True}
    class_args = ['path']

    def load(self):
        """Load and return the Bag from the serialized file.

        Uses Bag constructor which delegates to fill_from() for
        format detection based on file extension.

        Returns:
            Bag: The deserialized Bag hierarchy.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file extension is not recognized.
        """
        from ..bag import Bag
        return Bag(self._kw['path'])
