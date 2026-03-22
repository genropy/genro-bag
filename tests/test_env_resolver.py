# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for EnvResolver."""

from __future__ import annotations

import os

import pytest

from genro_bag import Bag
from genro_bag.resolvers import EnvResolver


ENV_PREFIX = "_GENRO_TEST_ENV_"


@pytest.fixture(autouse=True)
def _clean_env():
    """Remove all test env vars before and after each test."""
    keys = [k for k in os.environ if k.startswith(ENV_PREFIX)]
    for k in keys:
        del os.environ[k]
    yield
    keys = [k for k in os.environ if k.startswith(ENV_PREFIX)]
    for k in keys:
        del os.environ[k]


class TestEnvResolverStandalone:
    """EnvResolver without Bag integration."""

    def test_reads_existing_variable(self):
        """Returns the value of an existing environment variable."""
        os.environ[f"{ENV_PREFIX}HOST"] = "db.example.com"
        resolver = EnvResolver(f"{ENV_PREFIX}HOST")
        assert resolver() == "db.example.com"

    def test_missing_variable_returns_default(self):
        """Returns the default value when the variable is not set."""
        resolver = EnvResolver(f"{ENV_PREFIX}MISSING", default="fallback")
        assert resolver() == "fallback"

    def test_missing_variable_no_default_returns_none(self):
        """Returns None when variable is not set and no default."""
        resolver = EnvResolver(f"{ENV_PREFIX}MISSING")
        assert resolver() is None

    def test_reflects_runtime_changes(self):
        """With cache_time=0, picks up env changes immediately."""
        os.environ[f"{ENV_PREFIX}PORT"] = "5432"
        resolver = EnvResolver(f"{ENV_PREFIX}PORT")

        assert resolver() == "5432"

        os.environ[f"{ENV_PREFIX}PORT"] = "3306"
        assert resolver() == "3306"

    def test_cache_prevents_reread(self):
        """With cache_time>0, value is cached."""
        os.environ[f"{ENV_PREFIX}CACHED"] = "original"
        resolver = EnvResolver(f"{ENV_PREFIX}CACHED", cache_time=300)

        assert resolver() == "original"

        os.environ[f"{ENV_PREFIX}CACHED"] = "changed"
        assert resolver() == "original"  # still cached

    def test_cache_reset_forces_reread(self):
        """After reset(), cached value is re-read from environment."""
        os.environ[f"{ENV_PREFIX}RESET"] = "v1"
        resolver = EnvResolver(f"{ENV_PREFIX}RESET", cache_time=300)

        assert resolver() == "v1"
        os.environ[f"{ENV_PREFIX}RESET"] = "v2"
        assert resolver() == "v1"

        resolver.reset()
        assert resolver() == "v2"


class TestEnvResolverWithBag:
    """EnvResolver attached to a Bag node."""

    def test_bag_access_resolves_env(self):
        """Accessing a Bag node resolves the environment variable."""
        os.environ[f"{ENV_PREFIX}DB"] = "postgres"
        bag = Bag()
        bag["db_type"] = EnvResolver(f"{ENV_PREFIX}DB")
        assert bag["db_type"] == "postgres"

    def test_bag_reflects_env_changes(self):
        """Bag access reflects runtime environment changes."""
        os.environ[f"{ENV_PREFIX}MODE"] = "development"
        bag = Bag()
        bag["mode"] = EnvResolver(f"{ENV_PREFIX}MODE")

        assert bag["mode"] == "development"

        os.environ[f"{ENV_PREFIX}MODE"] = "production"
        assert bag["mode"] == "production"

    def test_node_attr_overrides_var_name(self):
        """Changing var_name via node attr reads a different variable."""
        os.environ[f"{ENV_PREFIX}A"] = "value_a"
        os.environ[f"{ENV_PREFIX}B"] = "value_b"

        bag = Bag()
        bag.set_item("setting", EnvResolver(f"{ENV_PREFIX}A"))

        assert bag["setting"] == "value_a"

        bag.set_attr("setting", var_name=f"{ENV_PREFIX}B")
        assert bag["setting"] == "value_b"

    def test_default_value_via_bag(self):
        """Default value is used when variable is not set."""
        bag = Bag()
        bag.set_item("setting", EnvResolver(f"{ENV_PREFIX}NOEXIST", default="fallback"))
        assert bag["setting"] == "fallback"
