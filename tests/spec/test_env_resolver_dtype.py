"""Spec test: ``EnvResolver`` con kwarg ``dtype`` converte il valore
letto da ``os.environ`` in un tipo Python via ``tytx_decode``.

Dipende da test_resolvers.py (resolver di base).

Contratto: se ``dtype`` e' impostato e la variabile e' presente, il
resolver compone internamente la stringa ``value::dtype`` e la passa a
``tytx_decode``. Senza ``dtype`` (default) il comportamento e' quello
storico: ritorna la stringa grezza o il ``default``.

## Scala

1. dtype='L' su intero valido            ritorna int
2. dtype='B' su boolean                  ritorna bool
3. dtype='R' su float                    ritorna float
4. nessun dtype                          ritorna stringa (comportamento attuale)
5. variabile assente con dtype           ritorna None, niente conversione
6. valore non parsabile per il dtype     solleva eccezione
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
# 4. nessun dtype: comportamento attuale (stringa)
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
        """Se la variabile non e' settata e default=None, ritorna None
        senza tentare la conversione."""
        monkeypatch.delenv("X_MISSING", raising=False)
        bag = Bag()
        bag["x"] = EnvResolver("X_MISSING", dtype="L")
        assert bag["x"] is None


# =============================================================================
# 6. valore non parsabile per il dtype
# =============================================================================


class TestUnparsableValue:
    def test_unparsable_value_raises(self, monkeypatch):
        """Una stringa non convertibile per il dtype richiesto solleva
        ValueError: il chiamante che dichiara il tipo si assume la
        responsabilita' della forma del valore."""
        monkeypatch.setenv("X_BAD", "not_a_number")
        bag = Bag()
        bag["x"] = EnvResolver("X_BAD", dtype="L")
        with pytest.raises(ValueError):
            _ = bag["x"]
