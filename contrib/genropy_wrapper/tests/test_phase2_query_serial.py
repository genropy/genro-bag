"""Phase 2 comparative tests: Query & Serialization.

Tests cover Areas C (query/traversal) and D (serialization) across all three
implementations: original (gnr.core.gnrbag), new (genro_bag), and wrapper
(replacement.gnrbag).

Fixture usage:
    - bag_class: all 3 implementations (original, new, wrapper)
    - bag_class_camel: original + wrapper (camelCase API)
    - bag_class_snake: new + wrapper (snake_case API)
"""

import json
import pickle


# ============================================================
# Helpers
# ============================================================


def _make_nested_bag(cls):
    """Create a nested Bag for testing: a.x=1, a.y=2, b.z=3, c=4."""
    bag = cls()
    a = cls()
    a["x"] = 1
    a["y"] = 2
    b = cls()
    b["z"] = 3
    bag["a"] = a
    bag["b"] = b
    bag["c"] = 4
    return bag


def _make_flat_bag(cls):
    """Create a flat Bag: name=Alice, age=30, city=Rome."""
    bag = cls()
    bag["name"] = "Alice"
    bag["age"] = 30
    bag["city"] = "Rome"
    return bag


# ============================================================
# Area C: Query & Traversal
# ============================================================


class TestDigest:
    """Test digest/query on all 3 implementations.

    digest('#k') should return labels; digest('#k,#v') should return
    (label, value) tuples. These work identically across all implementations.
    """

    def test_digest_keys(self, bag_class):
        """digest('#k') returns list of labels."""
        bag = _make_flat_bag(bag_class)
        result = bag.digest("#k")
        assert result == ["name", "age", "city"]

    def test_digest_keys_values(self, bag_class):
        """digest('#k,#v') returns list of (label, value) tuples."""
        bag = _make_flat_bag(bag_class)
        result = bag.digest("#k,#v")
        assert result == [("name", "Alice"), ("age", 30), ("city", "Rome")]

    def test_digest_values_only(self, bag_class):
        """digest('#v') returns list of values."""
        bag = _make_flat_bag(bag_class)
        result = bag.digest("#v")
        assert result == ["Alice", 30, "Rome"]

    def test_digest_with_condition(self, bag_class):
        """digest with condition filters nodes."""
        bag = _make_flat_bag(bag_class)
        result = bag.digest("#k,#v", condition=lambda n: isinstance(n.value, int))
        assert result == [("age", 30)]

    def test_digest_empty_bag(self, bag_class):
        """digest on empty Bag returns empty list."""
        bag = bag_class()
        result = bag.digest("#k,#v")
        assert result == []


class TestDigestCamel:
    """Test digest camelCase-specific features: asColumns parameter."""

    def test_digest_as_columns(self, bag_class_camel):
        """digest with asColumns=True transposes results into column lists."""
        bag = _make_flat_bag(bag_class_camel)
        result = bag.digest("#k,#v", asColumns=True)
        assert result == [["name", "age", "city"], ["Alice", 30, "Rome"]]

    def test_digest_as_columns_empty(self, bag_class_camel):
        """digest asColumns on empty Bag returns empty column lists."""
        bag = bag_class_camel()
        result = bag.digest("#k,#v", asColumns=True)
        assert result == [[], []]

    def test_digest_as_columns_single(self, bag_class_camel):
        """digest asColumns with single selector returns list of one list."""
        bag = _make_flat_bag(bag_class_camel)
        result = bag.digest("#k", asColumns=True)
        assert result == [["name", "age", "city"]]


