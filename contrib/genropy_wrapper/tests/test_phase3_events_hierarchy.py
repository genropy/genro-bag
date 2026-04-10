"""Phase 3 tests: Events, Hierarchy, Resolvers.

Comparative tests across original gnr.core.gnrbag, new genro_bag,
and the compatibility wrapper. Tests cover:
- Area E: Events (subscribe/unsubscribe, event firing)
- Area F: Hierarchy (child, rowchild, merge, copy, diff, backref)
- Area G: Resolvers (setCallBackItem, setResolver, getResolver, BagCbResolver)
"""

import warnings

import pytest
import genro_bag
from gnr.core.gnrbag import BagCbResolver as OrigBagCbResolver
from genro_bag.resolver import BagCbResolver as NewBagCbResolver
from replacement.gnrbag import Bag as WrapperBag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impl_name(cls):
    """Derive implementation name from a Bag class."""
    module = cls.__module__
    if module == "gnr.core.gnrbag":
        return "original"
    elif module.startswith("genro_bag"):
        return "new"
    return "wrapper"


def _make_nested_bag(cls):
    """Create a nested bag: a={x:1, y:2}, b={z:3}, c=4."""
    b = cls()
    inner_a = cls()
    inner_a["x"] = 1
    inner_a["y"] = 2
    b["a"] = inner_a
    inner_b = cls()
    inner_b["z"] = 3
    b["b"] = inner_b
    b["c"] = 4
    return b


def _make_flat_bag(cls):
    """Create a flat bag: name=Alice, age=30, city=Rome."""
    b = cls()
    b["name"] = "Alice"
    b["age"] = 30
    b["city"] = "Rome"
    return b


# ===========================================================================
# AREA E: EVENTS
# ===========================================================================


class TestBackrefCamel:
    """Test setBackRef/clearBackRef via camelCase API (original + wrapper)."""

    def test_set_backref_enables_parent(self, bag_class_camel):
        """After setBackRef, nested Bag should have a parent reference."""
        parent = bag_class_camel()
        parent["child"] = bag_class_camel()
        parent.setBackRef()
        child_bag = parent["child"]
        assert child_bag.parent is parent

    def test_clear_backref_removes_parent(self, bag_class_camel):
        """After clearBackRef, parent reference should be cleared."""
        parent = bag_class_camel()
        parent["child"] = bag_class_camel()
        parent.setBackRef()
        parent.clearBackRef()
        child_bag = parent["child"]
        assert child_bag.parent is None

    def test_backref_property(self, bag_class_camel):
        """The backref property should reflect the current state."""
        b = bag_class_camel()
        assert not b.backref
        b.setBackRef()
        assert b.backref


class TestBackrefSnake:
    """Test set_backref/clear_backref via snake_case API (new + wrapper)."""

    def test_set_backref_enables_parent(self, bag_class_snake):
        """After set_backref, nested Bag should have a parent reference."""
        parent = bag_class_snake()
        parent["child"] = bag_class_snake()
        parent.set_backref()
        child_bag = parent["child"]
        assert child_bag.parent is parent

    def test_clear_backref(self, bag_class_snake):
        """After clear_backref, parent reference should be cleared."""
        parent = bag_class_snake()
        parent["child"] = bag_class_snake()
        parent.set_backref()
        parent.clear_backref()
        child_bag = parent["child"]
        assert child_bag.parent is None


