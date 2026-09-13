# Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Legacy Bag adapter contracts on the native engine."""

import pytest

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver


def test_legacy_item_kwargs_are_always_node_attributes():
    bag = Bag()
    value = object()

    bag.setItem(
        "instances.app",
        value,
        _attributes={"path": "old", "explicit": True},
        path="/isolated/instance",
        resolver="metadata only",
        node_position="metadata only",
    )
    node = bag.get_node("instances.app")

    assert node.static_value is value
    assert node.resolver is None
    assert node.attr == {
        "path": "/isolated/instance",
        "explicit": True,
        "resolver": "metadata only",
        "node_position": "metadata only",
    }


def test_add_item_and_append_node_keep_legacy_kwargs_as_attributes():
    bag = Bag()
    bag.addItem("row", 1, path="first", resolver="metadata only")
    with pytest.warns(DeprecationWarning, match="renamed duplicate"):
        bag.addItem("row", 2, path="second", resolver="metadata only")
    appended = bag.appendNode(
        "tail",
        3,
        path="third",
        resolver="metadata only",
        node_position="metadata only",
    )

    assert bag.get_node("row").resolver is None
    assert bag.get_attr("row") == {"path": "first", "resolver": "metadata only"}
    assert bag.get_node("row__dup_1").resolver is None
    assert bag.get_attr("row__dup_1") == {
        "path": "second",
        "resolver": "metadata only",
    }
    assert appended.resolver is None
    assert appended.attr == {
        "path": "third",
        "resolver": "metadata only",
        "node_position": "metadata only",
    }


def test_filter_recursively_prunes_branches_and_preserves_attributes():
    bag = Bag()
    branch = Bag()
    branch.set_item(
        "keep",
        1,
        _attributes={"selected": True, "nullable": None},
        _remove_null_attributes=False,
    )
    branch.set_item("drop", 2, _attributes={"selected": False})
    bag.set_item(
        "branch",
        branch,
        _attributes={"section": "main", "empty": None},
        _remove_null_attributes=False,
    )
    bag.set_item("top_drop", 3)

    visited = []

    def selected(node):
        visited.append(node.label)
        return node.attr.get("selected", False)

    result = bag.filter(selected)

    assert visited == ["keep", "drop", "top_drop"]
    assert result.keys() == ["branch"]
    assert result.get_attr("branch") == {"section": "main", "empty": None}
    assert result.get_attr("branch.keep") == {"selected": True, "nullable": None}
    assert result.get_item("branch.keep") == 1


def test_filter_calls_callback_for_empty_bags():
    bag = Bag()
    bag.set_item("keep_empty", Bag(), _attributes={"selected": True})
    bag.set_item("drop_empty", Bag(), _attributes={"selected": False})

    visited = []

    def selected(node):
        visited.append(node.label)
        return node.attr["selected"]

    result = bag.filter(selected)

    assert visited == ["keep_empty", "drop_empty"]
    assert result.keys() == ["keep_empty"]
    assert isinstance(result.get_item("keep_empty"), Bag)
    assert not result.get_item("keep_empty")


def test_filter_defaults_to_static_resolver_reads():
    calls = []
    bag = Bag()
    bag.set_item(
        "lazy",
        None,
        resolver=BagCbResolver(lambda: calls.append(1) or 7, read_only=True),
    )

    result = bag.filter(lambda node: node.label == "lazy")

    assert calls == []
    assert result.get_item("lazy", static=True) is None
    assert result.get_resolver("lazy") is None


def test_filter_nonstatic_mode_uses_resolved_values():
    calls = []
    bag = Bag()
    bag.set_item(
        "lazy",
        None,
        resolver=BagCbResolver(lambda: calls.append(1) or 7, read_only=True),
    )

    result = bag.filter(lambda node: True, _mode="resolved")

    assert calls == [1]
    assert result.get_item("lazy") == 7
    assert result.get_resolver("lazy") is None


def test_filter_preserves_each_native_bag_subclass_during_recursion():
    class OuterBag(Bag):
        pass

    class InnerBag(Bag):
        pass

    inner = InnerBag()
    inner.set_item("keep", 1, _attributes={"selected": True})
    inner.set_item("drop", 2)
    bag = OuterBag()
    bag.set_item("inner", inner)

    result = bag.filter(lambda node: node.attr.get("selected", False))

    assert type(result) is OuterBag
    assert type(result.get_item("inner")) is InnerBag
    assert result.get_item("inner").keys() == ["keep"]


def test_filter_recurses_into_a_resolver_returned_bag_when_nonstatic():
    class ResolvedBag(Bag):
        pass

    resolved = ResolvedBag()
    resolved.set_item("keep", 1, _attributes={"selected": True})
    resolved.set_item("drop", 2)
    bag = Bag()
    bag.set_item("lazy_branch", None, resolver=BagCbResolver(lambda: resolved))

    result = bag.filter(
        lambda node: node.attr.get("selected", False),
        _mode="resolved",
    )

    assert type(result.get_item("lazy_branch")) is ResolvedBag
    assert result.get_item("lazy_branch").keys() == ["keep"]
    assert result.get_resolver("lazy_branch") is None


def test_find_node_by_attr_preserves_depth_first_identity_and_static_mode():
    calls = []
    bag = Bag()
    nested = Bag()
    first = nested.set_item('first', 1, nodeId='target')
    bag.set_item('branch', nested)
    bag.set_item('second', 2, nodeId='target')
    bag.set_item('lazy', BagCbResolver(lambda: calls.append(1) or Bag()))
    assert bag.findNodeByAttr('nodeId', 'target') is first
    assert bag.findNodeByAttr('nodeId', 'missing') is None
    assert calls == []
    assert bag.findNodeByAttr('nodeId', 'missing', _mode='') is None
    assert calls == [1]
