"""Phase 1: Access & Mutation + Iteration — comparative tests.

Fixture usage:
- bag_class: all 3 (original, new, wrapper) — bracket notation + common APIs only
- bag_class_camel: original + wrapper — camelCase methods (getItem, setItem, etc.)
- bag_class_snake: new + wrapper — snake_case methods (get_item, set_item, etc.)
"""

# ============================================================================
# TestSetGet — bracket notation (all 3)
# ============================================================================


class TestSetGet:
    """Test basic set/get using bracket notation (works on all 3)."""

    def test_simple_set_get(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        assert bag["a"] == 1

    def test_hierarchical_set_get(self, bag_class):
        bag = bag_class()
        bag["a.b.c"] = 42
        assert bag["a.b.c"] == 42

    def test_overwrite_value(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["a"] = 2
        assert bag["a"] == 2

    def test_nested_bag_creation(self, bag_class):
        bag = bag_class()
        bag["a.b.c"] = 1
        intermediate = bag["a"]
        assert hasattr(intermediate, "_htraverse")

    def test_set_multiple_children(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert bag["a"] == 1
        assert bag["b"] == 2
        assert bag["c"] == 3


# ============================================================================
# TestSetGetCamel — getItem/setItem (original + wrapper)
# ============================================================================


class TestSetGetCamel:
    """Test camelCase set/get: getItem, setItem."""

    def test_setItem_getItem(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 10)
        assert bag.getItem("x") == 10

    def test_setItem_hierarchical(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("a.b.c", 42)
        assert bag.getItem("a.b.c") == 42

    def test_getItem_default(self, bag_class_camel):
        bag = bag_class_camel()
        assert bag.getItem("missing", default="fallback") == "fallback"

    def test_setItem_with_attributes(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1, color="red", size=10)
        assert bag.getAttr("x", "color") == "red"
        assert bag.getAttr("x", "size") == 10


# ============================================================================
# TestSetGetSnake — get_item/set_item (new + wrapper)
# ============================================================================


class TestSetGetSnake:
    """Test snake_case set/get: get_item, set_item."""

    def test_set_item_get_item(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 10)
        assert bag.get_item("x") == 10

    def test_get_item_default(self, bag_class_snake):
        bag = bag_class_snake()
        result = bag.get_item("missing", default="fallback")
        assert result == "fallback"

    def test_set_item_returns_node(self, bag_class_snake):
        bag = bag_class_snake()
        node = bag.set_item("x", 1)
        assert node is not None
        assert node.label == "x"


# ============================================================================
# TestAttributes — camelCase (original + wrapper) and snake_case (new + wrapper)
# ============================================================================


class TestAttributesCamel:
    """Test camelCase attribute methods (original + wrapper)."""

    def test_setAttr_getAttr(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1)
        bag.setAttr("x", color="blue")
        assert bag.getAttr("x", "color") == "blue"

    def test_getAttr_default(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1)
        assert bag.getAttr("x", "missing", default="nope") == "nope"

    def test_delAttr(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1, color="red")
        bag.delAttr("x", "color")
        assert bag.getAttr("x", "color") is None

    def test_setAttr_with_dict(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1)
        bag.setAttr("x", _attributes={"a": 1, "b": 2})
        assert bag.getAttr("x", "a") == 1
        assert bag.getAttr("x", "b") == 2


class TestAttributesSnake:
    """Test snake_case attribute methods (new + wrapper)."""

    def test_set_and_get_attr(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 1)
        bag.set_attr("x", color="red")
        assert bag.get_attr("x", "color") == "red"

    def test_get_attr_default(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 1)
        assert bag.get_attr("x", "missing", default="nope") == "nope"

    def test_del_attr(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 1, color="red", size=10)
        bag.del_attr("x", "color")
        assert bag.get_attr("x", "color") is None
        assert bag.get_attr("x", "size") == 10

    def test_set_attr_with_dict(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 1)
        bag.set_attr("x", _attributes={"a": 1, "b": 2})
        assert bag.get_attr("x", "a") == 1
        assert bag.get_attr("x", "b") == 2


# ============================================================================
# TestPopClear — pop, clear, del (all 3 via bracket notation)
# ============================================================================


class TestPopClear:
    """Test removal operations using common APIs."""

    def test_pop_returns_value(self, bag_class):
        bag = bag_class()
        bag["a"] = 42
        result = bag.pop("a")
        assert result == 42
        assert "a" not in bag

    def test_pop_default(self, bag_class):
        bag = bag_class()
        result = bag.pop("missing", "fallback")
        assert result == "fallback"

    def test_del_item(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        del bag["a"]
        assert "a" not in bag

    def test_clear(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.clear()
        assert len(bag) == 0


class TestPopClearCamel:
    """Test camelCase pop/popNode (original + wrapper)."""

    def test_popNode(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 99)
        node = bag.popNode("x")
        assert node is not None
        assert node.getLabel() == "x"


class TestPopClearSnake:
    """Test snake_case pop_node (new + wrapper)."""

    def test_pop_node_returns_node(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 99, color="red")
        node = bag.pop_node("x")
        assert node is not None
        assert node.label == "x"


# ============================================================================
# TestIteration — keys, values, items, len, iter, contains (all 3)
# ============================================================================


class TestIteration:
    """Test iteration and containment operations (common API)."""

    def test_keys(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert list(bag.keys()) == ["a", "b", "c"]

    def test_values(self, bag_class):
        bag = bag_class()
        bag["a"] = 10
        bag["b"] = 20
        assert list(bag.values()) == [10, 20]

    def test_items(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["b"] = 2
        result = list(bag.items())
        assert result == [("a", 1), ("b", 2)]

    def test_len(self, bag_class):
        bag = bag_class()
        assert len(bag) == 0
        bag["a"] = 1
        assert len(bag) == 1
        bag["b"] = 2
        assert len(bag) == 2

    def test_contains(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        assert "a" in bag
        assert "b" not in bag

    def test_contains_hierarchical(self, bag_class):
        bag = bag_class()
        bag["a.b.c"] = 1
        assert "a" in bag
        assert "a.b" in bag
        assert "a.b.c" in bag
        assert "a.b.d" not in bag

    def test_iter_yields_nodes(self, bag_class):
        bag = bag_class()
        bag["a"] = 1
        bag["b"] = 2
        nodes = list(bag)
        assert len(nodes) == 2
        assert nodes[0].label == "a"
        assert nodes[1].label == "b"


# ============================================================================
# TestIterAliases — iterkeys, itervalues, iteritems (original + wrapper)
# ============================================================================


class TestIterAliases:
    """Test legacy iterator aliases (original + wrapper)."""

    def test_iterkeys(self, bag_class_camel):
        bag = bag_class_camel()
        bag["a"] = 1
        bag["b"] = 2
        result = list(bag.iterkeys())
        assert result == ["a", "b"]

    def test_itervalues(self, bag_class_camel):
        bag = bag_class_camel()
        bag["a"] = 10
        bag["b"] = 20
        result = list(bag.itervalues())
        assert result == [10, 20]

    def test_iteritems(self, bag_class_camel):
        bag = bag_class_camel()
        bag["a"] = 1
        bag["b"] = 2
        result = list(bag.iteritems())
        assert result == [("a", 1), ("b", 2)]


# ============================================================================
# TestBagNodeCamel — BagNode camelCase methods (original + wrapper)
# ============================================================================


class TestBagNodeCamel:
    """Test BagNode camelCase methods (original + wrapper)."""

    def test_getLabel(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 42)
        node = bag.getNode("x")
        assert node.getLabel() == "x"

    def test_getValue_setValue(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 42)
        node = bag.getNode("x")
        assert node.getValue() == 42
        node.setValue(99)
        assert node.getValue() == 99

    def test_getAttr_setAttr_delAttr(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("x", 1)
        node = bag.getNode("x")
        node.setAttr(color="red")
        assert node.getAttr("color") == "red"
        node.delAttr("color")
        assert node.getAttr("color") is None


# ============================================================================
# TestBagNodeSnake — BagNode snake_case methods (new + wrapper)
# ============================================================================


class TestBagNodeSnake:
    """Test BagNode snake_case methods (new + wrapper)."""

    def test_node_label(self, bag_class_snake):
        bag = bag_class_snake()
        bag["x"] = 42
        node = bag.get_node("x")
        assert node.label == "x"

    def test_node_value(self, bag_class_snake):
        bag = bag_class_snake()
        bag["x"] = 42
        node = bag.get_node("x")
        assert node.value == 42

    def test_node_attr(self, bag_class_snake):
        bag = bag_class_snake()
        bag.set_item("x", 1, color="red")
        node = bag.get_node("x")
        assert node.get_attr("color") == "red"

    def test_node_set_value(self, bag_class_snake):
        bag = bag_class_snake()
        bag["x"] = 1
        node = bag.get_node("x")
        node.set_value(99)
        assert bag["x"] == 99


# ============================================================================
# TestGetNode — camelCase (original + wrapper) and snake_case (new + wrapper)
# ============================================================================


class TestGetNodeCamel:
    """Test getNode (original + wrapper)."""

    def test_getNode_returns_node(self, bag_class_camel):
        bag = bag_class_camel()
        bag["x"] = 42
        node = bag.getNode("x")
        assert node is not None
        assert node.getLabel() == "x"

    def test_getNode_missing(self, bag_class_camel):
        bag = bag_class_camel()
        node = bag.getNode("missing")
        assert node is None

    def test_getNode_hierarchical(self, bag_class_camel):
        bag = bag_class_camel()
        bag["a.b.c"] = 42
        node = bag.getNode("a.b.c")
        assert node is not None
        assert node.getValue() == 42


class TestGetNodeSnake:
    """Test get_node (new + wrapper)."""

    def test_get_node_returns_node(self, bag_class_snake):
        bag = bag_class_snake()
        bag["x"] = 42
        node = bag.get_node("x")
        assert node is not None
        assert node.label == "x"

    def test_get_node_missing_returns_none(self, bag_class_snake):
        bag = bag_class_snake()
        node = bag.get_node("missing")
        assert node is None

    def test_get_node_hierarchical(self, bag_class_snake):
        bag = bag_class_snake()
        bag["a.b.c"] = 42
        node = bag.get_node("a.b.c")
        assert node is not None
        assert node.value == 42


# ============================================================================
# TestAddItemDuplicates — addItem with duplicate labels (original + wrapper)
# ============================================================================


class TestAddItemDuplicates:
    """Test addItem allowing duplicate labels."""

    def test_addItem_creates_duplicates(self, bag_class_camel):
        bag = bag_class_camel()
        bag.addItem("member", "John")
        bag.addItem("member", "Paul")
        bag.addItem("member", "George")
        bag.addItem("member", "Ringo")
        nodes = list(bag)
        assert len(nodes) == 4
        values = [n.value for n in nodes]
        assert values == ["John", "Paul", "George", "Ringo"]

    def test_addItem_all_same_label(self, bag_class_camel):
        bag = bag_class_camel()
        bag.addItem("item", "a")
        bag.addItem("item", "b")
        bag.addItem("item", "c")
        labels = [n.label for n in bag]
        assert labels == ["item", "item", "item"]

    def test_addItem_with_attributes(self, bag_class_camel):
        bag = bag_class_camel()
        bag.addItem("x", 1, color="red")
        bag.addItem("x", 2, color="blue")
        nodes = list(bag)
        assert nodes[0].getAttr("color") == "red"
        assert nodes[1].getAttr("color") == "blue"

    def test_addItem_mixed_with_setItem(self, bag_class_camel):
        bag = bag_class_camel()
        bag.setItem("a", 1)
        bag.addItem("b", 2)
        bag.addItem("b", 3)
        bag.setItem("c", 4)
        assert len(list(bag)) == 4
        labels = [n.label for n in bag]
        assert labels == ["a", "b", "b", "c"]


# ============================================================================
# TestSetdefault — all 3 (using bracket to verify)
# ============================================================================


class TestSetdefault:
    """Test setdefault method."""

    def test_setdefault_new_key(self, bag_class):
        bag = bag_class()
        bag.setdefault("x", 42)
        assert bag["x"] == 42

    def test_setdefault_existing_key(self, bag_class):
        bag = bag_class()
        bag["x"] = 10
        bag.setdefault("x", 42)
        assert bag["x"] == 10
