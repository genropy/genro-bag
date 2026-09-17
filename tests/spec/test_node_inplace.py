"""Spec test: BagNode - public node API in place.

Depends on test_basic.py (set_item, get_item, get_node, etc.).

## Principle

A BagNode is NOT instantiated alone in tests (alone it makes no sense:
needs a Bag to contain it). It is ALWAYS obtained via Bag:

    node = bag.set_item(path, value, ...)       # return
    node = bag.get_node(path)                   # lookup
    node = bag.pop_node(path)                   # removal
    node = bag.node(label)                      # direct access

Once in place, public methods (no underscore) of BagNode
are public API and must be exercised.

## Scale

1.  Node identity                               label / __str__ / __repr__ / __eq__
2.  value / value setter / get_value
3.  static_value                                cached value without trigger
4.  attr property / set_attr / get_attr / del_attr / has_attr
5.  is_branch                                   Bag value vs scalar
6.  retired validation surface                  no longer provided
7.  position                                    index in parent container
8.  parent_bag / parent_node                    navigation
9.  fullpath (with backref)                     path pointed to node
10. get_inherited_attributes                    merge along parent chain
11. attribute_owner_node                        ascending search for attribute
12. diff                                        compare label/attr/value
13. as_tuple                                    (label, value, attr, resolver)
14. to_json                                     serializable dict
15. subscribe / unsubscribe                     node-level notifications
16. reset_resolver                              removes resolver
17. compiled                                    external compiled dict (lazy initialized)
18. orphaned                                    recursive detach from parent
19. property _ (underscore)                     returns parent_bag or raises
20. xml_tag                                     preserved from XML parsing
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagNode

# =============================================================================
# 1. Node identity
# =============================================================================


class TestNodeIdentity:
    def test_label_attribute(self):
        """node.label exposes label used for insertion."""
        bag = Bag()
        node = bag.set_item("foo", 1)
        assert node.label == "foo"

    def test_str_contains_label(self):
        """str(node) includes label."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert "x" in str(node)

    def test_repr_contains_label_and_id(self):
        """repr(node) includes label and object id."""
        bag = Bag()
        node = bag.set_item("x", 1)
        r = repr(node)
        assert "x" in r
        assert str(id(node)) in r

    def test_equal_nodes_have_same_label_attr_value(self):
        """Two nodes with same label, attr, value are equal (via __eq__)."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v"})
        n2 = b.set_item("x", 1, _attributes={"k": "v"})
        assert n1 == n2

    def test_different_value_not_equal(self):
        """Nodes with different values are not equal."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("x", 2)
        assert n1 != n2

    def test_different_label_not_equal(self):
        """Nodes with different labels are not equal."""
        bag = Bag()
        n1 = bag.set_item("x", 1)
        n2 = bag.set_item("y", 1)
        assert n1 != n2

    def test_ne_with_non_bagnode(self):
        """__eq__ with non-BagNode object returns False."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node != "not a node"
        assert node != 42


# =============================================================================
# 2. value / value setter / get_value
# =============================================================================


class TestNodeValue:
    def test_value_property_reads_value(self):
        """node.value reads node value."""
        bag = Bag()
        node = bag.set_item("x", 42)
        assert node.value == 42

    def test_value_setter_updates_value(self):
        """node.value = X updates value, visible also from bag[x]."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.value = 99
        assert bag.get_item("x") == 99

    def test_get_value_static_true_reads_static(self):
        """get_value(static=True) returns cached value without trigger."""
        bag = Bag()
        node = bag.set_item("x", 7)
        assert node.get_value(static=True) == 7


# =============================================================================
# 3. static_value
# =============================================================================


class TestStaticValue:
    def test_static_value_property(self):
        """static_value exposes cached value without triggering resolver."""
        bag = Bag()
        node = bag.set_item("x", 10)
        assert node.static_value == 10

    def test_static_value_on_node_with_resolver_before_load(self):
        """static_value on node with resolver before read is None."""
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        # never read -> static_value None
        assert node.static_value is None


# =============================================================================
# 4. attr / set_attr / get_attr / del_attr / has_attr
# =============================================================================


