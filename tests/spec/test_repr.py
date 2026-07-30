"""Spec test: Bag - string representations (__str__, to_string).

Depends on test_basic.py (set_item, get_item, attributes).

Tests verify OBSERVABLE PROPERTIES of string output (contains label, contains
value, indented hierarchy) rather than testing character-by-character format.
The exact format can evolve without breaking tests.

## Scale

1. __str__ on empty Bag            empty string
2. __str__ shows idx, label, value, type
3. __str__ shows attributes
4. __str__ handles nested Bags     nested indented
5. __str__ handles None and bytes
6. to_string on empty Bag          empty string
7. to_string shows label and value in tree format
8. to_string uses tree chars (├──, └──)
9. to_string formats attributes    [key=value]
10. to_string handles nesting      child indentation
"""

from __future__ import annotations

from genro_bag import Bag


# =============================================================================
# __str__
# =============================================================================


class TestStr:
    def test_empty_bag_str_is_empty(self):
        """str(Bag()) is empty string."""
        assert str(Bag()) == ""

    def test_str_contains_label_and_value(self):
        """str shows label and value of each node."""
        bag = Bag()
        bag["name"] = "alice"
        bag["count"] = 42
        out = str(bag)
        assert "name" in out
        assert "alice" in out
        assert "count" in out
        assert "42" in out

    def test_str_shows_index_of_each_node(self):
        """str prefixes each line with node index."""
        bag = Bag({"a": 1, "b": 2})
        out = str(bag)
        # two nodes have indices 0 and 1
        assert "0" in out
        assert "1" in out

    def test_str_shows_type_name(self):
        """str includes type name of value (int, str, ...)."""
        bag = Bag()
        bag["x"] = 42
        bag["y"] = "hello"
        out = str(bag)
        assert "int" in out
        assert "str" in out

    def test_str_shows_attributes(self):
        """str includes node attributes when present."""
        bag = Bag()
        bag.set_item("x", 1, _attributes={"type": "int"})
        out = str(bag)
        assert "type" in out

    def test_str_no_attr_marker_when_empty(self):
        """When node has no attributes, str does not show '<>'."""
        bag = Bag({"a": 1})
        out = str(bag)
        assert "<>" not in out

    def test_str_nested_bag_indented(self):
        """str shows sub-Bags with child labels indented."""
        bag = Bag()
        bag["outer.inner"] = 42
        out = str(bag)
        # both 'outer' and 'inner' appear
        assert "outer" in out
        assert "inner" in out

    def test_str_handles_none_value(self):
        """str shows 'None' for None values."""
        bag = Bag()
        bag["empty"] = None
        out = str(bag)
        assert "None" in out
        assert "empty" in out

    def test_str_handles_bytes_value(self):
        """str decodes bytes to UTF-8 for display."""
        bag = Bag()
        bag["b"] = b"hello"
        out = str(bag)
        assert "hello" in out


# =============================================================================
# to_string - ASCII tree
# =============================================================================


class TestToString:
    def test_empty_bag_returns_empty_string(self):
        """to_string() on empty Bag returns empty string."""
        assert Bag().to_string() == ""

    def test_shows_label_and_value(self):
        """to_string shows label: value for each node."""
        bag = Bag({"name": "alice", "age": 30})
        out = bag.to_string()
        assert "name" in out
        assert "alice" in out
        assert "age" in out
        assert "30" in out

    def test_uses_tree_characters(self):
        """to_string uses tree chars ├── and └── for branches."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        out = bag.to_string()
        # last has └──, others ├──
        assert "├──" in out
        assert "└──" in out

    def test_formats_attributes_in_brackets(self):
        """to_string formats attributes between [ ] after label."""
        bag = Bag()
        bag.set_item("user", "alice", _attributes={"id": 1})
        out = bag.to_string()
        assert "user" in out
        assert "id" in out
        # attributes enclosed in square brackets
        assert "[" in out
        assert "]" in out

    def test_nested_bag_children_are_indented(self):
        """to_string indents children of sub-Bags."""
        bag = Bag()
        bag["outer.inner"] = 42
        out = bag.to_string()
        lines = out.split("\n")
        # line with 'inner' is more indented than line with 'outer'
        outer_line = next(l for l in lines if "outer" in l)
        inner_line = next(l for l in lines if "inner" in l)
        # count leading spaces
        outer_indent = len(outer_line) - len(outer_line.lstrip(" │"))
        inner_indent = len(inner_line) - len(inner_line.lstrip(" │"))
        assert inner_indent > outer_indent

    def test_long_string_value_truncated(self):
        """Long strings (>50) are truncated with '...'."""
        bag = Bag()
        long_value = "x" * 100
        bag["big"] = long_value
        out = bag.to_string()
        assert "..." in out

    def test_none_value_shown_as_none(self):
        """None value appears as 'None'."""
        bag = Bag()
        bag["empty"] = None
        out = bag.to_string()
        assert "None" in out

    def test_bytes_value_decoded(self):
        """bytes decoded for display."""
        bag = Bag()
        bag["b"] = b"hello"
        out = bag.to_string()
        assert "hello" in out
