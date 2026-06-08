"""Spec test: il segmento ``#parent`` (alias ``../``) deve essere
risolto sia in testa al path sia come segmento interno, coerentemente
col legacy gnr/core/gnrbag.py.

Dipende da test_basic.py (set_item, get_item).

Contratto:
- ``r.get_item("a.x.#parent.c")`` torna al livello del padre di ``x``
  (cioe' ``a``) e legge ``c``.
- ``r.get_item("a.x.../c")`` e' alias di ``a.x.#parent.c`` (l'alias
  ``../`` consuma il punto-separatore davanti, quindi servono tre punti
  fra il segmento e la c finale: ``x`` + ``.`` + ``../``  -> ``...``).
- ``#parent`` consecutivi camminano piu' livelli verso l'alto.
- Da root, un ``#parent`` ulteriore non rompe ma rende il path
  irrisolvibile (``None``).
- ``set_item`` con ``#parent`` interno crea i nodi al livello giusto.

## Scala

1. inner #parent legge fratello                       a.x.#parent.c -> 'C'
2. ../ alias                                          a.x../c       -> 'C'
3. multipli #parent consecutivi                       a.b.x.#parent.#parent.z -> 'Z'
4. #parent da root -> None (no crash)
5. set_item con inner #parent crea al livello giusto
6. #parent in testa continua a funzionare             regressione
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. inner #parent legge un fratello del nodo intermedio
# =============================================================================


class TestInnerParentReadsSibling:
    def test_inner_parent_walks_up_then_reads_sibling(self):
        """a.x e' una Bag; a.x.#parent torna ad a; .c legge il fratello."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_item("a.c", "C")
        r.set_backref()
        assert r.get_item("a.x.#parent.c") == "C"


# =============================================================================
# 2. ../ alias deve funzionare uguale
# =============================================================================


class TestSlashSlashAlias:
    def test_slash_slash_alias_resolves_inner_parent(self):
        """``../`` e' alias testuale di ``#parent``. La sintassi richiede il
        triplo-punto perche' la replace e' letterale: ``../`` consuma il
        punto-separatore (``.`` + ``../`` -> ``...``)."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_item("a.c", "C")
        r.set_backref()
        assert r.get_item("a.x.../c") == "C"


# =============================================================================
# 3. multipli #parent consecutivi
# =============================================================================


class TestMultipleConsecutiveParents:
    def test_two_consecutive_parents_walk_up_two_levels(self):
        """a.b.x.#parent.#parent.z dovrebbe salire da x a b a a, poi leggere z."""
        r = Bag()
        r.set_item("a.b.x.y", "Y")
        r.set_item("a.z", "Z")
        r.set_backref()
        assert r.get_item("a.b.x.#parent.#parent.z") == "Z"


# =============================================================================
# 4. #parent da root: irrisolvibile ma niente crash
# =============================================================================


class TestParentFromRoot:
    def test_parent_above_root_returns_none(self):
        """Da root non si puo' salire: get_item ritorna None senza eccezioni."""
        r = Bag()
        r.set_item("a", 1)
        # niente set_backref intenzionale: il root NON ha parent comunque
        assert r.get_item("#parent.a") is None


# =============================================================================
# 5. set_item con inner #parent
# =============================================================================


class TestSetItemWithInnerParent:
    def test_set_item_with_inner_parent_writes_at_right_level(self):
        """set_item('a.x.#parent.d', 'D') deve creare a.d='D'."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_backref()
        r.set_item("a.x.#parent.d", "D")
        assert r.get_item("a.d") == "D"
        # gli altri rami non sono toccati
        assert r.get_item("a.x.y") == "Y"


# =============================================================================
# 6. regressione: leading #parent continua a funzionare
# =============================================================================


class TestLeadingParentStillWorks:
    def test_leading_parent_on_subbag_resolves_to_root(self):
        """Da una sub-bag con backref, #parent in testa torna al root."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_item("a.c", "C")
        r.set_backref()
        subbag = r["a.x"]
        # subbag e' una Bag con parent = a
        assert subbag.get_item("#parent.c") == "C"