class TestSubscribeCamel:
    """Test subscribe/unsubscribe with subscriberId (original + wrapper)."""

    def test_subscribe_insert_fires(self, bag_class_camel):
        """Subscribing to insert events should fire when items are added."""
        b = bag_class_camel()
        events = []
        b.subscribe(subscriberId="test", insert=lambda **kw: events.append(kw))
        b["x"] = 1
        assert len(events) == 1
        assert events[0]["evt"] == "ins"

    def test_subscribe_update_fires(self, bag_class_camel):
        """Subscribing to update events should fire when values change."""
        b = bag_class_camel()
        b["x"] = 1
        events = []
        b.subscribe(subscriberId="test", update=lambda **kw: events.append(kw))
        b["x"] = 2
        assert len(events) >= 1

    def test_subscribe_delete_fires(self, bag_class_camel):
        """Subscribing to delete events should fire when items are removed."""
        b = bag_class_camel()
        b["x"] = 1
        events = []
        b.subscribe(subscriberId="test", delete=lambda **kw: events.append(kw))
        b.pop("x")
        assert len(events) == 1
        assert events[0]["evt"] == "del"

    def test_subscribe_any(self, bag_class_camel):
        """Using any= should register for insert, update, and delete."""
        b = bag_class_camel()
        events = []
        b.subscribe(subscriberId="test", any=lambda **kw: events.append(kw["evt"]))
        b["x"] = 1  # insert
        b["x"] = 2  # update
        b.pop("x")  # delete
        assert "ins" in events
        assert "del" in events

    def test_unsubscribe(self, bag_class_camel):
        """Unsubscribing should stop events from firing."""
        b = bag_class_camel()
        events = []
        b.subscribe(subscriberId="test", any=lambda **kw: events.append(1))
        b.unsubscribe(subscriberId="test", any=True)
        b["x"] = 1
        assert len(events) == 0


class TestSubscribeSnake:
    """Test subscribe/unsubscribe with subscriber_id (new + wrapper)."""

    def test_subscribe_with_snake_case(self, bag_class_snake):
        """subscriber_id parameter should work."""
        b = bag_class_snake()
        events = []
        b.subscribe(subscriber_id="test", insert=lambda **kw: events.append(1))
        b["x"] = 1
        assert len(events) == 1

    def test_unsubscribe_with_snake_case(self, bag_class_snake):
        """Unsubscribe with subscriber_id should work."""
        b = bag_class_snake()
        events = []
        b.subscribe(subscriber_id="test", any=lambda **kw: events.append(1))
        b.unsubscribe(subscriber_id="test", any=True)
        b["x"] = 1
        assert len(events) == 0


class TestNodeSubscribe:
    """Test BagNode-level subscribe/unsubscribe (original + wrapper)."""

    def test_node_subscribe_value_change(self, bag_class_camel):
        """Node subscribers should fire when the node's value changes."""
        b = bag_class_camel()
        b.setBackRef()
        b["x"] = 1
        events = []
        node = b.getNode("x")
        node.subscribe(subscriberId="test", callback=lambda **kw: events.append(kw))
        b["x"] = 2
        assert len(events) >= 1
        assert events[0]["evt"] == "upd_value"

    def test_node_unsubscribe(self, bag_class_camel):
        """After unsubscribing, node events should no longer fire."""
        b = bag_class_camel()
        b.setBackRef()
        b["x"] = 1
        events = []
        node = b.getNode("x")
        node.subscribe(subscriberId="test", callback=lambda **kw: events.append(1))
        node.unsubscribe(subscriberId="test")
        b["x"] = 2
        assert len(events) == 0


# ===========================================================================
# AREA F: HIERARCHY
# ===========================================================================


class TestCopy:
    """Test copy() shallow semantics (original + wrapper)."""

    def test_copy_creates_new_bag(self, bag_class_camel):
        """copy() should return a different Bag with same content."""
        b = _make_flat_bag(bag_class_camel)
        c = b.copy()
        assert c == b
        assert c is not b

    def test_copy_shallow_independence(self):
        """Modifying the copy should not affect the original (for leaf values).

        Original's copy.copy() shares _nodes list, so this only tests
        the wrapper which uses manual iteration for true independence.
        """
        b = _make_flat_bag(WrapperBag)
        c = b.copy()
        c["name"] = "Bob"
        assert b["name"] == "Alice"

    def test_copy_preserves_attributes(self, bag_class_camel):
        """copy() should preserve node attributes."""
        b = bag_class_camel()
        b.setItem("x", 1, color="red")
        c = b.copy()
        assert c.getAttr("x", "color") == "red"