class TestDigestSnake:
    """Test query() snake_case features: deep, iter, limit."""

    def test_query_deep(self, bag_class_snake):
        """query with deep=True traverses nested Bags."""
        bag = _make_nested_bag(bag_class_snake)
        result = bag.query("#k,#v", deep=True, branch=False)
        labels = [r[0] for r in result]
        assert "x" in labels
        assert "y" in labels
        assert "z" in labels
        assert "c" in labels

    def test_query_iter(self, bag_class_snake):
        """query with iter=True returns a generator."""
        bag = _make_flat_bag(bag_class_snake)
        result = bag.query("#k", iter=True)
        assert hasattr(result, "__next__")
        assert list(result) == ["name", "age", "city"]

    def test_query_limit(self, bag_class_snake):
        """query with limit restricts number of results."""
        bag = _make_flat_bag(bag_class_snake)
        result = bag.query("#k", limit=2)
        assert len(result) == 2
        assert result == ["name", "age"]

    def test_query_leaf_only(self, bag_class_snake):
        """query with branch=False excludes Bag-valued nodes."""
        bag = _make_nested_bag(bag_class_snake)
        result = bag.query("#k", branch=False)
        assert result == ["c"]

    def test_query_branch_only(self, bag_class_snake):
        """query with leaf=False excludes non-Bag-valued nodes."""
        bag = _make_nested_bag(bag_class_snake)
        result = bag.query("#k", leaf=False)
        assert result == ["a", "b"]


class TestWalkCallback:
    """Test walk with callback on all 3 implementations.

    walk(callback) calls callback(node, **kw) for each node depth-first.
    If callback returns truthy, walk stops early and returns that value.
    """

    def test_walk_visits_all(self, bag_class):
        """walk visits all nodes in order (flat Bag)."""
        bag = _make_flat_bag(bag_class)
        visited = []
        bag.walk(lambda n, **kw: visited.append(n.label) or None)
        assert visited == ["name", "age", "city"]

    def test_walk_nested(self, bag_class):
        """walk traverses nested Bags depth-first."""
        bag = _make_nested_bag(bag_class)
        visited = []
        bag.walk(lambda n, **kw: visited.append(n.label) or None)
        # Depth-first: a, x, y, b, z, c
        assert visited == ["a", "x", "y", "b", "z", "c"]

    def test_walk_early_exit(self, bag_class):
        """walk stops if callback returns truthy value."""
        bag = _make_flat_bag(bag_class)
        result = bag.walk(lambda n, **kw: n.label if n.label == "age" else None)
        assert result == "age"


class TestWalkGenerator:
    """Test walk generator mode (snake_case API: new + wrapper)."""

    def test_walk_generator(self, bag_class_snake):
        """walk() with no callback returns generator of (path, node) tuples."""
        bag = _make_nested_bag(bag_class_snake)
        result = list(bag.walk())
        paths = [p for p, _n in result]
        assert "a" in paths
        assert "a.x" in paths
        assert "a.y" in paths
        assert "b" in paths
        assert "b.z" in paths
        assert "c" in paths

    def test_walk_generator_values(self, bag_class_snake):
        """walk generator yields correct node values."""
        bag = _make_flat_bag(bag_class_snake)
        result = {p: n.value for p, n in bag.walk()}
        assert result == {"name": "Alice", "age": 30, "city": "Rome"}


class TestTraverse:
    """Test traverse() on original + wrapper (camelCase API).

    traverse() yields BagNode objects (not tuples), depth-first.
    """

    def test_traverse_yields_nodes(self, bag_class_camel):
        """traverse yields BagNode objects."""
        bag = _make_nested_bag(bag_class_camel)
        nodes = list(bag.traverse())
        labels = [n.label for n in nodes]
        assert labels == ["a", "x", "y", "b", "z", "c"]

    def test_traverse_leaf_values(self, bag_class_camel):
        """traverse yields nodes with correct values for leaves."""
        bag = _make_flat_bag(bag_class_camel)
        result = {n.label: n.value for n in bag.traverse()}
        assert result == {"name": "Alice", "age": 30, "city": "Rome"}


