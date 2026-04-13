"""Tests for gnrbag_wrapper — __getattr__ chain, deprecation warnings, overrides."""

import warnings

import pytest

from replacement.gnrbag_wrapper import (
    Bag,
    BagCbResolver,
    BagNode,
    BagResolver,
    _camel_to_snake,
)


# ---------------------------------------------------------------------------
# _camel_to_snake helper
# ---------------------------------------------------------------------------

class TestCamelToSnake:
    def test_simple(self):
        assert _camel_to_snake("getItem") == "get_item"

    def test_multi_word(self):
        assert _camel_to_snake("setBackRef") == "set_back_ref"

    def test_to_xml(self):
        assert _camel_to_snake("toXml") == "to_xml"

    def test_from_json(self):
        assert _camel_to_snake("fromJson") == "from_json"

    def test_is_empty(self):
        assert _camel_to_snake("isEmpty") == "is_empty"

    def test_as_dict(self):
        assert _camel_to_snake("asDict") == "as_dict"

    def test_already_snake(self):
        assert _camel_to_snake("get_item") == "get_item"

    def test_single_word(self):
        assert _camel_to_snake("keys") == "keys"


# ---------------------------------------------------------------------------
# __getattr__ fallback chain
# ---------------------------------------------------------------------------

class TestGetattr:
    """Test the 3-level __getattr__ fallback: wrp_ → snake_case → AttributeError."""

    def test_level1_wrp_method(self):
        """wrp_getItem exists → getItem is found via __getattr__ level 1."""
        b = Bag()
        b["x"] = 10
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.getItem("x")
        assert result == 10
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()

    def test_level2_auto_conversion(self):
        """No wrp_, but snake_case method exists → found via level 2.

        BagNode.parentBag has no wrp_ but parent_bag property exists.
        """
        b = Bag()
        b.set_backref()
        b["x"] = 1
        node = b.get_node("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = node.parentBag
        assert result is b
        assert len(w) == 1
        assert "parent_bag" in str(w[0].message)

    def test_level3_attribute_error(self):
        """No wrp_, no snake_case match → AttributeError."""
        b = Bag()
        with pytest.raises(AttributeError, match="nonExistentMethod"):
            b.nonExistentMethod()

    def test_snake_case_direct_no_warning(self):
        """Direct snake_case call bypasses __getattr__ — no warning."""
        b = Bag()
        b["x"] = 10
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.get_item("x")
        assert result == 10
        assert len(w) == 0

    def test_private_attr_raises(self):
        """__getattr__ skips attributes starting with _."""
        b = Bag()
        with pytest.raises(AttributeError):
            b._nonexistent

    def test_wrp_setBackRef(self):
        """setBackRef → wrp_setBackRef via __getattr__ level 1."""
        b = Bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.setBackRef()
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
        assert b.backref is True

    def test_wrp_clearBackRef(self):
        """clearBackRef → wrp_clearBackRef via __getattr__ level 1."""
        b = Bag()
        b.set_backref()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.clearBackRef()
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
        assert b.backref is False


# ---------------------------------------------------------------------------
# Override: Bag.pop
# ---------------------------------------------------------------------------

class TestBagPop:
    def test_pop_with_default(self):
        """pop(path, default=x) — no warning."""
        b = Bag()
        b["a"] = 1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.pop("a", default="nope")
        assert result == 1
        assert len(w) == 0

    def test_pop_missing_with_default(self):
        b = Bag()
        result = b.pop("missing", default="fallback")
        assert result == "fallback"

    def test_pop_with_dflt_deprecated(self):
        """pop(path, dflt=x) — deprecation warning."""
        b = Bag()
        b["a"] = 1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.pop("missing", dflt="old_style")
        assert result == "old_style"
        assert len(w) == 1
        assert "dflt" in str(w[0].message)

    def test_pop_positional(self):
        """pop(path, value) — positional, no warning."""
        b = Bag()
        result = b.pop("missing", "positional_default")
        assert result == "positional_default"


# ---------------------------------------------------------------------------
# Override: Bag.walk
# ---------------------------------------------------------------------------

class TestBagWalk:
    def _make_bag(self):
        b = Bag()
        b["a"] = 1
        b["b"] = 2
        return b

    def test_walk_with_static(self):
        """walk(static=True) — no warning."""
        b = self._make_bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nodes = list(b.walk(static=True))
        assert len(nodes) == 2
        assert len(w) == 0

    def test_walk_with_mode_keyword(self):
        """walk(_mode='static') — deprecation warning."""
        b = self._make_bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nodes = list(b.walk(_mode="static"))
        assert len(nodes) == 2
        assert len(w) == 1
        assert "_mode" in str(w[0].message)

    def test_walk_with_st_mode_positional(self):
        """walk(cb, 'static') — positional st_mode, deprecation warning."""
        b = self._make_bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nodes = list(b.walk(None, "static"))
        assert len(nodes) == 2
        assert len(w) == 1
        assert "st_mode" in str(w[0].message)

    def test_walk_with_st_mode_false(self):
        """walk(cb, '') — empty string means static=False."""
        b = self._make_bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nodes = list(b.walk(None, ""))
        assert len(nodes) == 2
        assert len(w) == 1

    def test_walk_default_no_warning(self):
        """walk() with defaults — no warning."""
        b = self._make_bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            nodes = list(b.walk())
        assert len(nodes) == 2
        assert len(w) == 0


# ---------------------------------------------------------------------------
# Override: Bag.subscribe / unsubscribe
# ---------------------------------------------------------------------------

class TestBagSubscribe:
    def test_subscribe_snake_case(self):
        """subscribe(subscriber_id=...) — no warning."""
        b = Bag()
        b.set_backref()
        called = []
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.subscribe(subscriber_id="s1", any=lambda *a, **kw: called.append(1))
        assert len(w) == 0

    def test_subscribe_camel_case(self):
        """subscribe(subscriberId=...) — deprecation warning."""
        b = Bag()
        b.set_backref()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.subscribe(subscriberId="s1", any=lambda *a, **kw: None)
        assert len(w) == 1
        assert "subscriberId" in str(w[0].message)

    def test_unsubscribe_camel_case(self):
        """unsubscribe(subscriberId=...) — deprecation warning."""
        b = Bag()
        b.set_backref()
        b.subscribe(subscriber_id="s1", any=lambda *a, **kw: None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.unsubscribe(subscriberId="s1", any=True)
        assert len(w) == 1
        assert "subscriberId" in str(w[0].message)


# ---------------------------------------------------------------------------
# Override: Bag.digest
# ---------------------------------------------------------------------------

class TestBagDigest:
    def test_digest_as_columns(self):
        """digest(as_columns=True) — no warning."""
        b = Bag()
        b["a"] = 1
        b["b"] = 2
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.digest("#k,#v", as_columns=True)
        assert len(w) == 0
        assert result == [["a", "b"], [1, 2]]

    def test_digest_asColumns_deprecated(self):
        """digest(asColumns=True) — deprecation warning."""
        b = Bag()
        b["a"] = 1
        b["b"] = 2
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.digest("#k,#v", asColumns=True)
        assert len(w) == 1
        assert "asColumns" in str(w[0].message)
        assert result == [["a", "b"], [1, 2]]


# ---------------------------------------------------------------------------
# Override: Bag.update
# ---------------------------------------------------------------------------

class TestBagUpdate:
    def test_update_simple(self):
        """update(source) — no warning, delegates to super()."""
        b = Bag()
        b["a"] = 1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.update({"a": 10, "b": 2})
        assert b["a"] == 10
        assert b["b"] == 2
        assert len(w) == 0

    def test_update_ignore_none(self):
        """update(source, ignore_none=True) — no warning."""
        b = Bag()
        b["a"] = 1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.update({"a": None}, ignore_none=True)
        assert b["a"] == 1
        assert len(w) == 0

    def test_update_ignoreNone_deprecated(self):
        """update(source, ignoreNone=True) — deprecation warning."""
        b = Bag()
        b["a"] = 1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.update({"a": None}, ignoreNone=True)
        assert b["a"] == 1
        assert len(w) == 1
        assert "ignoreNone" in str(w[0].message)

    def test_update_resolved_deprecated(self):
        """update(source, resolved=True) — deprecation warning."""
        b = Bag()
        other = Bag()
        other["x"] = 5
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.update(other, resolved=True)
        assert b["x"] == 5
        assert any("resolved" in str(x.message) for x in w)


# ---------------------------------------------------------------------------
# Override: BagNode.subscribe / unsubscribe
# ---------------------------------------------------------------------------

class TestBagNodeSubscribe:
    def test_node_subscribe_snake_case(self):
        """BagNode.subscribe(subscriber_id=...) — no warning."""
        b = Bag()
        b["x"] = 1
        node = b.get_node("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            node.subscribe(subscriber_id="s1", callback=lambda *a, **kw: None)
        assert len(w) == 0

    def test_node_subscribe_camel_case(self):
        """BagNode.subscribe(subscriberId=...) — deprecation warning."""
        b = Bag()
        b["x"] = 1
        node = b.get_node("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            node.subscribe(subscriberId="s1", callback=lambda *a, **kw: None)
        assert len(w) == 1
        assert "subscriberId" in str(w[0].message)

    def test_node_unsubscribe_camel_case(self):
        """BagNode.unsubscribe(subscriberId=...) — deprecation warning."""
        b = Bag()
        b["x"] = 1
        node = b.get_node("x")
        node.subscribe(subscriber_id="s1", callback=lambda *a, **kw: None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            node.unsubscribe(subscriberId="s1")
        assert len(w) == 1
        assert "subscriberId" in str(w[0].message)


# ---------------------------------------------------------------------------
# BagResolver.__init__ kwargs remap
# ---------------------------------------------------------------------------

class TestBagResolverInit:
    def test_snake_case_kwargs(self):
        """BagResolver(cache_time=300) — no warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = BagResolver(cache_time=300, read_only=True)
        assert r.cache_time == 300
        assert r.read_only is True
        assert len(w) == 0

    def test_camel_case_kwargs(self):
        """BagResolver(cacheTime=300) — deprecation warning + remap."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            r = BagResolver(cacheTime=300, readOnly=False)
        assert r.cache_time == 300
        assert r.read_only is False
        assert len(w) == 2  # one per kwarg


# ---------------------------------------------------------------------------
# BagNode wrp_* via __getattr__
# ---------------------------------------------------------------------------

class TestBagNodeGetattr:
    def test_getValue(self):
        """BagNode.getValue via __getattr__ → wrp_getValue."""
        b = Bag()
        b["x"] = 42
        node = b.get_node("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = node.getValue()
        assert result == 42
        assert len(w) == 1

    def test_getLabel(self):
        """BagNode.getLabel via __getattr__ → wrp_getLabel."""
        b = Bag()
        b["mykey"] = 1
        node = b.get_node("mykey")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = node.getLabel()
        assert result == "mykey"
        assert len(w) == 1

    def test_getAttr(self):
        """BagNode.getAttr via __getattr__ → wrp_getAttr."""
        b = Bag()
        b.set_item("x", 1, _attributes={"color": "red"})
        node = b.get_node("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = node.getAttr("color")
        assert result == "red"
        assert len(w) == 1


# ---------------------------------------------------------------------------
# Bag wrp_* via __getattr__
# ---------------------------------------------------------------------------

class TestBagWrpMethods:
    def test_setItem_getItem(self):
        """setItem/getItem via __getattr__."""
        b = Bag()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            b.setItem("path.to.val", 99)
            result = b.getItem("path.to.val")
        assert result == 99

    def test_getNode(self):
        """getNode via __getattr__."""
        b = Bag()
        b["x"] = 1
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            node = b.getNode("x")
        assert node is not None
        assert node.label == "x"

    def test_isEmpty(self):
        """isEmpty via __getattr__."""
        b = Bag()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert b.isEmpty() is True
        b["a"] = 1
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert b.isEmpty() is False

    def test_iterkeys(self):
        """iterkeys via __getattr__."""
        b = Bag()
        b["a"] = 1
        b["b"] = 2
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = list(b.iterkeys())
        assert result == ["a", "b"]

    def test_formula_deprecated(self):
        """formula() → stub with deprecation warning."""
        b = Bag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.formula("x+1")
        assert result is None
        assert any("deprecated" in str(x.message).lower() for x in w)


# ---------------------------------------------------------------------------
# Dunder overrides
# ---------------------------------------------------------------------------

class TestDunderOverrides:
    def test_pow(self):
        """bag ** {'color': 'red'} updates parent node attrs."""
        parent = Bag()
        parent.set_backref()
        child = Bag()
        parent.set_item("child", child)
        child ** {"color": "red"}
        assert parent.get_attr("child", "color") == "red"

    def test_call_no_args(self):
        """bag() returns keys list."""
        b = Bag()
        b["a"] = 1
        b["b"] = 2
        assert b() == ["a", "b"]

    def test_call_with_path(self):
        """bag('a') returns value."""
        b = Bag()
        b["a"] = 42
        assert b("a") == 42


# ---------------------------------------------------------------------------
# WrapperBagNodeContainer: duplicates
# ---------------------------------------------------------------------------

class TestDuplicates:
    def test_add_duplicate(self):
        """addItem with duplicate labels."""
        b = Bag()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            b.addItem("item", "first")
            b.addItem("item", "second")
        keys = list(b.keys())
        assert keys.count("item") == 2
        values = list(b.values())
        assert "first" in values
        assert "second" in values
