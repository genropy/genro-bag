# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""TxtDocResolver - lazily loads text file content."""

from __future__ import annotations

from ..resolver import BagResolver


class TxtDocResolver(BagResolver):
    class_kwargs = {'cache_time': 500,
                   'read_only': True
    }
    class_args = ['path']

    def load(self):
        with open(self._kw['path'], mode='rb') as f:
            result = f.read()
        return result
