"""Spec test: ``EnvResolver`` with ``dtype`` kwarg converts the value
read from ``os.environ`` to a Python type via ``tytx_decode``.

Depends on test_resolvers.py (base resolver).

Contract: if ``dtype`` is set and the variable is present, the
resolver internally composes the string ``value::dtype`` and passes it to
``tytx_decode``. Without ``dtype`` (default), the behavior is the
historical one: returns the raw string or the ``default``.

## Scale

1. dtype='L' on valid integer              returns int
2. dtype='B' on boolean                    returns bool
3. dtype='R' on float                      returns float
4. no dtype                                returns string (current behavior)
5. missing variable with dtype             returns None, no conversion
6. value not parsable for the dtype        raises exception
"""

from __future__ import annotations

import pytest

from genro_bag import Bag
from genro_bag.resolvers import EnvResolver

# =============================================================================
# 1. dtype='L' su intero valido
# =============================================================================


class TestDtypeLong:
    def test_long_dtype_converts_to_int(self, monkeypatch):
        monkeypatch.setenv("X_PORT", "8080")
        bag = Bag()
        bag["port"] = EnvResolver("X_PORT", dtype="L")
        assert bag["port"] == 8080
        assert type(bag["port"]) is int


# =============================================================================
# 2. dtype='B' per boolean
# =============================================================================


class TestDtypeBool:
    def test_bool_dtype_true(self, monkeypatch):
        monkeypatch.setenv("X_FLAG", "true")
        bag = Bag()
        bag["flag"] = EnvResolver("X_FLAG", dtype="B")
        assert bag["flag"] is True

    def test_bool_dtype_false(self, monkeypatch):
        monkeypatch.setenv("X_FLAG", "false")
        bag = Bag()
        bag["flag"] = EnvResolver("X_FLAG", dtype="B")
        assert bag["flag"] is False


# =============================================================================
# 3. dtype='R' per real/float
# =============================================================================


class TestDtypeReal:
    def test_real_dtype_converts_to_float(self, monkeypatch):
        monkeypatch.setenv("X_RATIO", "3.14")
        bag = Bag()
        bag["ratio"] = EnvResolver("X_RATIO", dtype="R")
        assert bag["ratio"] == 3.14
        assert type(bag["ratio"]) is float


# =============================================================================
# 4. no dtype: current behaviour (string)
# =============================================================================


class TestNoDtype:
    def test_without_dtype_returns_string(self, monkeypatch):
        monkeypatch.setenv("X_RAW", "8080")
        bag = Bag()
        bag["raw"] = EnvResolver("X_RAW")
        assert bag["raw"] == "8080"
        assert type(bag["raw"]) is str


# =============================================================================
# 5. variabile assente: nessuna conversione
# =============================================================================


class TestMissingVariable:
    def test_missing_var_with_dtype_returns_none(self, monkeypatch):
        """If the variable is not set and default=None, returns None
        without attempting conversion."""
        monkeypatch.delenv("X_MISSING", raising=False)
        bag = Bag()
        bag["x"] = EnvResolver("X_MISSING", dtype="L")
        assert bag["x"] is None


# =============================================================================
# 6. value not parsable for the dtype
# =============================================================================


class TestUnparsableValue:
    def test_unparsable_value_raises(self, monkeypatch):
        """A string not convertible to the requested dtype raises
        ValueError: the caller who declares the type assumes responsibility
        for the form of the value."""
        monkeypatch.setenv("X_BAD", "not_a_number")
        bag = Bag()
        bag["x"] = EnvResolver("X_BAD", dtype="L")
        with pytest.raises(ValueError):
            _ = bag["x"]
