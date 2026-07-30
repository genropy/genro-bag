"""Spec test: ``Bag.__contains__`` (operator ``in``) must be
a pure existence check, static and supporting ``?attr`` syntax
like other read methods.

Depends on test_basic.py (set_item) and test_resolvers.py (resolver).

Contract:
- ``"a.b" in bag`` returns True if path exists, False otherwise.
- ``"a.b?color" in bag`` returns True if node a.b exists AND has
  ``color`` attribute. False if path or attribute missing.
- ``"a.b?a1&a2" in bag`` returns True only if ALL attributes
  exist on node. (Uniform convention with get.)
- ``in`` is static: does not trigger resolver along path.

## Scale

1. existing path                        True
2. missing path                         False
3. ?attr existing                       True
4. ?attr missing                        False
5. ?a&b: all present                    True
6. ?a&b: one missing                    False
7. ?attr on missing path                False
8. in does NOT trigger resolver         load not called
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver

# =============================================================================
# 1-2. path existence
# =============================================================================


class TestContainsPath:
    def test_existing_path_returns_true(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.bb" in b
        assert "aa" in b

    def test_missing_path_returns_false(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.cc" not in b
        assert "zz" not in b


# =============================================================================
# 3-4. ?attr singolo
# =============================================================================


class TestContainsQueryAttr:
    def test_existing_attribute_returns_true(self):
        b = Bag()
        b.set_item("aa.bb", "foo", color="red", width=56)
        assert "aa.bb?color" in b
        assert "aa.bb?width" in b

    def test_missing_attribute_returns_false(self):
        b = Bag()
        b.set_item("aa.bb", "foo", color="red")
        assert "aa.bb?missing" not in b


# =============================================================================
# 5-6. ?a&b: every attribute must exist
# =============================================================================


class TestContainsQueryMultipleAttrs:
    def test_all_attributes_present_returns_true(self):
        b = Bag()
        b.set_item("x", "v", a=1, b=2, c=3)
        assert "x?a&b" in b
        assert "x?a&b&c" in b

    def test_one_missing_attribute_returns_false(self):
        b = Bag()
        b.set_item("x", "v", a=1, b=2)
        assert "x?a&missing" not in b


# =============================================================================
# 7. ?attr su path inesistente
# =============================================================================


class TestContainsQueryAttrOnMissingPath:
    def test_query_attr_on_missing_path_returns_false(self):
        b = Bag()
        b["aa.bb"] = "foo"
        assert "aa.cc?color" not in b
        assert "zz?anything" not in b


# =============================================================================
# 8-9. `in` does NOT trigger resolvers (static semantics)
# =============================================================================


class TestContainsIsStatic:
    def test_in_does_not_trigger_resolver(self):
        """Operator ``in`` must be purely static: no resolver is executed
        during a containment check. Direct consequence: an untriggered resolver
        is opaque to ``in``, the path beneath it does not appear present until
        the resolver is loaded explicitly."""
        calls = []

        class CountingResolver(BagSyncResolver):
            def load(self):
                calls.append("load")
                inner = Bag()
                inner["bb"] = "computed"
                return inner

        b = Bag()
        b.set_item("aa", CountingResolver())

        # Path under resolver is opaque to `in` until resolver is loaded.
        # No side-effects.
        assert ("aa.bb" in b) is False
        assert calls == []

        # Node `aa` (resolver level) is visible statically.
        assert "aa" in b
        assert calls == []

    def test_in_remains_opaque_to_resolver_content(self):
        """Even after resolver is explicitly loaded, generated content is not
        materialized on the node (stays in resolver). ``in`` continues not to
        see it: consistent with its static semantics, and user who wants to
        know if ``aa.bb`` truly exists must use ``bag.get_node('aa.bb')`` (not
        static)."""
        calls = []

        class CountingResolver(BagSyncResolver):
            def load(self):
                calls.append("load")
                inner = Bag()
                inner["bb"] = "computed"
                return inner

        b = Bag()
        b.set_item("aa", CountingResolver())

        # Explicit trigger of resolver
        _ = b["aa"]
        assert calls == ["load"]

        # `in` remains static: opaque even after trigger
        assert ("aa.bb" in b) is False
        # And did not add calls (does not re-trigger)
        assert calls == ["load"]

        # To test true presence of path, use non-static API
        assert b.get_node("aa.bb") is not None
