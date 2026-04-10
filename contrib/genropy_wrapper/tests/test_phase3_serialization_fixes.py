"""Phase 3: Serialization fixes and traversal bugs.

Tests for fixes in genro-bag core and wrapper:
- Issue #31: #n and #attr=value in intermediate path traversal
- Issue #36: XML serialization (static mode, False attributes)
- Issue #36: JSON round-trip (node_tag, resolver metadata)

All tests use bag_class_snake fixture (new + wrapper) since these
are genro-bag specific bugs that don't apply to the original gnrbag.
"""

import json

import pytest

import genro_bag
from genro_bag.resolver import BagResolver


# ---------------------------------------------------------------------------
# Test resolver for JSON serialization round-trip.
# Must be module-level so importlib can find it during deserialize().
# ---------------------------------------------------------------------------

class _TestResolver(BagResolver):
    """Minimal resolver for serialization testing.

    Multiplies base * multiplier. Parameters are all JSON-serializable
    so serialize()/deserialize() round-trip works.
    """

    class_args = ["base"]
    class_kwargs = {
        "cache_time": 0,
        "read_only": False,
        "retry_policy": None,
        "as_bag": None,
        "multiplier": 2,
    }
    internal_params = {"cache_time", "read_only", "retry_policy", "as_bag"}

    def load(self):
        return self._kw["base"] * self._kw["multiplier"]


# ===========================================================================
# A1. #n and #attr=value in intermediate path traversal
# ===========================================================================

class TestHashTraversal:
    """Test #n and #attr=value syntax in intermediate path segments."""

    def _make_bag(self, Bag):
        """Create a bag with items containing child nodes with attributes.

        Structure:
            items/
                item_a  (id=10)  -> sub/ name="alpha"
                item_b  (id=20)  -> sub/ name="beta"
                item_c  (id=30)  -> sub/ name="gamma"
        """
        bag = Bag()
        items = Bag()

        for label, id_val, name in [
            ("item_a", "10", "alpha"),
            ("item_b", "20", "beta"),
            ("item_c", "30", "gamma"),
        ]:
            child = Bag()
            child.set_item("name", name)
            items.set_item(label, child, _attributes={"id": id_val})

        bag.set_item("items", items)
        return bag

    def test_numeric_index_intermediate(self, bag_class_snake):
        """Access nested value via #n in intermediate segment.

        bag['items.#0.name'] should return the name of the first item.
        """
        bag = self._make_bag(bag_class_snake)
        result = bag["items.#0.name"]
        assert result == "alpha"

    def test_numeric_index_second_item(self, bag_class_snake):
        """Access second item via #1."""
        bag = self._make_bag(bag_class_snake)
        result = bag["items.#1.name"]
        assert result == "beta"

    def test_attr_value_intermediate(self, bag_class_snake):
        """Access nested value via #attr=value in intermediate segment.

        bag['items.#id=20.name'] should find the item with id=20
        and return its child 'name'.
        """
        bag = self._make_bag(bag_class_snake)
        result = bag["items.#id=20.name"]
        assert result == "beta"

    def test_attr_value_first_item(self, bag_class_snake):
        """Access item with id=10 via attribute lookup."""
        bag = self._make_bag(bag_class_snake)
        result = bag["items.#id=10.name"]
        assert result == "alpha"

    def test_attr_value_not_found(self, bag_class_snake):
        """#attr=value with non-existent value returns None."""
        bag = self._make_bag(bag_class_snake)
        result = bag.get_item("items.#id=999.name")
        assert result is None

    def test_numeric_index_out_of_range(self, bag_class_snake):
        """#n with out-of-range index returns None."""
        bag = self._make_bag(bag_class_snake)
        result = bag.get_item("items.#99.name")
        assert result is None


# ===========================================================================
# A2 + A3. XML serialization fixes
# ===========================================================================

