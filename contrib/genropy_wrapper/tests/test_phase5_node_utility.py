"""Phase 5 tests: BagNode details, utilities, and semantic differences.

Tests cover:
- BagNode.getFormattedValue (display formatting with caption)
- Bag.getFormattedValue (join node formatted values)
- asDict / asDictDeeply (dict conversion)
- asString (encoded string representation)
- __pow__ (parent attribute update shorthand)
- getNodeByAttr / getNodeByValue (node lookup)
- getDeepestNode (partial path traversal)
- update (full original signature with resolved, ignoreNone, preservePattern)
- summarizeAttributes (recursive attribute aggregation)
- Validator stubs (deprecation warnings)
- __call__ (keys or value shorthand)
- deepcopy (deep recursive copy)
- sort / sum (aggregation methods on all 3 implementations)

Each test uses conftest fixtures:
- bag_class_camel: original + wrapper (camelCase API)
- bag_class: original + new + wrapper (common API)
"""

import re
import warnings

import pytest

from replacement.gnrbag import Bag as WrapperBag

# ============================================================================
# BagNode.getFormattedValue
# ============================================================================


class TestBagNodeGetFormattedValue:
    """Test BagNode.getFormattedValue on original and wrapper."""

    def test_basic_scalar(self, bag_class_camel):
        """getFormattedValue returns 'Label: value' for simple scalar nodes."""
        b = bag_class_camel()
        b.setItem("name", "Alice")
        node = b.getNode("name")
        result = node.getFormattedValue()
        assert result == "Name: Alice"

    def test_formatted_value_attr_overrides(self, bag_class_camel):
        """_formattedValue attribute overrides the raw value in display."""
        b = bag_class_camel()
        b.setItem("status", "A", _formattedValue="Active")
        node = b.getNode("status")
        result = node.getFormattedValue()
        assert "Active" in result
        assert "A" not in result or "Active" in result

    def test_displayed_value_attr(self, bag_class_camel):
        """_displayedValue attribute used when _formattedValue is absent."""
        b = bag_class_camel()
        b.setItem("code", 42, _displayedValue="forty-two")
        node = b.getNode("code")
        result = node.getFormattedValue()
        assert "forty-two" in result

    def test_valuelabel_attr_caption(self, bag_class_camel):
        """_valuelabel attribute overrides the label as caption."""
        b = bag_class_camel()
        b.setItem("f1", "hello", _valuelabel="Field One")
        node = b.getNode("f1")
        result = node.getFormattedValue()
        assert result.startswith("Field One:")

    def test_name_long_caption(self, bag_class_camel):
        """name_long attribute used as caption when _valuelabel is absent."""
        b = bag_class_camel()
        b.setItem("f2", "world", name_long="Second Field")
        node = b.getNode("f2")
        result = node.getFormattedValue()
        assert result.startswith("Second Field:")

    def test_omit_empty_true(self, bag_class_camel):
        """getFormattedValue returns empty string for None value when omitEmpty=True."""
        b = bag_class_camel()
        b.setItem("empty", None)
        node = b.getNode("empty")
        result = node.getFormattedValue(omitEmpty=True)
        assert result == ""

    def test_omit_empty_false(self, bag_class_camel):
        """getFormattedValue includes None value when omitEmpty=False."""
        b = bag_class_camel()
        b.setItem("empty", None)
        node = b.getNode("empty")
        result = node.getFormattedValue(omitEmpty=False)
        assert "Empty:" in result


# ============================================================================
# Bag.getFormattedValue
# ============================================================================


class TestBagGetFormattedValue:
    """Test Bag-level getFormattedValue on original and wrapper."""

    def test_joins_node_values(self, bag_class_camel):
        """Bag.getFormattedValue joins all node formatted values."""
        b = bag_class_camel()
        b.setItem("name", "Alice")
        b.setItem("age", 30)
        result = b.getFormattedValue()
        assert "Name: Alice" in result
        assert "Age: 30" in result

    def test_skips_underscore_labels(self, bag_class_camel):
        """Nodes with labels starting with '_' are skipped."""
        b = bag_class_camel()
        b.setItem("visible", "yes")
        b.setItem("_hidden", "no")
        result = b.getFormattedValue()
        assert "Visible:" in result
        assert "_hidden" not in result.lower()

    def test_custom_joiner(self, bag_class_camel):
        """Custom joiner string used between formatted values."""
        b = bag_class_camel()
        b.setItem("a", 1)
        b.setItem("b", 2)
        result = b.getFormattedValue(joiner=" | ")
        assert " | " in result


