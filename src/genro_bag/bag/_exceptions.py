# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Bag exceptions — isolated module to avoid circular imports."""


class BagException(Exception):
    """Base exception for Bag operations."""


class BagSerializationError(BagException):
    """A value cannot be written to the wire.

    Always names the offending node and, for attributes, the key: the
    underlying TypeError only reports the type, which is useless on a
    Bag of any size.
    """