class TestDeepCopy:
    """Test deepcopy() on all 3 implementations."""

    def test_deepcopy_independence(self, bag_class):
        """Modifying nested Bag in deepcopy should not affect original."""
        b = _make_nested_bag(bag_class)
        c = b.deepcopy()
        c["a"]["x"] = 999
        assert b["a"]["x"] == 1

    def test_deepcopy_equality(self, bag_class):
        """Deepcopy should be equal to original."""
        b = _make_nested_bag(bag_class)
        c = b.deepcopy()
        assert c == b


class TestDiff:
    """Test diff() comparison (original + wrapper)."""

    def test_diff_equal_bags(self, bag_class_camel):
        """diff() of equal bags should return None."""
        b1 = _make_flat_bag(bag_class_camel)
        b2 = _make_flat_bag(bag_class_camel)
        assert b1.diff(b2) is None

    def test_diff_different_values(self, bag_class_camel):
        """diff() of bags with different values should return a description."""
        b1 = _make_flat_bag(bag_class_camel)
        b2 = _make_flat_bag(bag_class_camel)
        b2["name"] = "Bob"
        result = b1.diff(b2)
        assert result is not None
        assert "name" in result

    def test_diff_different_length(self, bag_class_camel):
        """diff() of bags with different lengths should note 'Different length'."""
        b1 = _make_flat_bag(bag_class_camel)
        b2 = bag_class_camel()
        b2["x"] = 1
        result = b1.diff(b2)
        assert "Different length" in result

    def test_diff_nested_bags(self, bag_class_camel):
        """diff() should recurse into nested Bag values."""
        b1 = _make_nested_bag(bag_class_camel)
        b2 = _make_nested_bag(bag_class_camel)
        b2["a"]["x"] = 999
        result = b1.diff(b2)
        assert result is not None
        assert "value:" in result


class TestMerge:
    """Test merge() with various flag combinations (original + wrapper)."""

    def test_merge_basic(self, bag_class_camel):
        """Basic merge: combine two bags, all flags True."""
        b1 = bag_class_camel()
        b1["a"] = 1
        b1["b"] = 2
        b2 = bag_class_camel()
        b2["b"] = 20
        b2["c"] = 30
        result = b1.merge(b2)
        assert result["a"] == 1
        assert result["b"] == 20  # updated from b2
        assert result["c"] == 30  # added from b2

    def test_merge_no_update_values(self, bag_class_camel):
        """upd_values=False: existing values should not be overwritten."""
        b1 = bag_class_camel()
        b1["a"] = 1
        b2 = bag_class_camel()
        b2["a"] = 999
        result = b1.merge(b2, upd_values=False)
        assert result["a"] == 1

    def test_merge_no_add_values(self, bag_class_camel):
        """add_values=False: new keys from other should not be added."""
        b1 = bag_class_camel()
        b1["a"] = 1
        b2 = bag_class_camel()
        b2["b"] = 2
        result = b1.merge(b2, add_values=False)
        assert "a" in result
        assert "b" not in result

    def test_merge_returns_new_bag(self, bag_class_camel):
        """merge() should return a new Bag, not modify originals."""
        b1 = _make_flat_bag(bag_class_camel)
        b2 = bag_class_camel()
        b2["extra"] = "value"
        result = b1.merge(b2)
        assert "extra" in result
        assert "extra" not in b1

    def test_merge_recursive(self, bag_class_camel):
        """merge() should recursively merge nested Bags."""
        b1 = bag_class_camel()
        inner1 = bag_class_camel()
        inner1["x"] = 1
        b1["sub"] = inner1

        b2 = bag_class_camel()
        inner2 = bag_class_camel()
        inner2["x"] = 10
        inner2["y"] = 20
        b2["sub"] = inner2

        result = b1.merge(b2)
        assert result["sub"]["x"] == 10
        assert result["sub"]["y"] == 20

    def test_merge_attr_flags(self, bag_class_camel):
        """Test attribute merge flags: upd_attr=True, add_attr=False."""
        b1 = bag_class_camel()
        b1.setItem("a", 1, color="red")
        b2 = bag_class_camel()
        b2.setItem("a", 1, color="blue", size="large")
        result = b1.merge(b2, upd_attr=True, add_attr=False)
        assert result.getAttr("a", "color") == "blue"  # updated
        assert result.getAttr("a", "size") is None  # not added