class TestFilter:
    """Test filter() on original + wrapper (camelCase API).

    filter(cb) returns a new Bag containing only nodes where cb(node) is truthy.
    Recursively filters nested Bags; empty sub-Bags are excluded.
    """

    def test_filter_simple(self, bag_class_camel):
        """filter returns Bag with matching nodes only."""
        bag = _make_flat_bag(bag_class_camel)
        result = bag.filter(lambda n: isinstance(n.value, str))
        assert list(result.keys()) == ["name", "city"]
        assert result["name"] == "Alice"

    def test_filter_nested(self, bag_class_camel):
        """filter on nested Bag excludes empty sub-Bags."""
        bag = _make_nested_bag(bag_class_camel)
        # Keep only nodes with value > 2 (leaves only)
        result = bag.filter(lambda n: isinstance(n.value, int) and n.value > 2)
        # 'a' sub-Bag has no matching leaves (x=1,y=2), so excluded
        # 'b' sub-Bag has z=3, so included
        # 'c'=4 is a direct match
        assert "a" not in result
        assert "b" in result
        assert result["b.z"] == 3
        assert result["c"] == 4

    def test_filter_no_match(self, bag_class_camel):
        """filter with no matches returns empty Bag."""
        bag = _make_flat_bag(bag_class_camel)
        result = bag.filter(lambda n: False)
        assert len(result) == 0


class TestGetLeaves:
    """Test getLeaves() on original + wrapper.

    getLeaves() returns [(path_string, value)] for all leaf nodes.
    """

    def test_get_leaves_nested(self, bag_class_camel):
        """getLeaves on nested Bag returns only leaf paths and values."""
        bag = _make_nested_bag(bag_class_camel)
        leaves = bag.getLeaves()
        leaf_dict = dict(leaves)
        assert leaf_dict["a.x"] == 1
        assert leaf_dict["a.y"] == 2
        assert leaf_dict["b.z"] == 3
        assert leaf_dict["c"] == 4
        assert len(leaves) == 4

    def test_get_leaves_flat(self, bag_class_camel):
        """getLeaves on flat Bag returns all items."""
        bag = _make_flat_bag(bag_class_camel)
        leaves = bag.getLeaves()
        assert len(leaves) == 3


class TestGetIndex:
    """Test getIndex() and getIndexList() on original + wrapper."""

    def test_get_index(self, bag_class_camel):
        """getIndex returns (path_list, node) for all nodes."""
        bag = _make_nested_bag(bag_class_camel)
        index = bag.getIndex()
        # Should include both branches and leaves
        path_lists = [p for p, _n in index]
        assert ["a"] in path_lists
        assert ["a", "x"] in path_lists
        assert ["b", "z"] in path_lists
        assert ["c"] in path_lists

    def test_get_index_list(self, bag_class_camel):
        """getIndexList returns list of dot-separated path strings."""
        bag = _make_nested_bag(bag_class_camel)
        paths = bag.getIndexList()
        assert "a" in paths
        assert "a.x" in paths
        assert "c" in paths

    def test_get_index_list_as_text(self, bag_class_camel):
        """getIndexList(asText=True) returns newline-joined string."""
        bag = _make_nested_bag(bag_class_camel)
        text = bag.getIndexList(asText=True)
        assert isinstance(text, str)
        assert "\n" in text
        assert "a.x" in text


class TestNodesByAttr:
    """Test nodesByAttr() on original + wrapper.

    nodesByAttr finds ALL nodes with a matching attribute, recursively.
    """

    def test_nodes_by_attr_exists(self, bag_class_camel):
        """nodesByAttr finds nodes that have a specific attribute."""
        bag = bag_class_camel()
        bag.setItem("a", 1, color="red")
        bag.setItem("b", 2, color="blue")
        bag.setItem("c", 3)
        result = bag.nodesByAttr("color")
        assert len(result) == 2
        labels = {n.label for n in result}
        assert labels == {"a", "b"}

    def test_nodes_by_attr_value(self, bag_class_camel):
        """nodesByAttr with value kwarg matches exact attribute value."""
        bag = bag_class_camel()
        bag.setItem("a", 1, color="red")
        bag.setItem("b", 2, color="blue")
        bag.setItem("c", 3, color="red")
        result = bag.nodesByAttr("color", value="red")
        assert len(result) == 2
        labels = {n.label for n in result}
        assert labels == {"a", "c"}

    def test_nodes_by_attr_nested(self, bag_class_camel):
        """nodesByAttr searches nested Bags recursively."""
        bag = bag_class_camel()
        child = bag_class_camel()
        child.setItem("x", 10, tag="important")
        child.setItem("y", 20)
        bag.setItem("child", child)
        bag.setItem("top", 99, tag="important")
        result = bag.nodesByAttr("tag", value="important")
        assert len(result) == 2