class TestNodeAttr:
    def test_attr_property_returns_dict(self):
        """node.attr returns dict of attributes."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.attr == {"k": "v"}

    def test_set_attr_via_kwargs(self):
        """node.set_attr(k=v) adds attribute."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.set_attr(k="v")
        assert node.get_attr("k") == "v"

    def test_set_attr_via_dict(self):
        """node.set_attr(attr={...}) accepts dict."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.set_attr(attr={"a": 1, "b": 2})
        assert node.get_attr("a") == 1
        assert node.get_attr("b") == 2

    def test_get_attr_single(self):
        """get_attr(label) returns specific attribute."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.get_attr("k") == "v"

    def test_get_attr_missing_returns_default(self):
        """get_attr(missing, default=X) returns X."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.get_attr("nope", default="fallback") == "fallback"

    def test_get_attr_no_label_returns_all(self):
        """get_attr() without label returns all attributes."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        result = node.get_attr()
        assert result == {"a": 1, "b": 2}

    def test_del_attr_removes_key(self):
        """del_attr(key) removes attribute."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        node.del_attr("a")
        assert not node.has_attr("a")
        assert node.has_attr("b")

    def test_del_attr_comma_separated(self):
        """del_attr('a,b') removes multiple attributes from comma-separated string."""
        bag = Bag()
        node = bag.set_item(
            "x", 1, _attributes={"a": 1, "b": 2, "c": 3}
        )
        node.del_attr("a,b")
        assert not node.has_attr("a")
        assert not node.has_attr("b")
        assert node.has_attr("c")

    def test_has_attr_without_value(self):
        """has_attr(key) returns True if attribute exists."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.has_attr("k") is True
        assert node.has_attr("missing") is False

    def test_has_attr_with_value_match(self):
        """has_attr(key, value) returns True only if match."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"kind": "int"})
        assert node.has_attr("kind", "int") is True
        assert node.has_attr("kind", "str") is False


# =============================================================================
# 5. is_branch
# =============================================================================


class TestIsBranch:
    def test_is_branch_true_for_bag_value(self):
        """Node with Bag value has is_branch=True."""
        bag = Bag()
        bag["outer.inner"] = 1  # create sub-bag 'outer'
        outer = bag.get_node("outer")
        assert isinstance(outer, BagNode)
        assert outer.is_branch is True

    def test_is_branch_false_for_scalar(self):
        """Node with scalar value has is_branch=False."""
        bag = Bag()
        node = bag.set_item("x", 42)
        assert node.is_branch is False


# =============================================================================
# 6. Retired validation surface
# =============================================================================


class TestRetiredValidation:
    def test_node_validation_is_no_longer_provided(self):
        node = Bag().set_item("x", 1)
        assert not hasattr(node, "is_valid")
        assert not hasattr(node, "_invalid_reasons")


# =============================================================================
# 7. position
# =============================================================================


class TestPosition:
    def test_position_returns_index(self):
        """position returns 0-based index in parent."""
        bag = Bag()
        n0 = bag.set_item("a", 1)
        n1 = bag.set_item("b", 2)
        n2 = bag.set_item("c", 3)
        assert n0.position == 0
        assert n1.position == 1
        assert n2.position == 2

    def test_position_reflects_reordering(self):
        """After reordering, position reflects new position."""
        bag = Bag()
        bag.set_item("a", 1)
        bag.set_item("b", 2)
        n = bag.set_item("c", 3, node_position="<")
        assert n.position == 0

    def test_position_none_on_popped_node(self):
        """A popped node has no containing Bag and therefore no position."""
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        assert node.position is None


# =============================================================================
# 8. parent_bag / parent_node
# =============================================================================


class TestParentLinks:
    def test_parent_bag_returns_containing_bag(self):
        """node.parent_bag is Bag containing node."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.parent_bag is bag

    def test_parent_bag_none_after_orphaned_call(self):
        """pop_node detaches immediately; orphaned remains safe to call again."""
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        # pop_node already removed the parent reference
        assert node.parent_bag is None
        # orphaned() zeros reference
        node.orphaned()
        assert node.parent_bag is None

    def test_parent_node_with_backref(self):
        """With backref, node inside sub-Bag sees parent_node."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)  # enable backref
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.parent_node is not None
        assert inner.parent_node.label == "outer"

    def test_parent_node_none_for_top_level(self):
        """Top-level node has no parent_node."""
        root = Bag()
        root.set_backref()
        node = root.set_item("x", 1)
        assert node.parent_node is None


# =============================================================================
# 9. fullpath (with backref)
# =============================================================================


class TestNodeFullpath:
    def test_fullpath_of_connected_top_level_node(self):
        """A node connected to a root Bag has its label as its path."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.fullpath == "x"

    def test_fullpath_reports_path_with_backref(self):
        """With backref, nested node has dot-separated fullpath from root."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)  # enable backref
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.fullpath == "outer.inner"


# =============================================================================
# 10. get_inherited_attributes
# =============================================================================


class TestInheritedAttributes:
    def test_inherited_merges_ancestors_attributes(self):
        """inherited returns attributes merged from parent chain (with backref)."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        # attribute on outer node (container)
        root.set_attr("outer", env="prod")
        # attribute on inner node (leaf)
        root.set_attr("outer.inner", role="worker")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        inherited = inner.get_inherited_attributes()
        assert inherited.get("env") == "prod"
        assert inherited.get("role") == "worker"

    def test_inherited_own_overrides_ancestor(self):
        """If node has attribute already in ancestor, node wins."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", k="from_outer")
        root.set_attr("outer.inner", k="from_inner")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.get_inherited_attributes()["k"] == "from_inner"


# =============================================================================
# 11. attribute_owner_node
# =============================================================================


class TestAttributeOwnerNode:
    def test_finds_ancestor_with_attribute(self):
        """attribute_owner_node finds ancestor owning attribute."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", kind="section")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        owner = inner.attribute_owner_node("kind")
        assert isinstance(owner, BagNode)
        assert owner.label == "outer"

    def test_finds_ancestor_with_attr_value_match(self):
        """attribute_owner_node with value matches on (key, value)."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", role="admin")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        owner = inner.attribute_owner_node("role", "admin")
        assert isinstance(owner, BagNode)
        assert owner.label == "outer"

    def test_returns_none_when_not_found(self):
        """attribute_owner_node returns None if attribute not found."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.attribute_owner_node("nonexistent") is None