class TestXmlStaticAndAttrs:
    """Test XML serialization: static mode and False attribute handling."""

    def test_xml_no_resolver_trigger(self, bag_class_snake):
        """XML serialization must NOT trigger resolvers.

        A resolver that raises on execution is attached to a node.
        to_xml() should succeed without triggering it.
        """
        class _RaisingResolver(BagResolver):
            """Resolver that raises if executed."""
            class_args = []
            class_kwargs = {
                "cache_time": 0,
                "read_only": False,
                "retry_policy": None,
                "as_bag": None,
            }
            internal_params = {"cache_time", "read_only", "retry_policy", "as_bag"}

            def load(self):
                raise RuntimeError("Resolver should not be triggered during XML serialization")

        bag = bag_class_snake()
        resolver = _RaisingResolver()
        bag.set_item("data", None, resolver=resolver)

        # This should NOT raise — resolver must not be triggered
        xml = bag.to_xml()
        assert "<data" in xml

    def test_xml_false_attribute_preserved(self, bag_class_snake):
        """Attributes with value False must appear in XML output.

        False is a valid attribute value, distinct from None (which means
        "no value" and is correctly omitted).
        """
        bag = bag_class_snake()
        bag.set_item("node", "hello", _attributes={"active": False, "visible": True})
        xml = bag.to_xml()

        # False should appear in the XML output.
        # The wrapper adds ::B type suffix, core does not.
        assert "active=" in xml
        assert "False" in xml
        # True should also appear
        assert "visible=" in xml
        assert "True" in xml

    def test_xml_none_attribute_omitted(self, bag_class_snake):
        """Attributes with value None should still be omitted from XML."""
        bag = bag_class_snake()
        bag.set_item("node", "hello", _attributes={"present": "yes", "absent": None})
        xml = bag.to_xml()

        assert 'present="yes"' in xml
        assert "absent" not in xml


# ===========================================================================
# A4 + A5. JSON round-trip: node_tag and resolver
# ===========================================================================

class TestJsonRoundTrip:
    """Test JSON serialization/deserialization preserves node_tag and resolver."""

    def test_json_round_trip_node_tag(self, bag_class_snake):
        """node_tag must survive JSON round-trip.

        A node with node_tag="custom_type" should have the same
        node_tag after to_json() -> from_json().
        """
        bag = bag_class_snake()
        bag.set_item("item", "value", node_tag="custom_type")

        # Verify node_tag is set
        node = bag.get_node("item")
        assert node.node_tag == "custom_type"

        # Round-trip through JSON
        json_str = bag.to_json()
        restored = bag_class_snake.from_json(json_str)

        restored_node = restored.get_node("item")
        assert restored_node is not None
        assert restored_node.node_tag == "custom_type"
        assert restored["item"] == "value"

    def test_json_node_tag_none_not_serialized(self, bag_class_snake):
        """Nodes without node_tag should not have 'tag' in JSON output."""
        bag = bag_class_snake()
        bag.set_item("item", "value")

        json_str = bag.to_json()
        # Parse the JSON to inspect structure
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        if isinstance(data, list) and data:
            assert "tag" not in data[0]

    def test_json_round_trip_resolver(self):
        """Resolver metadata must survive JSON round-trip.

        A node with a _TestResolver should have the resolver
        reconstructed after to_json() -> from_json().
        Only tested on genro_bag.Bag (not wrapper) because the
        test resolver class is specific to genro_bag.
        """
        Bag = genro_bag.Bag

        bag = Bag()
        resolver = _TestResolver(10, multiplier=3)
        bag.set_item("computed", None, resolver=resolver)

        # Verify resolver works
        assert bag["computed"] == 30

        # Round-trip through JSON
        json_str = bag.to_json()
        restored = Bag.from_json(json_str)

        # Verify resolver is reconstructed
        restored_node = restored.get_node("computed")
        assert restored_node is not None
        assert restored_node.resolver is not None
        assert isinstance(restored_node.resolver, _TestResolver)

        # Verify resolver produces same result
        assert restored["computed"] == 30

    def test_json_resolver_metadata_in_output(self):
        """Verify resolver metadata structure in JSON output."""
        Bag = genro_bag.Bag

        bag = Bag()
        resolver = _TestResolver(10, multiplier=3)
        bag.set_item("computed", None, resolver=resolver)

        json_str = bag.to_json()
        data = json.loads(json_str) if isinstance(json_str, str) else json_str

        # Find the node dict
        assert isinstance(data, list)
        node_dict = data[0]
        assert "resolver" in node_dict
        assert node_dict["resolver"]["resolver_class"] == "_TestResolver"
        assert node_dict["resolver"]["resolver_module"] == __name__