# ============================================================
# Area D: Serialization
# ============================================================


class TestXmlRoundtrip:
    """Test XML roundtrip on new + wrapper via snake_case API.

    to_xml() produces fragment XML (no root); we wrap in <root> for parsing.
    Original is excluded because it has no to_xml/from_xml snake_case API.
    Note: values become strings (no type info in plain to_xml).
    """

    def test_xml_roundtrip_flat(self, bag_class_snake):
        """XML roundtrip preserves flat Bag structure."""
        bag = _make_flat_bag(bag_class_snake)
        xml = f"<root>{bag.to_xml()}</root>"
        restored = bag_class_snake.from_xml(xml)
        inner = restored["root"] if "root" in restored else restored
        assert "name" in inner
        assert inner["name"] == "Alice"

    def test_xml_roundtrip_nested(self, bag_class_snake):
        """XML roundtrip preserves nested Bag structure."""
        bag = _make_nested_bag(bag_class_snake)
        xml = f"<root>{bag.to_xml()}</root>"
        restored = bag_class_snake.from_xml(xml)
        inner = restored["root"] if "root" in restored else restored
        assert "a" in inner
        assert "b" in inner


class TestXmlRoundtripCamel:
    """Test toXml/fromXml on original + wrapper with _T type annotations.

    The wrapper's toXml produces _T attributes for typed values, enabling
    type-preserving roundtrip when parsed by from_xml which decodes _T.
    """

    def test_toxml_has_type_annotations(self, bag_class_camel):
        """toXml output includes _T attributes for typed values."""
        bag = bag_class_camel()
        bag.setItem("count", 42)
        bag.setItem("name", "test")
        xml = bag.toXml()
        # Integer should have _T="L"
        assert '_T="L"' in xml
        # String should NOT have _T (or _T="T")
        assert "test" in xml

    def test_toxml_fromxml_roundtrip(self, bag_class_camel):
        """toXml -> fromXml roundtrip preserves types via _T annotations."""
        bag = bag_class_camel()
        bag.setItem("count", 42)
        bag.setItem("ratio", 3.14)
        bag.setItem("name", "test")
        bag.setItem("flag", True)

        xml = bag.toXml()
        restored = bag_class_camel()
        restored.fromXml(xml)

        assert restored["count"] == 42
        assert isinstance(restored["count"], int)
        assert restored["name"] == "test"

    def test_toxml_genrobag_root(self, bag_class_camel):
        """toXml wraps content in <GenRoBag> by default."""
        bag = bag_class_camel()
        bag.setItem("a", 1)
        xml = bag.toXml()
        assert "<GenRoBag>" in xml
        assert "</GenRoBag>" in xml

    def test_toxml_omit_root(self, bag_class_camel):
        """toXml with omitRoot=True does not wrap in <GenRoBag>."""
        bag = bag_class_camel()
        bag.setItem("a", 1)
        xml = bag.toXml(omitRoot=True)
        assert "<GenRoBag>" not in xml

    def test_toxml_nested(self, bag_class_camel):
        """toXml handles nested Bags correctly."""
        bag = _make_nested_bag(bag_class_camel)
        xml = bag.toXml()
        restored = bag_class_camel()
        restored.fromXml(xml)
        # Nested structure preserved
        assert "a" in restored
        assert restored["a.x"] is not None


class TestJsonRoundtrip:
    """Test JSON roundtrip on new + wrapper via snake_case API.

    Original is excluded because it has no to_json/from_json snake_case API.
    """

    def test_json_roundtrip_flat(self, bag_class_snake):
        """JSON roundtrip preserves flat Bag structure and types."""
        bag = _make_flat_bag(bag_class_snake)
        json_str = bag.to_json()
        restored = bag_class_snake.from_json(json_str)
        assert restored["name"] == "Alice"
        assert restored["age"] == 30
        assert restored["city"] == "Rome"

    def test_json_roundtrip_nested(self, bag_class_snake):
        """JSON roundtrip preserves nested Bag structure."""
        bag = _make_nested_bag(bag_class_snake)
        json_str = bag.to_json()
        restored = bag_class_snake.from_json(json_str)
        assert restored["a.x"] == 1
        assert restored["b.z"] == 3
        assert restored["c"] == 4


