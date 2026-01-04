# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Concrete BagResolver implementations.

This module provides ready-to-use resolver implementations:

- DirectoryResolver: Lazily loads directory contents as a Bag
- TxtDocResolver: Lazily loads text file content

Example:
    from genro_bag import Bag
    from genro_bag.resolvers import DirectoryResolver

    bag = Bag()
    bag['docs'] = DirectoryResolver('/path/to/docs', ext='txt')

    # Access triggers lazy loading
    for node in bag['docs']:
        print(node.label, node.attr)
"""

from .directory_resolver import DirectoryResolver
from .txt_doc_resolver import TxtDocResolver

__all__ = [
    'DirectoryResolver',
    'TxtDocResolver',
]