# ============================================================================
# asDict / asDictDeeply
# ============================================================================


class TestAsDict:
    """Test asDict and asDictDeeply on original and wrapper."""

    def test_as_dict_basic(self, bag_class_camel):
        """asDict returns flat dict of first-level key-value pairs."""
        b = bag_class_camel()
        b.setItem("x", 1)
        b.setItem("y", 2)
        d = b.asDict()
        assert d == {"x": 1, "y": 2}

    def test_as_dict_lower(self, bag_class_camel):
        """asDict with lower=True lowercases keys."""
        b = bag_class_camel()
        b.setItem("Name", "Alice")
        d = b.asDict(lower=True)
        assert "name" in d
        assert d["name"] == "Alice"

    def test_as_dict_deeply_recursive(self, bag_class_camel):
        """asDictDeeply recursively converts nested Bags to dicts."""
        b = bag_class_camel()
        inner = bag_class_camel()
        inner.setItem("c", 3)
        b.setItem("a", 1)
        b.setItem("b", inner)
        d = b.asDictDeeply()
        assert d["a"] == 1
        assert isinstance(d["b"], dict)
        assert d["b"]["c"] == 3

    def test_as_dict_deeply_deep_nesting(self, bag_class_camel):
        """asDictDeeply handles multiple levels of nesting."""
        b = bag_class_camel()
        level2 = bag_class_camel()
        level3 = bag_class_camel()
        level3.setItem("deep", "value")
        level2.setItem("mid", level3)
        b.setItem("top", level2)
        d = b.asDictDeeply()
        assert d["top"]["mid"]["deep"] == "value"


# ============================================================================
# asString
# ============================================================================


class TestAsString:
    """Test asString on original and wrapper."""

    def test_returns_bytes(self, bag_class_camel):
        """asString returns bytes, not str."""
        b = bag_class_camel()
        b.setItem("x", 1)
        result = b.asString()
        assert isinstance(result, bytes)

    def test_contains_content(self, bag_class_camel):
        """asString output contains the bag content."""
        b = bag_class_camel()
        b.setItem("hello", "world")
        result = b.asString()
        assert b"hello" in result
        assert b"world" in result


# ============================================================================
# __pow__
# ============================================================================


class TestPow:
    """Test __pow__ attribute update shorthand on original and wrapper."""

    def test_pow_updates_parent_attrs(self, bag_class_camel):
        """bag ** {'key': 'val'} updates parent node attributes."""
        parent = bag_class_camel()
        child = bag_class_camel()
        parent.setItem("child", child)
        parent.setBackRef()
        child ** {"color": "red"}
        assert parent.getAttr("child", "color") == "red"

    def test_pow_no_parent_noop(self, bag_class_camel):
        """__pow__ is a no-op when bag has no parent."""
        b = bag_class_camel()
        b.setItem("x", 1)
        # Should not raise
        b ** {"color": "blue"}


# ============================================================================
# getNodeByAttr / getNodeByValue
# ============================================================================


class TestNodeLookup:
    """Test getNodeByAttr and getNodeByValue on original and wrapper."""

    def test_get_node_by_attr_found(self, bag_class_camel):
        """getNodeByAttr finds node with matching attribute at first level."""
        b = bag_class_camel()
        b.setItem("item1", "val1", myid="abc")
        b.setItem("item2", "val2", myid="def")
        node = b.getNodeByAttr("myid", "def")
        assert node is not None
        assert node.label == "item2"

    def test_get_node_by_attr_not_found(self, bag_class_camel):
        """getNodeByAttr returns None when no match."""
        b = bag_class_camel()
        b.setItem("item1", "val1", myid="abc")
        node = b.getNodeByAttr("myid", "zzz")
        assert node is None

    def test_get_node_by_value(self, bag_class_camel):
        """getNodeByValue finds node by sub-value match."""
        b = bag_class_camel()
        inner1 = bag_class_camel()
        inner1.setItem("name", "Alice")
        inner2 = bag_class_camel()
        inner2.setItem("name", "Bob")
        b.setItem("r1", inner1)
        b.setItem("r2", inner2)
        node = b.getNodeByValue("name", "Bob")
        assert node is not None
        assert node.label == "r2"