class TestJsonRoundtripCamel:
    """Test toJson/fromJson on original + wrapper.

    NOTE: The original's fromJson expects parsed data (dict/list), not strings.
    The caller must call json.loads() first. The wrapper handles both.
    Tests use json.loads() for compatibility with both implementations.
    """

    def test_tojson_fromjson(self, bag_class_camel):
        """toJson -> json.loads -> fromJson roundtrip preserves data."""
        bag = _make_flat_bag(bag_class_camel)
        json_str = bag.toJson()
        restored = bag_class_camel()
        restored.fromJson(json.loads(json_str))
        assert restored["name"] == "Alice"
        assert restored["age"] == 30

    def test_tojson_typed(self, bag_class_camel):
        """toJson -> json.loads -> fromJson roundtrip preserves types."""
        bag = bag_class_camel()
        bag.setItem("count", 42)
        bag.setItem("name", "test")
        json_str = bag.toJson(typed=True)
        restored = bag_class_camel()
        restored.fromJson(json.loads(json_str))
        assert restored["count"] == 42
        assert isinstance(restored["count"], int)


class TestPickle:
    """Test standard pickle roundtrip on all 3 implementations.

    Uses Python's pickle.dumps/loads directly (not the camelCase method).
    """

    def test_pickle_roundtrip_flat(self, bag_class):
        """pickle roundtrip preserves flat Bag structure and types."""
        bag = _make_flat_bag(bag_class)
        data = pickle.dumps(bag)
        restored = pickle.loads(data)
        assert restored["name"] == "Alice"
        assert restored["age"] == 30
        assert isinstance(restored["age"], int)

    def test_pickle_roundtrip_nested(self, bag_class):
        """pickle roundtrip preserves nested Bag structure."""
        bag = _make_nested_bag(bag_class)
        data = pickle.dumps(bag)
        restored = pickle.loads(data)
        assert restored["a.x"] == 1
        assert restored["b.z"] == 3
        assert restored["c"] == 4


class TestPickleCamel:
    """Test pickle() camelCase method on original + wrapper.

    Bag.pickle(destination) is used in Genropy application code
    (archive, startup data, lazyBag). Bag.unpickle() is never used
    in application code (Bag(filepath) constructor is used instead),
    so it is not tested or wrapped.
    """

    def test_pickle_returns_bytes(self, bag_class_camel):
        """pickle() with no destination returns bytes."""
        bag = _make_flat_bag(bag_class_camel)
        data = bag.pickle()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_pickle_to_file(self, bag_class_camel, tmp_path):
        """pickle(destination) writes to file successfully."""
        bag = _make_flat_bag(bag_class_camel)
        filepath = str(tmp_path / "test.pkl")
        bag.pickle(destination=filepath)
        # Verify by loading with stdlib pickle
        with open(filepath, "rb") as f:
            restored = pickle.load(f)
        assert restored["name"] == "Alice"
        assert restored["age"] == 30


class TestToTree:
    """Test toTree() on original + wrapper.

    toTree transforms a flat Bag of records into a hierarchical grouping.
    """

    def test_to_tree_basic(self, bag_class_camel):
        """toTree groups items by specified field."""
        bag = bag_class_camel()
        # Create flat records
        r1 = bag_class_camel()
        r1.setItem("dept", "eng")
        r1.setItem("name", "Alice")
        bag.setItem("r1", r1)

        r2 = bag_class_camel()
        r2.setItem("dept", "eng")
        r2.setItem("name", "Bob")
        bag.setItem("r2", r2)

        r3 = bag_class_camel()
        r3.setItem("dept", "sales")
        r3.setItem("name", "Carol")
        bag.setItem("r3", r3)

        tree = bag.toTree("dept")
        # Should have two groups: eng and sales
        assert "eng" in tree
        assert "sales" in tree