# =============================================================================
# 12. diff
# =============================================================================


class TestDiff:
    def test_diff_none_when_equal(self):
        """diff returns None if nodes are equivalent."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v"})
        n2 = b.set_item("x", 1, _attributes={"k": "v"})
        assert n1.diff(n2) is None

    def test_diff_reports_label_difference(self):
        """diff reports different label."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("y", 1)
        result = n1.diff(n2)
        assert result is not None
        assert "label" in result.lower()

    def test_diff_reports_value_difference(self):
        """diff reports different value."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("x", 2)
        result = n1.diff(n2)
        assert result is not None
        assert "value" in result.lower()

    def test_diff_reports_attr_difference(self):
        """diff reports different attributes."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v1"})
        n2 = b.set_item("x", 1, _attributes={"k": "v2"})
        result = n1.diff(n2)
        assert result is not None
        assert "attr" in result.lower()


# =============================================================================
# 13. as_tuple
# =============================================================================


class TestAsTuple:
    def test_returns_label_value_attr_resolver(self):
        """as_tuple returns (label, value, attr, resolver)."""
        bag = Bag()
        node = bag.set_item("x", 42, _attributes={"k": "v"})
        label, value, attr, resolver = node.as_tuple()
        assert label == "x"
        assert value == 42
        assert attr == {"k": "v"}
        assert resolver is None

    def test_tuple_has_resolver_when_set(self):
        """If node has resolver, it appears in tuple."""
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        _, _, _, resolver = node.as_tuple()
        assert isinstance(resolver, UuidResolver)


# =============================================================================
# 14. to_json
# =============================================================================


class TestNodeToJson:
    def test_returns_dict_with_label_value_attr(self):
        """to_json returns dict with keys 'label', 'value', 'attr'."""
        bag = Bag()
        node = bag.set_item("x", 42, _attributes={"k": "v"})
        data = node.to_json()
        assert data["label"] == "x"
        assert data["value"] == 42
        assert data["attr"] == {"k": "v"}


# =============================================================================
# 15. subscribe / unsubscribe (node-level)
# =============================================================================


class TestNodeSubscription:
    def test_node_subscribe_receives_update_notifications(self):
        """node.subscribe registers callback invoked on value change."""
        events: list = []
        bag = Bag()
        node = bag.set_item("x", 1)
        node.subscribe("s1", lambda **kw: events.append(kw))
        bag["x"] = 2

        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"

    def test_node_unsubscribe_stops_notifications(self):
        """After unsubscribe, no more node-level events arrive."""
        events: list = []
        bag = Bag()
        node = bag.set_item("x", 1)
        node.subscribe("s1", lambda **kw: events.append(kw))
        node.unsubscribe("s1")
        bag["x"] = 2

        assert events == []


# =============================================================================
# 16. reset_resolver
# =============================================================================


class TestResetResolver:
    def test_missing_resolver_raises_without_mutation(self):
        bag = Bag({"item": 42})
        node = bag.get_node("item")
        node.set_attr(caption="Kept")
        events = []
        bag.subscribe("watch", update=lambda **kw: events.append(kw))
        for reset in (node.reset_resolver, node.resetResolver):
            with pytest.raises(ValueError, match="node has no resolver"):
                reset()
            assert node.get_value(static=True) == 42
            assert node.attr == {"caption": "Kept"}
            assert not events

    def test_reset_resolver_clears_value_and_invalidates_cache(self):
        """reset_resolver() invalidates cache and zeros current value.

        Does not remove resolver: the name refers to "reset of resolver",
        i.e. reset of cached state, not deletion of object.
        """
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        first = bag["id"]  # triggers load -> UUID generated and cached
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        assert node.resolver is not None
        node.reset_resolver()
        # resolver remains, but cache is invalidated: re-access generates
        # new uuid (cache_time=-1 -> not reloaded until cleared)
        second = bag["id"]
        assert node.resolver is not None
        assert first != second