# ============================================================================
# getDeepestNode
# ============================================================================


class TestGetDeepestNode:
    """Test getDeepestNode on original and wrapper."""

    def test_full_path_match(self, bag_class_camel):
        """Full path match returns node with empty _tail_list."""
        b = bag_class_camel()
        inner = bag_class_camel()
        inner.setItem("baz", 42)
        b.setItem("foo", inner)
        node = b.getDeepestNode("foo.baz")
        assert node is not None
        assert node.label == "baz"
        assert node._tail_list == []

    def test_partial_path_match(self, bag_class_camel):
        """Partial path match returns deepest node with remaining segments in _tail_list."""
        b = bag_class_camel()
        inner = bag_class_camel()
        inner.setItem("bar", "exists")
        b.setItem("foo", inner)
        node = b.getDeepestNode("foo.bar.baz.qux")
        assert node is not None
        assert node.label == "bar"
        assert node._tail_list == ["baz", "qux"]

    def test_no_match(self, bag_class_camel):
        """No match returns None."""
        b = bag_class_camel()
        b.setItem("x", 1)
        node = b.getDeepestNode("nonexistent.path")
        assert node is None


# ============================================================================
# update (full signature)
# ============================================================================


class TestUpdate:
    """Test update with full original signature on original and wrapper."""

    def test_update_from_dict(self, bag_class_camel):
        """update from dict sets key-value pairs."""
        b = bag_class_camel()
        b.setItem("x", 1)
        b.update({"x": 10, "y": 20})
        assert b["x"] == 10
        assert b["y"] == 20

    def test_update_from_bag(self, bag_class_camel):
        """update from another Bag merges nodes."""
        b1 = bag_class_camel()
        b1.setItem("a", 1)
        b1.setItem("b", 2)
        b2 = bag_class_camel()
        b2.setItem("b", 20)
        b2.setItem("c", 30)
        b1.update(b2)
        assert b1["a"] == 1
        assert b1["b"] == 20
        assert b1["c"] == 30

    def test_update_ignore_none(self, bag_class_camel):
        """update with ignoreNone=True skips None values."""
        b = bag_class_camel()
        b.setItem("x", 1)
        other = bag_class_camel()
        other.setItem("x", None)
        b.update(other, ignoreNone=True)
        assert b["x"] == 1

    def test_update_recursive_bags(self, bag_class_camel):
        """update recursively merges nested Bags."""
        b1 = bag_class_camel()
        inner1 = bag_class_camel()
        inner1.setItem("a", 1)
        inner1.setItem("b", 2)
        b1.setItem("sub", inner1)

        b2 = bag_class_camel()
        inner2 = bag_class_camel()
        inner2.setItem("b", 20)
        inner2.setItem("c", 30)
        b2.setItem("sub", inner2)

        b1.update(b2)
        assert b1["sub.a"] == 1
        assert b1["sub.b"] == 20
        assert b1["sub.c"] == 30

    def test_update_preserve_pattern(self, bag_class_camel):
        """update with preservePattern protects matching values."""
        b = bag_class_camel()
        b.setItem("msg", "KEEP_THIS")
        other = bag_class_camel()
        other.setItem("msg", "new_value")
        pattern = re.compile(r"KEEP")
        b.update(other, preservePattern=pattern)
        assert b["msg"] == "KEEP_THIS"


# ============================================================================
# summarizeAttributes
# ============================================================================


