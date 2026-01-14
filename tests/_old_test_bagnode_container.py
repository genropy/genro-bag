# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for NodeContainer specification."""


from genro_bag import NodeContainer


class TestNodeContainerBasic:
    """Test basic NodeContainer creation and access."""

    def test_create_empty(self):
        """Create an empty NodeContainer."""
        d = NodeContainer()
        assert len(d) == 0

    def test_create_from_dict(self):
        """Create NodeContainer from a dict."""
        d = NodeContainer({"a": 1, "b": 2})
        assert d["a"] == 1
        assert d["b"] == 2


class TestAccessSyntax:
    """Test the three access syntaxes: label, numeric index, '#n' string."""

    def test_access_by_label(self):
        """Access by label string."""
        d = NodeContainer()
        d["foo"] = 1
        d["bar"] = 2
        d["baz"] = 3

        assert d["foo"] == 1
        assert d["bar"] == 2
        assert d["baz"] == 3

    def test_access_by_numeric_index(self):
        """Access by numeric index."""
        d = NodeContainer()
        d["foo"] = 1
        d["bar"] = 2
        d["baz"] = 3

        assert d[0] == 1
        assert d[1] == 2
        assert d[2] == 3

    def test_access_by_hash_index(self):
        """Access by '#n' string index."""
        d = NodeContainer()
        d["foo"] = 1
        d["bar"] = 2
        d["baz"] = 3

        assert d["#0"] == 1
        assert d["#1"] == 2
        assert d["#2"] == 3

    def test_all_syntaxes_equivalent(self):
        """All three syntaxes return the same value."""
        d = NodeContainer()
        d["foo"] = 1
        d["bar"] = 2
        d["baz"] = 3

        # Access second element with all syntaxes
        assert d["bar"] == d[1] == d["#1"] == 2


class TestMissingKeys:
    """Test behavior for missing keys/indices - never raises, returns None."""

    def test_missing_label_returns_none(self):
        """Missing label returns None."""
        d = NodeContainer()
        d["foo"] = 1

        assert d["missing"] is None

    def test_out_of_range_index_returns_none(self):
        """Out of range numeric index returns None."""
        d = NodeContainer()
        d["foo"] = 1

        assert d[99] is None

    def test_out_of_range_hash_index_returns_none(self):
        """Out of range '#n' index returns None."""
        d = NodeContainer()
        d["foo"] = 1

        assert d["#99"] is None


class TestContains:
    """Test __contains__ for checking existence."""

    def test_contains_existing_label(self):
        """Label exists."""
        d = NodeContainer()
        d["foo"] = 1

        assert "foo" in d

    def test_contains_missing_label(self):
        """Label does not exist."""
        d = NodeContainer()
        d["foo"] = 1

        assert "missing" not in d


class TestLen:
    """Test __len__ method."""

    def test_len_empty(self):
        """Length of empty NodeContainer is 0."""
        d = NodeContainer()
        assert len(d) == 0

    def test_len_with_elements(self):
        """Length reflects number of elements."""
        d = NodeContainer()
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3

        assert len(d) == 3
