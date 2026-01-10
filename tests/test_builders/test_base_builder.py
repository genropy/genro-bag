# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase and builder decorators."""

import pytest
from decimal import Decimal
from typing import Annotated, Literal

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element
from genro_bag.builders.validations import Range, Regex


class SimpleBuilder(BagBuilderBase):
    """Simple builder for testing."""

    @element(tags='item, product')
    def item(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(sub_tags='item[1:],product')  # At least 1 item, any number of product
    def container(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()
    def section(self, target, tag, **attr):
        return self.child(target, tag, **attr)


# =============================================================================
# Tests for BagBuilderBase functionality
# =============================================================================

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

    def test_builder_creates_node(self):
        """Builder creates nodes with tag."""
        bag = Bag(builder=SimpleBuilder)
        node = bag.item(name='test')

        assert node.tag == 'item'
        assert node.label == 'item_0'
        assert node.value is None
        assert node.attr.get('name') == 'test'

    def test_builder_creates_branch_node(self):
        """Builder creates branch nodes (returns BagNode, Bag created lazy)."""
        from genro_bag import BagNode

        bag = Bag(builder=SimpleBuilder)
        container_node = bag.container()

        # child() always returns BagNode
        assert isinstance(container_node, BagNode)
        assert container_node.tag == 'container'
        assert container_node.label == 'container_0'
        # No Bag yet (lazy creation)
        assert container_node.value is None

    def test_builder_lazy_bag_creation(self):
        """Bag is created lazily when children are added."""
        from genro_bag import BagNode

        bag = Bag(builder=SimpleBuilder)
        container_node = bag.container()

        # Add a child via the node - this triggers lazy Bag creation
        item_node = container_node.item()

        # Now the container has a Bag value
        assert isinstance(container_node.value, Bag)
        assert container_node.value.builder is bag.builder
        # The item is inside the container's Bag
        assert item_node.tag == 'item'

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
        assert len(bag['#0']) == 2


# =============================================================================
# Tests for element decorator with sub_tags validation
# =============================================================================

class TestBuilderSubTagsValidation:
    """Tests for sub_tags validation via @element decorator."""

    def test_element_with_sub_tags_spec(self):
        """@element sub_tags spec defines valid children."""
        class ContainerBuilder(BagBuilderBase):
            @element(sub_tags='span,p')
            def div(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def span(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def p(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=ContainerBuilder)
        div_node = bag.div()
        div_node.span()
        div_node.p()

        # div_node.value is the Bag containing children (created lazily)
        assert isinstance(div_node.value, Bag)
        assert len(div_node.value) == 2

    def test_element_leaf(self):
        """Leaf element creates node without children."""
        class LeafBuilder(BagBuilderBase):
            @element()
            def br(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=LeafBuilder)
        node = bag.br()

        assert node.value is None
        assert node.tag == 'br'


# =============================================================================
# Tests for attribute validation via @element decorator
# =============================================================================

class TestBuilderValidation:
    """Tests for attribute validation via @element decorator."""

    def test_element_validates_int_range(self):
        """@element validates int range via Annotated."""
        class ValidatingBuilder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return self.child(target, tag, colspan=colspan, **attr)

        bag = Bag(builder=ValidatingBuilder)

        # Valid
        bag.td(colspan=5)

        # Too small
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.td(colspan=0)

        # Too large
        with pytest.raises(ValueError, match='must be <= 10'):
            bag.td(colspan=20)

    def test_element_validates_enum_values(self):
        """@element validates enum values via Literal."""
        class ValidatingBuilder(BagBuilderBase):
            @element()
            def td(self, target, tag, scope: Literal['row', 'col'] = None, **attr):
                return self.child(target, tag, scope=scope, **attr)

        bag = Bag(builder=ValidatingBuilder)

        # Valid
        bag.td(scope='row')

        # Invalid
        with pytest.raises(ValueError, match='expected'):
            bag.td(scope='invalid')


# =============================================================================
# Tests for Annotated validation constraints
# =============================================================================

class TestAnnotatedConstraintsValidation:
    """Tests for validation via Annotated constraints in @element."""

    def test_element_validates_multiple_constraints(self):
        """@element validates multiple constraints on same parameter."""
        class ConstraintBuilder(BagBuilderBase):
            @element()
            def td(self, target, tag,
                   colspan: Annotated[int, Range(ge=1, le=10)] = None,
                   scope: Literal['row', 'col'] = None,
                   **attr):
                return self.child(target, tag, colspan=colspan, scope=scope, **attr)

        bag = Bag(builder=ConstraintBuilder)

        # Valid call
        bag.td(colspan=5, scope='row')

        # Invalid colspan
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.td(colspan=0)

        # Invalid scope
        with pytest.raises(ValueError, match='expected'):
            bag.td(scope='invalid')

    def test_element_validates_pattern(self):
        """@element validates pattern constraint via Annotated."""
        class PatternBuilder(BagBuilderBase):
            @element()
            def email(self, target, tag,
                      address: Annotated[str, Regex(r'^[\w\.-]+@[\w\.-]+\.\w+$')] = None,
                      **attr):
                return self.child(target, tag, address=address, **attr)

        bag = Bag(builder=PatternBuilder)

        # Valid
        bag.email(address='test@example.com')

        # Invalid
        with pytest.raises(ValueError, match='must match pattern'):
            bag.email(address='not-an-email')


# =============================================================================
# Tests for =reference resolution in sub_tags spec
# =============================================================================

class TestBuilderReferences:
    """Tests for =reference resolution in @element sub_tags spec."""

    def test_ref_in_sub_tags_spec(self):
        """References in sub_tags spec are resolved correctly."""
        class RefBuilder(BagBuilderBase):
            @property
            def _ref_items(self):
                return 'apple,banana'

            @element(sub_tags='=items')
            def menu(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def apple(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def banana(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=RefBuilder)
        menu = bag.menu()
        # These should work because =items resolves to 'apple, banana'
        menu.apple()
        menu.banana()

        # Verify structure
        assert len(menu.value) == 2


# =============================================================================
# Tests for @element decorator
# =============================================================================

class TestElementDecorator:
    """Tests for @element decorator."""

    def test_single_tag(self):
        """Element with no tags uses method name as tag."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        bag.item()
        assert bag.get_node('item_0').tag == 'item'

    def test_multiple_tags(self):
        """Element can handle multiple tags."""
        class Builder(BagBuilderBase):
            @element(tags='apple, banana, cherry')
            def fruit(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        bag.apple()
        bag.banana()
        bag.cherry()

        assert bag.get_node('apple_0').tag == 'apple'
        assert bag.get_node('banana_0').tag == 'banana'
        assert bag.get_node('cherry_0').tag == 'cherry'


# =============================================================================
# Integration tests for @element with Bag
# =============================================================================

class TestElementDecoratorIntegration:
    """Integration tests for @element with Bag."""

    def test_leaf_element(self):
        """Leaf element creates node."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        node = bag.item(name='test')

        assert node.value is None
        assert node.tag == 'item'

    def test_branch_element(self):
        """Branch element returns BagNode, Bag created lazily."""
        from genro_bag import BagNode

        class Builder(BagBuilderBase):
            @element(sub_tags='item')
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        container_node = bag.container()

        # child() always returns BagNode
        assert isinstance(container_node, BagNode)
        assert container_node.tag == 'container'
        # No Bag yet (lazy creation)
        assert container_node.value is None

        # Add child triggers lazy Bag creation
        container_node.item()
        assert isinstance(container_node.value, Bag)
        assert container_node.value.builder is bag.builder


# =============================================================================
# Tests for validation with Annotated constraints
# =============================================================================

class TestAnnotatedValidation:
    """Tests for validation with Annotated constraints."""

    def test_pattern_valid(self):
        """Pattern constraint accepts valid value."""
        Email = Annotated[str, Regex(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, email: Email = None, **attr):
                return self.child(target, tag, email=email, **attr)

        bag = Bag(builder=Builder)
        bag.contact(email='test@example.com')

    def test_pattern_invalid(self):
        """Pattern constraint rejects invalid value."""
        Email = Annotated[str, Regex(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, email: Email = None, **attr):
                return self.child(target, tag, email=email, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must match pattern'):
            bag.contact(email='not-an-email')

    def test_range_valid(self):
        """Range constraints accept valid value."""
        Peso = Annotated[int, Range(ge=1, le=13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, peso=peso, **attr)

        bag = Bag(builder=Builder)
        bag.item(peso=5)

    def test_range_min_invalid(self):
        """Range constraint rejects value below minimum."""
        Peso = Annotated[int, Range(ge=1, le=13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, peso=peso, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.item(peso=0)

    def test_range_max_invalid(self):
        """Range constraint rejects value above maximum."""
        Peso = Annotated[int, Range(ge=1, le=13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, peso=peso, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be <= 13'):
            bag.item(peso=20)

    def test_decimal_range(self):
        """Decimal type with Range constraints."""
        Amount = Annotated[Decimal, Range(ge=0, le=1000)]

        class Builder(BagBuilderBase):
            @element()
            def payment(self, target, tag, amount: Amount = None, **attr):
                return self.child(target, tag, amount=amount, **attr)

        bag = Bag(builder=Builder)
        bag.payment(amount=Decimal('500.50'))

        with pytest.raises(ValueError, match='must be >= 0'):
            bag.payment(amount=Decimal('-1'))

        with pytest.raises(ValueError, match='must be <= 1000'):
            bag.payment(amount=Decimal('1001'))