class TestSummarizeAttributes:
    """Test summarizeAttributes on original and wrapper."""

    def test_basic_sum(self, bag_class_camel):
        """summarizeAttributes sums specified attributes across nodes."""
        b = bag_class_camel()
        b.setItem("a", None, qty=10)
        b.setItem("b", None, qty=20)
        result = b.summarizeAttributes(["qty"])
        assert result["qty"] == 30

    def test_recursive_sum(self, bag_class_camel):
        """summarizeAttributes recursively sums through nested Bags."""
        b = bag_class_camel()
        inner = bag_class_camel()
        inner.setItem("c", None, qty=5)
        inner.setItem("d", None, qty=15)
        b.setItem("sub", inner, qty=0)
        b.setItem("top", None, qty=10)
        result = b.summarizeAttributes(["qty"])
        # sub's qty gets updated to 20 (5+15), then total = 20 + 10 = 30
        assert result["qty"] == 30


# ============================================================================
# Validator stubs (wrapper only)
# ============================================================================


class TestValidatorStubs:
    """Test that validator methods emit DeprecationWarning on wrapper."""

    def test_node_add_validator_warning(self):
        """BagNode.addValidator emits DeprecationWarning."""
        b = WrapperBag()
        b.setItem("x", 1)
        node = b.getNode("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            node.addValidator("test", "params")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_node_remove_validator_warning(self):
        """BagNode.removeValidator emits DeprecationWarning."""
        b = WrapperBag()
        b.setItem("x", 1)
        node = b.getNode("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            node.removeValidator("test")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_node_get_validator_data_returns_default(self):
        """BagNode.getValidatorData returns dflt and emits warning."""
        b = WrapperBag()
        b.setItem("x", 1)
        node = b.getNode("x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = node.getValidatorData("test", dflt="fallback")
            assert result == "fallback"
            assert len(w) == 1

    def test_bag_add_validator_warning(self):
        """Bag-level addValidator emits DeprecationWarning."""
        b = WrapperBag()
        b.setItem("x", 1)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            b.addValidator("x", "test", "params")
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)


# ============================================================================
# __call__
# ============================================================================


class TestCall:
    """Test __call__ on all 3 implementations."""

    def test_call_no_args_returns_keys(self, bag_class):
        """bag() returns list of keys."""
        b = bag_class()
        b["x"] = 1
        b["y"] = 2
        result = b()
        assert result == ["x", "y"]

    def test_call_with_path_returns_value(self, bag_class):
        """bag('path') returns value at path."""
        b = bag_class()
        b["x"] = 42
        result = b("x")
        assert result == 42


# ============================================================================
# deepcopy
# ============================================================================


class TestDeepcopy:
    """Test deepcopy on all 3 implementations."""

    def test_deepcopy_independence(self, bag_class):
        """Deep copy is independent of original."""
        b = bag_class()
        inner = bag_class()
        inner["a"] = 1
        b["sub"] = inner
        cp = b.deepcopy()
        cp["sub.a"] = 999
        assert b["sub.a"] == 1

    def test_deepcopy_preserves_structure(self, bag_class):
        """Deep copy preserves all keys and values."""
        b = bag_class()
        b["x"] = 10
        b["y"] = "hello"
        cp = b.deepcopy()
        assert cp["x"] == 10
        assert cp["y"] == "hello"


# ============================================================================
# sort / sum (common API — all 3 implementations)
# ============================================================================


class TestSortSum:
    """Test sort and sum on all 3 implementations."""

    def test_sort_by_key_ascending(self, bag_class):
        """sort('#k:a') sorts nodes by key ascending."""
        b = bag_class()
        b["c"] = 3
        b["a"] = 1
        b["b"] = 2
        b.sort("#k:a")
        assert list(b.keys()) == ["a", "b", "c"]

    def test_sort_by_key_descending(self, bag_class):
        """sort('#k:d') sorts nodes by key descending."""
        b = bag_class()
        b["a"] = 1
        b["c"] = 3
        b["b"] = 2
        b.sort("#k:d")
        assert list(b.keys()) == ["c", "b", "a"]

    def test_sum_values(self, bag_class):
        """sum('#v') sums all node values."""
        b = bag_class()
        b["a"] = 10
        b["b"] = 20
        b["c"] = 30
        result = b.sum("#v")
        assert result == 60