class TestRowChild:
    """Test rowchild() auto-numbering (original + wrapper)."""

    def test_rowchild_auto_numbering(self, bag_class_camel):
        """rowchild() should create zero-padded numbered children."""
        b = bag_class_camel()
        b.rowchild(label="First")
        b.rowchild(label="Second")
        b.rowchild(label="Third")
        keys = b.keys()
        assert keys[0] == "R_00000000"
        assert keys[1] == "R_00000001"
        assert keys[2] == "R_00000002"

    def test_rowchild_pkey(self, bag_class_camel):
        """rowchild() should set _pkey attribute."""
        b = bag_class_camel()
        b.rowchild(_pkey="my_key", label="Test")
        assert b.getAttr("R_00000000", "_pkey") == "my_key"

    def test_rowchild_kwargs_as_attrs(self, bag_class_camel):
        """Extra kwargs should become node attributes."""
        b = bag_class_camel()
        b.rowchild(label="Row1", action="doSomething")
        assert b.getAttr("R_00000000", "label") == "Row1"
        assert b.getAttr("R_00000000", "action") == "doSomething"

    def test_rowchild_custom_pattern(self, bag_class_camel):
        """Custom childname pattern should work."""
        b = bag_class_camel()
        b.rowchild(childname="item_#", label="A")
        b.rowchild(childname="item_#", label="B")
        keys = b.keys()
        assert keys[0] == "item_00000000"
        assert keys[1] == "item_00000001"


class TestChild:
    """Test child() structure creation (original + wrapper)."""

    def test_child_creates_bag(self, bag_class_camel):
        """child() should create an empty Bag and return it."""
        b = bag_class_camel()
        result = b.child("div")
        assert isinstance(result, genro_bag.Bag) or hasattr(result, "_htraverse")
        assert len(b) == 1

    def test_child_tag_replacement(self, bag_class_camel):
        """'*' in childname should be replaced with tag."""
        b = bag_class_camel()
        b.child("div", childname="*_header")
        assert "div_header" in b

    def test_child_counter_replacement(self, bag_class_camel):
        """'#' in childname should be replaced with sequential counter."""
        b = bag_class_camel()
        b.child("li", childname="item_#")
        b.child("li", childname="item_#")
        b.child("li", childname="item_#")
        assert "item_0" in b
        assert "item_1" in b
        assert "item_2" in b

    def test_child_star_and_hash(self, bag_class_camel):
        """Default childname '*_#' replaces both * and #."""
        b = bag_class_camel()
        b.child("div")
        b.child("div")
        assert "div_0" in b
        assert "div_1" in b

    def test_child_returns_bag_for_nesting(self, bag_class_camel):
        """The returned Bag can be used for nested structure building."""
        root = bag_class_camel()
        header = root.child("div", childname="header")
        header.child("h1", childname="title")
        assert "title" in header
        assert "header" in root

    def test_child_existing_same_tag_reuse(self, bag_class_camel):
        """If child exists with same tag, update attrs and return existing.

        Note: original updates attrs on result.attributes (child Bag's parentNode),
        NOT on the parent's node attributes. The wrapper updates via
        where.setAttr(childname, ...) which updates the parent node's attrs.
        Both approaches return the existing child Bag.
        """
        b = bag_class_camel()
        b.child("div", childname="header", color="red")
        result = b.child("div", childname="header", color="blue")
        assert result is not None
        if _impl_name(bag_class_camel) == "original":
            # original updates attrs on child.parentNode, not parent node
            assert b.getAttr("header", "color") == "red"  # unchanged on parent
        else:
            assert b.getAttr("header", "color") == "blue"

    def test_child_existing_different_tag_raises(self, bag_class_camel):
        """If child exists with different tag, raise BagException."""
        b = bag_class_camel()
        b.child("div", childname="header")
        with pytest.raises(Exception):
            b.child("span", childname="header")

    def test_child_dotted_path(self, bag_class_camel):
        """Dotted childname should create intermediate Bags."""
        b = bag_class_camel()
        b.child("input", childname="form.fields.name_field")
        assert "form" in b
        assert "fields" in b["form"]
        assert "name_field" in b["form"]["fields"]

    def test_child_tag_attribute(self, bag_class_camel):
        """child() should set tag= attribute on the created node."""
        b = bag_class_camel()
        b.child("div", childname="header", _class="main")
        assert b.getAttr("header", "tag") == "div"
        assert b.getAttr("header", "_class") == "main"


