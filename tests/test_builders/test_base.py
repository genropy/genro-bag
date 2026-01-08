# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase."""

import pytest

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element


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
        """Bag can be created with a builder class."""
        bag = Bag(builder=SimpleBuilder)
        assert isinstance(bag.builder, SimpleBuilder)

    def test_bag_without_builder(self):
        """Bag without builder works normally."""
        bag = Bag()
        assert bag.builder is None
        bag['test'] = 'value'
        assert bag['test'] == 'value'

    def test_builder_creates_leaf_node(self):
        """Builder creates leaf nodes with tag."""
        bag = Bag(builder=SimpleBuilder)
        node = bag.item(name='test')

        assert node.tag == 'item'
        assert node.label == 'item_0'
        assert node.value == ''
        assert node.attr.get('name') == 'test'

    def test_builder_creates_branch_node(self):
        """Builder creates branch nodes (returns Bag)."""
        bag = Bag(builder=SimpleBuilder)
        container = bag.container()

        assert isinstance(container, Bag)
        # Check the node was created in parent
        node = bag.get_node('container_0')
        assert node.tag == 'container'

    def test_builder_inheritance(self):
        """Child bags inherit builder from parent."""
        bag = Bag(builder=SimpleBuilder)
        container = bag.container()

        assert container.builder is bag.builder

    def test_builder_auto_label_generation(self):
        """Builder auto-generates unique labels."""
        bag = Bag(builder=SimpleBuilder)
        bag.item()
        bag.item()
        bag.item()

        labels = list(bag.keys())
        assert labels == ['item_0', 'item_1', 'item_2']

    def test_builder_multi_tag_method(self):
        """Single method handles multiple tags."""
        bag = Bag(builder=SimpleBuilder)
        bag.item()
        bag.product()

        node1 = bag.get_node('item_0')
        node2 = bag.get_node('product_0')

        assert node1.tag == 'item'
        assert node2.tag == 'product'

    def test_builder_fluent_api(self):
        """Builder enables fluent API."""
        bag = Bag(builder=SimpleBuilder)
        container = bag.container()
        container.item(name='first')
        container.item(name='second')

        assert len(bag) == 1
        assert len(container) == 2

    def test_builder_check_valid_structure(self):
        """check() returns empty list for valid structure."""
        bag = Bag(builder=SimpleBuilder)
        container = bag.container()
        container.item()
        container.item()

        node = bag.get_node('container_0')
        errors = bag.builder.check(container, parent_tag='container')
        assert errors == []

    def test_builder_check_missing_required_children(self):
        """check() reports missing required children."""
        bag = Bag(builder=SimpleBuilder)
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

        bag = Bag(builder=SchemaBuilder)
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

        bag = Bag(builder=SchemaBuilder)
        node = bag.br()

        assert node.value == ''
        assert node.tag == 'br'


class TestBuilderValidation:
    """Tests for attribute validation via public API."""

    def test_schema_validates_int_range(self):
        """Schema validates int min/max when element is called."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'td': {
                    'attrs': {
                        'colspan': {'type': 'int', 'min': 1, 'max': 10},
                    }
                }
            }

        bag = Bag(builder=ValidatingBuilder)

        # Valid
        bag.td(colspan=5)

        # Too small
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.td(colspan=0)

        # Too large
        with pytest.raises(ValueError, match='must be <= 10'):
            bag.td(colspan=20)

    def test_schema_validates_enum_values(self):
        """Schema validates enum values when element is called."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'td': {
                    'attrs': {
                        'scope': {'type': 'enum', 'values': ['row', 'col']},
                    }
                }
            }

        bag = Bag(builder=ValidatingBuilder)

        # Valid
        bag.td(scope='row')

        # Invalid
        with pytest.raises(ValueError, match='must be one of'):
            bag.td(scope='invalid')

    def test_schema_validates_required_attrs(self):
        """Schema validates required attrs when element is called."""
        class ValidatingBuilder(BagBuilderBase):
            _schema = {
                'img': {
                    'attrs': {
                        'src': {'type': 'string', 'required': True},
                    }
                }
            }

        bag = Bag(builder=ValidatingBuilder)

        # Missing required
        with pytest.raises(ValueError, match='is required'):
            bag.img()


class TestSchemaValidation:
    """Tests for validation via _schema in _make_schema_handler."""

    def test_schema_validates_attrs_on_call(self):
        """Schema-defined elements validate attrs when called."""
        class SchemaBuilder(BagBuilderBase):
            _schema = {
                'td': {
                    'attrs': {
                        'colspan': {'type': 'int', 'min': 1, 'max': 10},
                        'scope': {'type': 'enum', 'values': ['row', 'col']},
                    }
                }
            }

        bag = Bag(builder=SchemaBuilder)

        # Valid call
        bag.td(colspan=5, scope='row')

        # Invalid colspan
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.td(colspan=0)

        # Invalid scope
        with pytest.raises(ValueError, match='must be one of'):
            bag.td(scope='invalid')

    def test_schema_validates_pattern(self):
        """Schema validates pattern constraint."""
        class SchemaBuilder(BagBuilderBase):
            _schema = {
                'email': {
                    'leaf': True,
                    'attrs': {
                        'address': {'type': 'string', 'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
                    }
                }
            }

        bag = Bag(builder=SchemaBuilder)

        # Valid
        bag.email(address='test@example.com')

        # Invalid
        with pytest.raises(ValueError, match='must match pattern'):
            bag.email(address='not-an-email')

    def test_schema_validates_length(self):
        """Schema validates minLength/maxLength constraints."""
        class SchemaBuilder(BagBuilderBase):
            _schema = {
                'code': {
                    'leaf': True,
                    'attrs': {
                        'code': {'type': 'string', 'minLength': 3, 'maxLength': 10},
                    }
                }
            }

        bag = Bag(builder=SchemaBuilder)

        # Valid
        bag.code(code='ABC123')

        # Too short
        with pytest.raises(ValueError, match='at least 3 characters'):
            bag.code(code='AB')

        # Too long
        with pytest.raises(ValueError, match='at most 10 characters'):
            bag.code(code='ABCDEFGHIJK')


class TestBuilderReferences:
    """Tests for =reference resolution via public API."""

    def test_ref_in_children_spec(self):
        """References in children spec are resolved correctly."""
        class RefBuilder(BagBuilderBase):
            @property
            def _ref_items(self):
                return 'apple, banana'

            _schema = {
                'menu': {'children': '=items'},
                'apple': {'leaf': True},
                'banana': {'leaf': True},
            }

        bag = Bag(builder=RefBuilder)
        menu = bag.menu()
        # These should work because =items resolves to 'apple, banana'
        menu.apple()
        menu.banana()

        # Verify structure
        assert len(menu) == 2

    def test_ref_with_invalid_child_raises(self):
        """Invalid child under referenced parent raises error."""
        class RefBuilder(BagBuilderBase):
            @property
            def _ref_items(self):
                return 'apple, banana'

            _schema = {
                'menu': {'children': '=items'},
                'apple': {'leaf': True},
                'banana': {'leaf': True},
                'cherry': {'leaf': True},
            }

        bag = Bag(builder=RefBuilder)
        menu = bag.menu()
        # cherry is not in =items, should raise ValueError
        with pytest.raises(ValueError, match="'cherry' is not a valid child"):
            menu.cherry()
