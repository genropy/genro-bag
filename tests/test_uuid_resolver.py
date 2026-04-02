# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for UuidResolver."""

from __future__ import annotations

import uuid

import pytest

from genro_bag import Bag
from genro_bag.resolvers import UuidResolver


class TestUuidResolverStandalone:
    """UuidResolver without Bag integration."""

    def test_generates_valid_uuid4(self):
        """Default generates a valid UUID v4 string."""
        resolver = UuidResolver()
        result = resolver()
        uuid.UUID(result, version=4)

    def test_generates_valid_uuid1(self):
        """With version='uuid1', generates a valid UUID v1 string."""
        resolver = UuidResolver("uuid1")
        result = resolver()
        uuid.UUID(result, version=1)

    def test_cached_returns_same_value(self):
        """With cache_time=False (default), returns the same UUID every time."""
        resolver = UuidResolver()
        first = resolver()
        second = resolver()
        assert first == second

    def test_reset_generates_new_uuid(self):
        """After reset(), a new UUID is generated."""
        resolver = UuidResolver()
        first = resolver()
        resolver.reset()
        second = resolver()
        assert first != second

    def test_invalid_version_raises(self):
        """Unsupported version raises ValueError."""
        resolver = UuidResolver("uuid5")
        with pytest.raises(ValueError, match="Unsupported UUID version"):
            resolver()


class TestUuidResolverWithBag:
    """UuidResolver attached to a Bag node."""

    def test_bag_access_returns_uuid(self):
        """Accessing a Bag node returns a UUID string."""
        bag = Bag()
        bag["id"] = UuidResolver()
        result = bag["id"]
        uuid.UUID(result, version=4)

    def test_bag_access_returns_same_uuid(self):
        """Repeated access returns the same UUID."""
        bag = Bag()
        bag["id"] = UuidResolver()
        first = bag["id"]
        second = bag["id"]
        assert first == second

    def test_different_nodes_get_different_uuids(self):
        """Each node gets its own UUID."""
        bag = Bag()
        bag["id1"] = UuidResolver()
        bag["id2"] = UuidResolver()
        assert bag["id1"] != bag["id2"]

    def test_uuid1_via_bag(self):
        """UUID v1 works through Bag access."""
        bag = Bag()
        bag["ts_id"] = UuidResolver("uuid1")
        result = bag["ts_id"]
        uuid.UUID(result, version=1)