# ===========================================================================
# AREA G: RESOLVERS
# ===========================================================================


class TestResolverCamel:
    """Test resolver aliases via camelCase API (original + wrapper)."""

    def test_set_callback_item(self, bag_class_camel):
        """setCallBackItem should set a resolver that computes on access."""
        b = bag_class_camel()
        b.setCallBackItem("greeting", lambda x="hello": x)
        result = b["greeting"]
        assert result == "hello"

    def test_set_resolver(self):
        """setResolver should attach a resolver to a path.

        Only tested on wrapper — original's setResolver does not attach
        the resolver correctly.
        """
        b = WrapperBag()
        resolver = NewBagCbResolver(lambda x="world": x)
        b.setResolver("test", resolver)
        assert b["test"] == "world"

    def test_get_resolver(self):
        """getResolver should return the resolver attached to a node.

        Only tested on wrapper — original's getResolver calls
        node.getResolver() which does not exist on original BagNode.
        """
        b = WrapperBag()
        b.setCallBackItem("calc", lambda x="val": x)
        resolver = b.getResolver("calc")
        assert resolver is not None

    def test_get_resolver_none(self):
        """getResolver on a node without resolver should return None."""
        b = WrapperBag()
        b["plain"] = 42
        resolver = b.getResolver("plain")
        assert resolver is None


class TestResolverSnake:
    """Test BagCbResolver via snake_case API (new + wrapper)."""

    def test_cb_resolver_via_set_item(self, bag_class_snake):
        """Setting a BagCbResolver as value should work via set_item."""
        b = bag_class_snake()
        resolver = NewBagCbResolver(lambda x="test": x)
        b.set_item("calc", resolver)
        assert b["calc"] == "test"

    def test_resolver_property(self, bag_class_snake):
        """Node.resolver property should return the attached resolver."""
        b = bag_class_snake()
        resolver = NewBagCbResolver(lambda x="val": x)
        b.set_item("calc", resolver)
        node = b.get_node("calc")
        assert node.resolver is not None


class TestFormulaStubs:
    """Test deprecated formula/defineSymbol/defineFormula on wrapper only."""

    def test_formula_warns(self):
        """formula() should emit DeprecationWarning."""
        b = WrapperBag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = b.formula("test_formula")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert result is None

    def test_define_symbol_warns(self):
        """defineSymbol() should emit DeprecationWarning."""
        b = WrapperBag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.defineSymbol(x="path.to.x")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_define_formula_warns(self):
        """defineFormula() should emit DeprecationWarning."""
        b = WrapperBag()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.defineFormula(calc="$x + $y")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
