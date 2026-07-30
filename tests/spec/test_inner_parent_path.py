"""Spec test: ``#parent`` segment (alias ``../``) must be resolved
both at path start and as inner segment, consistent with legacy
gnr/core/gnrbag.py.

Depends on test_basic.py (set_item, get_item).

Contract:
- ``r.get_item("a.x.#parent.c")`` goes up to parent level of ``x``
  (i.e. ``a``) and reads ``c``.
- ``r.get_item("a.x.../c")`` is alias of ``a.x.#parent.c`` (alias
  ``../`` consumes preceding dot-separator, so three dots needed
  between segment and final c: ``x`` + ``.`` + ``../`` -> ``...``).
- Consecutive ``#parent`` walk multiple levels up.
- From root, further ``#parent`` does not crash but makes path
  unresolvable (``None``).
- ``set_item`` with inner ``#parent`` creates nodes at right level.

## Scale

1. inner #parent reads sibling                        a.x.#parent.c -> 'C'
2. ../ alias                                          a.x../c       -> 'C'
3. multiple consecutive #parent                       a.b.x.#parent.#parent.z -> 'Z'
4. #parent from root -> None (no crash)
5. set_item with inner #parent creates at right level
6. #parent at start still works                       regression
"""

from __future__ import annotations

from genro_bag import Bag

# =============================================================================
# 1. inner #parent reads a sibling of the intermediate node
# =============================================================================


class TestInnerParentReadsSibling:
    def test_inner_parent_walks_up_then_reads_sibling(self):
        """a.x is a Bag; a.x.#parent goes up to a; .c reads sibling."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_item("a.c", "C")
        r.set_backref()
        assert r.get_item("a.x.#parent.c") == "C"


# =============================================================================
# 2. the ../ alias must work the same way
# =============================================================================


class TestSlashSlashAlias:
    def test_slash_slash_alias_resolves_inner_parent(self):
        """``../`` is textual alias of ``#parent``. Syntax requires triple-dot
        because replace is literal: ``../`` consumes dot-separator
        (``.`` + ``../`` -> ``...``)."""
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
        """a.b.x.#parent.#parent.z should walk up from x to b to a, then read z."""
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
        """From root cannot go up: get_item returns None without exceptions."""
        r = Bag()
        r.set_item("a", 1)
        # no set_backref intentional: root has no parent anyway
        assert r.get_item("#parent.a") is None


# =============================================================================
# 5. set_item con inner #parent
# =============================================================================


class TestSetItemWithInnerParent:
    def test_set_item_with_inner_parent_writes_at_right_level(self):
        """set_item('a.x.#parent.d', 'D') must create a.d='D'."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_backref()
        r.set_item("a.x.#parent.d", "D")
        assert r.get_item("a.d") == "D"
        # other branches untouched
        assert r.get_item("a.x.y") == "Y"


# =============================================================================
# 6. regressione: leading #parent continua a funzionare
# =============================================================================


class TestLeadingParentStillWorks:
    def test_leading_parent_on_subbag_resolves_to_root(self):
        """From a sub-bag with backref, leading #parent goes to root."""
        r = Bag()
        r.set_item("a.x.y", "Y")
        r.set_item("a.c", "C")
        r.set_backref()
        subbag = r["a.x"]
        # subbag is a Bag with parent = a
        assert subbag.get_item("#parent.c") == "C"