# =============================================================================
# 17. compiled (lazy)
# =============================================================================


class TestCompiled:
    def test_compiled_returns_dict_lazy_init(self):
        """compiled exposes dict for external data, initialized at first access."""
        bag = Bag()
        node = bag.set_item("x", 1)
        c = node.compiled
        assert isinstance(c, dict)

    def test_compiled_same_instance_across_calls(self):
        """Two reads of compiled return same dict (same object)."""
        bag = Bag()
        node = bag.set_item("x", 1)
        c1 = node.compiled
        c2 = node.compiled
        assert c1 is c2


# =============================================================================
# 18. orphaned
# =============================================================================


class TestOrphaned:
    def test_orphaned_clears_parent_bag(self):
        """orphaned() zeros parent_bag on node and returns self for chaining."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.parent_bag is bag
        result = node.orphaned()
        assert result is node
        assert node.parent_bag is None


# =============================================================================
# 19. _ property (underscore) - parent_bag getter with raise
# =============================================================================


class TestUnderscoreProperty:
    def test_returns_parent_bag(self):
        """node._ returns parent Bag when node is attached."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node._ is bag

    def test_raises_when_no_parent(self):
        """node._ on node without parent_bag raises ValueError.

        A node extracted by pop_node has no parent.
        """
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        node.orphaned()
        with pytest.raises(ValueError):
            _ = node._


# =============================================================================
# 20. xml_tag
# =============================================================================


class TestXmlTag:
    def test_xml_tag_preserved_from_parsing(self):
        """After XML parse, node.xml_tag preserves original element tag."""
        bag = Bag.from_xml("<root><item>v</item></root>")
        node = bag.get_node("root.item")
        assert isinstance(node, BagNode)
        assert node.xml_tag == "item"

    def test_xml_tag_none_when_not_from_parsing(self):
        """A node created via set_item has no xml_tag."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.xml_tag is None


# =============================================================================
# 21. set_value with _attributes: 'upd_value_attr' event on parent
# =============================================================================


class TestSetValueWithAttributes:
    def test_set_value_with_attributes_fires_upd_value_attr_on_parent(self):
        """set_value(v, _attributes={...}) with backref emits 'upd_value_attr'."""
        events: list[str] = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_value(99, _attributes={"kind": "int"})

        assert "upd_value_attr" in events
        # value and attribute are both updated
        assert bag.get_item("x") == 99
        assert bag.get_attr("x", "kind") == "int"

    def test_set_value_with_updattr_false_replaces_attributes(self):
        """set_value(v, _attributes={...}, _updattr=False) replaces attributes."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        # _updattr=False: complete replacement, not merge
        node.set_value(99, _attributes={"c": 3}, _updattr=False)

        # old attributes are gone
        assert not node.has_attr("a")
        assert not node.has_attr("b")
        # only new attribute remains
        assert node.get_attr("c") == 3

    def test_set_value_does_not_fire_when_unchanged(self):
        """set_value with same value and same attr emits no event."""
        events: list[str] = []
        bag = Bag()
        bag.set_item("x", 1, _attributes={"k": "v"})
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        # same value, same attr -> no change
        node.set_value(1, _attributes={"k": "v"})
        assert events == []

    def test_set_value_trigger_false_suppresses_events(self):
        """set_value(v, trigger=False) does not notify subscribers."""
        events: list = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_value(42, trigger=False)

        assert events == []
        # but value is changed
        assert bag.get_item("x") == 42


# =============================================================================
# 22. set_value with BagNode as value: extract value and merge attr
# =============================================================================


class TestSetValueWithBagNode:
    def test_set_value_with_bagnode_extracts_value_and_replaces_attrs(self):
        """set_value(other_node) extracts value and replaces attr with other's.

        With _updattr not specified (default None in set_value), set_attr
        goes in replace mode: pre-existing attr are replaced
        by those of other node.
        """
        src = Bag()
        other = src.set_item("src", 42, _attributes={"origin": "lab"})

        dst = Bag()
        node = dst.set_item("x", 0, _attributes={"target": "prod"})
        node.set_value(other)

        # value of 'x' becomes 42 (extracted from other)
        assert dst.get_item("x") == 42
        # other's attr present
        assert dst.get_attr("x", "origin") == "lab"
        # pre-existing attr 'target' replaced (replace mode)
        assert dst.get_attr("x", "target") is None


# =============================================================================
# 23. set_attr without trigger
# =============================================================================


class TestSetAttrTriggerFalse:
    def test_set_attr_trigger_false_does_not_notify(self):
        """node.set_attr(trigger=False) updates attr but does not notify."""
        events: list = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_attr(trigger=False, k="v")

        assert events == []
        assert node.get_attr("k") == "v"
