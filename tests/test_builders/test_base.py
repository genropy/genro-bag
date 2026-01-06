# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase."""

import pytest

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders.decorators import element


class SimpleBuilder(BagBuilderBase):
    """Simple builder for testing."""

    @element(tags='item, product')
    def item(self, target, tag, **attr):
        return self.child(target, tag, value='', **attr)

    @element(children='item[1:]')
    def container(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def section(self, target, tag, **attr):
        return self.child(target, tag, **attr)


class TestBagBuilderBase:
    """Tests for BagBuilderBase functionality."""

    def test_bag_with_builder(self):
        """Bag can be created with a builder."""
        builder = SimpleBuilder()
        bag = Bag(builder=builder)
        assert bag.builder is builder

    def test_bag_without_builder(self):
        """Bag without builder works normally."""
        bag = Bag()
        assert bag.builder is None
        bag['test'] = 'value'
        assert bag['test'] == 'value'

    def test_builder_creates_leaf_node(self):
        """Builder creates leaf nodes with tag."""
        bag = Bag(builder=SimpleBuilder())
        node = bag.item(name='test')

        assert node.tag == 'item'
        assert node.label == 'item_0'
        assert node.value == ''
        assert node.attr.get('name') == 'test'

    def test_builder_creates_branch_node(self):
        """Builder creates branch nodes (returns Bag)."""
        bag = Bag(builder=SimpleBuilder())
        container = bag.container()

        assert isinstance(container, Bag)
        # Check the node was created in parent
        node = bag.get_node('container_0')
        assert node.tag == 'container'

    def test_builder_inheritance(self):
        """Child bags inherit builder from parent."""
        bag = Bag(builder=SimpleBuilder())
        container = bag.container()

        assert container.builder is bag.builder

    def test_builder_auto_label_generation(self):
        """Builder auto-generates unique labels."""
        bag = Bag(builder=SimpleBuilder())
        bag.item()
        bag.item()
        bag.item()

        labels = list(bag.keys())
        assert labels == ['item_0', 'item_1', 'item_2']

    def test_builder_multi_tag_method(self):
        """Single method handles multiple tags."""
        bag = Bag(builder=SimpleBuilder())
        bag.item()
        bag.product()

        node1 = bag.get_node('item_0')
        node2 = bag.get_node('product_0')

        assert node1.tag == 'item'
        assert node2.tag == 'product'

    def test_builder_fluent_api(self):
        """Builder enables fluent API."""
        bag = Bag(builder=SimpleBuilder())
        container = bag.container()
        container.item(name='first')
        container.item(name='second')

        assert len(bag) == 1
        assert len(container) == 2

    def test_builder_check_valid_structure(self):
        """check() returns empty list for valid structure."""
        bag = Bag(builder=SimpleBuilder())
        container = bag.container()
        container.item()
        container.item()

        node = bag.get_node('container_0')
        errors = bag.builder.check(container, parent_tag='container')
        assert errors == []

    def test_builder_check_missing_required_children(self):
        """check() reports missing required children."""
        bag = Bag(builder=SimpleBuilder())
        container = bag.container()
        # No items added - container requires at least 1 item

        errors = bag.builder.check(container, parent_tag='container')
        assert len(errors) == 1
        assert 'requires at least 1' in errors[0]


class TestBuilderSchema:
    """Tests for _schema-based builders."""

    def test_schema_based_element(self):
        """Schema dict defines elements."""
        class SchemaBuilder(BagBuilderBase):
            _schema = {
                'div': {'children': 'span, p'},
                'span': {'leaf': True},
                'p': {'leaf': True},
            }

        bag = Bag(builder=SchemaBuilder())
        div = bag.div()
        div.span()
        div.p()

        assert isinstance(div, Bag)
        assert len(div) == 2

    def test_schema_leaf_element(self):
        """Schema leaf elements get empty value."""
        class SchemaBuilder(BagBuilderBase):
            _schema = {
                'br': {'leaf': True},
            }

        bag = Bag(builder=SchemaBuilder())
        node = bag.br()

        assert node.value == ''
        assert node.tag == 'br'


class TestBuilderValidation:
    """Tests for attribute validation."""

    def test_validate_attrs_type_int(self):
        """Validates integer attributes."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'td': {
                    'attrs': {
                        'colspan': {'type': 'int', 'min': 1, 'max': 10},
                    }
                }
            }

        builder = ValidatingBuilder()

        # Valid
        errors = builder._validate_attrs('td', {'colspan': 5}, raise_on_error=False)
        assert errors == []

        # Too small
        errors = builder._validate_attrs('td', {'colspan': 0}, raise_on_error=False)
        assert len(errors) == 1
        assert 'must be >= 1' in errors[0]

        # Too large
        errors = builder._validate_attrs('td', {'colspan': 20}, raise_on_error=False)
        assert len(errors) == 1
        assert 'must be <= 10' in errors[0]

    def test_validate_attrs_type_enum(self):
        """Validates enum attributes."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'td': {
                    'attrs': {
                        'scope': {'type': 'enum', 'values': ['row', 'col']},
                    }
                }
            }

        builder = ValidatingBuilder()

        # Valid
        errors = builder._validate_attrs('td', {'scope': 'row'}, raise_on_error=False)
        assert errors == []

        # Invalid
        errors = builder._validate_attrs('td', {'scope': 'invalid'}, raise_on_error=False)
        assert len(errors) == 1
        assert 'must be one of' in errors[0]

    def test_validate_attrs_required(self):
        """Validates required attributes."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'img': {
                    'attrs': {
                        'src': {'type': 'string', 'required': True},
                    }
                }
            }

        builder = ValidatingBuilder()

        # Missing required
        errors = builder._validate_attrs('img', {}, raise_on_error=False)
        assert len(errors) == 1
        assert 'is required' in errors[0]


class TestBuilderReferences:
    """Tests for =reference resolution."""

    def test_resolve_simple_ref(self):
        """Resolves simple =ref references."""
        class RefBuilder(BagBuilderBase):
            @property
            def _ref_items(self):
                return 'apple, banana, cherry'

            _schema = {
                'menu': {'children': '=items'},
            }

        builder = RefBuilder()
        resolved = builder._resolve_ref('=items')
        assert resolved == 'apple, banana, cherry'

    def test_resolve_mixed_ref(self):
        """Resolves mixed refs and literals."""
        class RefBuilder(BagBuilderBase):
            @property
            def _ref_fruits(self):
                return 'apple, banana'

            _schema = {}

        builder = RefBuilder()
        resolved = builder._resolve_ref('=fruits, vegetable')
        assert 'apple' in resolved
        assert 'banana' in resolved
        assert 'vegetable' in resolved

    def test_resolve_ref_not_found(self):
        """Raises error for unknown reference."""
        class RefBuilder(BagBuilderBase):
            _schema = {}

        builder = RefBuilder()
        with pytest.raises(ValueError, match='Reference.*not found'):
            builder._resolve_ref('=unknown')
