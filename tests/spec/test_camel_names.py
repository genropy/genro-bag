# Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Name-surface contracts for mixed spelling on native engine classes."""

import pytest

from genro_bag import Bag, BagNode
from genro_bag.resolver import BagCbResolver


def test_mixed_names_keep_engine_classes_through_nested_creation():
    bag = Bag()
    bag.setItem("customer.name", "Mario")
    assert bag.get_item("customer.name") == "Mario"
    bag.set_item("customer.name", "Anna")
    assert bag.getItem("customer.name") == "Anna"
    branch = bag.getItem("customer")
    node = branch.getNode("name")
    assert type(branch) is Bag
    assert type(node) is BagNode
    node.setValue("Ada")
    assert node.get_value() == bag.getItem("customer.name") == "Ada"
    assert "getItem" in dir(Bag)
    assert Bag.getItem(bag, "customer.name") == "Ada"


def test_alias_dispatches_to_override_with_super():
    class UpperBag(Bag):
        def get_item(self, path, *args, **kwargs):
            return super().get_item(path, *args, **kwargs).upper()

    bag = UpperBag({"name": "Ada"})
    assert bag.getItem("name") == bag.get_item("name") == "ADA"


def test_explicit_camel_override_can_delegate_to_super():
    class AdaptedBag(Bag):
        def getItem(self, path):
            return super().getItem(path).upper()

    bag = AdaptedBag({"name": "Ada"})
    assert bag.getItem("name") == "ADA"
    assert bag.get_item("name") == "Ada"


def test_resolver_and_readable_properties_keep_identity():
    resolver = BagCbResolver(lambda: 42)
    bag = Bag()
    bag.setItem("answer", resolver)
    node = bag.getNode("answer")
    assert node.resolver is resolver
    assert node.parentBag is bag
    assert resolver.parentNode is node
    assert bag.getItem("answer") == 42


def test_explicit_property_setter_updates_modern_property():
    bag = Bag({"name": "Ada"})
    node = bag.getNode("name")
    node.staticvalue = "Anna"
    assert node.static_value == "Anna"
    assert bag.get_item("name") == "Anna"


def test_irregular_backref_names_delegate_to_engine():
    bag = Bag()
    bag.setItem("customer.name", "Ada")
    bag.setBackRef()
    assert bag.backref
    assert bag.getItem("customer").parent is bag
    bag.clearBackRef()
    assert not bag.backref


def test_phase_two_serialization_adapters_are_explicitly_exposed():
    assert callable(Bag.from_xml)
    assert callable(Bag().fromXml)
    assert callable(Bag().fromJson)


@pytest.mark.parametrize("name", ["missingName", "missing_name", "_getItem", "__missing__"])
def test_unknown_and_private_names_raise_attribute_error(name):
    with pytest.raises(AttributeError):
        getattr(Bag(), name)
