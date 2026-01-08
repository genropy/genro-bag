# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase and builder decorators."""

import pytest
from decimal import Decimal
from typing import Annotated, Literal

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element
from genro_bag.builders.validations import (
    annotation_to_attr_spec,
    extract_attrs_from_signature,
    parse_tag_spec,
    Max,
    MaxLength,
    Min,
    MinLength,
    Pattern,
)


class SimpleBuilder(BagBuilderBase):
    """Simple builder for testing."""

    @element(tags='item, product')
    def item(self, target, tag, value=None, node_label=None, **attr):
        return self.child(target, tag, **attr, _label=node_label, value=value or '')

    @element(children='item[1:]')
    def container(self, target, tag, value=None, node_label=None, **attr):
        return self.child(target, tag, **attr, _label=node_label, value=value)

    @element()
    def section(self, target, tag, value=None, node_label=None, **attr):
        return self.child(target, tag, **attr, _label=node_label, value=value)


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


# =============================================================================
# Tests for _schema-based builders
# =============================================================================

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


# =============================================================================
# Tests for attribute validation via public API
# =============================================================================

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


# =============================================================================
# Tests for validation via _schema in _make_schema_handler
# =============================================================================

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


# =============================================================================
# Tests for =reference resolution via public API
# =============================================================================

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


# =============================================================================
# Tests for parse_tag_spec function
# =============================================================================

class TestParseTagSpec:
    """Tests for parse_tag_spec function."""

    def test_simple_tag(self):
        """Parses simple tag name."""
        tag, min_c, max_c = parse_tag_spec('foo')
        assert tag == 'foo'
        assert min_c == 0
        assert max_c is None

    def test_exact_count(self):
        """Parses exact count [n]."""
        tag, min_c, max_c = parse_tag_spec('foo[2]')
        assert tag == 'foo'
        assert min_c == 2
        assert max_c == 2

    def test_min_only(self):
        """Parses min only [n:]."""
        tag, min_c, max_c = parse_tag_spec('foo[3:]')
        assert tag == 'foo'
        assert min_c == 3
        assert max_c is None

    def test_max_only(self):
        """Parses max only [:m]."""
        tag, min_c, max_c = parse_tag_spec('foo[:5]')
        assert tag == 'foo'
        assert min_c == 0
        assert max_c == 5

    def test_range(self):
        """Parses range [n:m]."""
        tag, min_c, max_c = parse_tag_spec('foo[2:5]')
        assert tag == 'foo'
        assert min_c == 2
        assert max_c == 5

    def test_whitespace(self):
        """Handles whitespace around tag."""
        tag, min_c, max_c = parse_tag_spec('  foo  [2:5]  ')
        assert tag == 'foo'

    def test_invalid_spec(self):
        """Raises error for invalid spec."""
        with pytest.raises(ValueError, match='Invalid tag specification'):
            parse_tag_spec('123invalid')


# =============================================================================
# Tests for annotation_to_attr_spec function
# =============================================================================

class TestAnnotationToAttrSpec:
    """Tests for annotation_to_attr_spec function."""

    def test_int_type(self):
        """Converts int annotation."""
        spec = annotation_to_attr_spec(int)
        assert spec == {'type': 'int'}

    def test_str_type(self):
        """Converts str annotation."""
        spec = annotation_to_attr_spec(str)
        assert spec == {'type': 'string'}

    def test_bool_type(self):
        """Converts bool annotation."""
        spec = annotation_to_attr_spec(bool)
        assert spec == {'type': 'bool'}

    def test_literal_type(self):
        """Converts Literal annotation."""
        spec = annotation_to_attr_spec(Literal['a', 'b', 'c'])
        assert spec == {'type': 'enum', 'values': ['a', 'b', 'c']}

    def test_optional_int(self):
        """Converts Optional[int] annotation."""
        from typing import Optional
        spec = annotation_to_attr_spec(Optional[int])
        assert spec == {'type': 'int'}

    def test_annotated_with_pattern(self):
        """Converts Annotated with Pattern constraint."""
        Email = Annotated[str, Pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')]
        spec = annotation_to_attr_spec(Email)
        assert spec['type'] == 'string'
        assert spec['pattern'] == r'^[\w\.-]+@[\w\.-]+\.\w+$'

    def test_annotated_with_min_max(self):
        """Converts Annotated with Min/Max constraints."""
        Peso = Annotated[int, Min(1), Max(13)]
        spec = annotation_to_attr_spec(Peso)
        assert spec['type'] == 'int'
        assert spec['min'] == 1
        assert spec['max'] == 13

    def test_annotated_with_length(self):
        """Converts Annotated with MinLength/MaxLength constraints."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]
        spec = annotation_to_attr_spec(Code)
        assert spec['type'] == 'string'
        assert spec['minLength'] == 3
        assert spec['maxLength'] == 10

    def test_annotated_decimal(self):
        """Converts Annotated Decimal with constraints."""
        Amount = Annotated[Decimal, Min(0), Max(1000)]
        spec = annotation_to_attr_spec(Amount)
        assert spec['type'] == 'decimal'
        assert spec['min'] == 0
        assert spec['max'] == 1000


# =============================================================================
# Tests for extract_attrs_from_signature function
# =============================================================================

class TestExtractAttrsFromSignature:
    """Tests for extract_attrs_from_signature function."""

    def test_typed_params(self):
        """Extracts typed parameters."""
        def func(self, target, tag, colspan: int = 1, scope: Literal['row', 'col'] = None):
            pass

        spec = extract_attrs_from_signature(func)
        assert 'colspan' in spec
        assert spec['colspan']['type'] == 'int'
        assert spec['colspan']['default'] == 1
        assert 'scope' in spec
        assert spec['scope']['type'] == 'enum'

    def test_skips_special_params(self):
        """Skips self, target, tag, label, value."""
        def func(self, target, tag, label, value, custom: str = 'x'):
            pass

        spec = extract_attrs_from_signature(func)
        assert 'self' not in spec
        assert 'target' not in spec
        assert 'tag' not in spec
        assert 'label' not in spec
        assert 'value' not in spec
        assert 'custom' in spec

    def test_required_param(self):
        """Marks params without default as required."""
        def func(self, target, tag, required_param: str):
            pass

        spec = extract_attrs_from_signature(func)
        assert spec['required_param']['required'] is True


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

    def test_children_spec_validation(self):
        """Children spec is validated via check()."""
        class Builder(BagBuilderBase):
            @element(children='item[1:], header[:1]')
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def item(self, target, tag, value=None, node_label=None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '')

            @element()
            def header(self, target, tag, value=None, node_label=None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '')

        bag = Bag(builder=Builder)
        container = bag.container()

        # Empty container - missing required item
        errors = bag.builder.check(container, parent_tag='container')
        assert len(errors) == 1
        assert 'requires at least 1' in errors[0]

        # Add required item
        container.item()
        errors = bag.builder.check(container, parent_tag='container')
        assert errors == []

        # Add optional header (max 1)
        container.header()
        errors = bag.builder.check(container, parent_tag='container')
        assert errors == []

        # Add second header (exceeds max)
        container.header()
        errors = bag.builder.check(container, parent_tag='container')
        assert len(errors) == 1
        assert 'allows at most 1' in errors[0]

    def test_attr_validation_from_signature(self):
        """Validates attributes from type hints."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: int = 1,
                   scope: Literal['row', 'col'] | None = None, **attr):
                return self.child(target, tag, colspan=colspan, scope=scope, **attr)

        bag = Bag(builder=Builder)

        # Valid call
        bag.td(colspan=2, scope='row')

        # Invalid scope should raise
        with pytest.raises(ValueError, match='must be one of'):
            bag.td(scope='invalid')


# =============================================================================
# Integration tests for @element with Bag
# =============================================================================

class TestElementDecoratorIntegration:
    """Integration tests for @element with Bag."""

    def test_leaf_element(self):
        """Leaf element creates node with value."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '')

        bag = Bag(builder=Builder)
        node = bag.item(name='test')

        assert node.value == ''
        assert node.tag == 'item'

    def test_branch_element(self):
        """Branch element creates nested Bag."""
        class Builder(BagBuilderBase):
            @element()
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        container = bag.container()

        assert isinstance(container, Bag)
        assert container.builder is bag.builder


# =============================================================================
# Tests for validation with Annotated constraints
# =============================================================================

class TestAnnotatedValidation:
    """Tests for validation with Annotated constraints."""

    def test_pattern_valid(self):
        """Pattern constraint accepts valid value."""
        Email = Annotated[str, Pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, value=None, node_label=None, email: Email = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', email=email)

        bag = Bag(builder=Builder)
        bag.contact(email='test@example.com')

    def test_pattern_invalid(self):
        """Pattern constraint rejects invalid value."""
        Email = Annotated[str, Pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, value=None, node_label=None, email: Email = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', email=email)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must match pattern'):
            bag.contact(email='not-an-email')

    def test_min_max_valid(self):
        """Min/Max constraints accept valid value."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, peso: Peso = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', peso=peso)

        bag = Bag(builder=Builder)
        bag.item(peso=5)

    def test_min_invalid(self):
        """Min constraint rejects value below minimum."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, peso: Peso = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', peso=peso)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.item(peso=0)

    def test_max_invalid(self):
        """Max constraint rejects value above maximum."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, peso: Peso = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', peso=peso)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be <= 13'):
            bag.item(peso=20)

    def test_min_length_valid(self):
        """MinLength constraint accepts valid value."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, code: Code = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', code=code)

        bag = Bag(builder=Builder)
        bag.item(code='ABC123')

    def test_min_length_invalid(self):
        """MinLength constraint rejects value too short."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, code: Code = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', code=code)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='at least 3 characters'):
            bag.item(code='AB')

    def test_max_length_invalid(self):
        """MaxLength constraint rejects value too long."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, value=None, node_label=None, code: Code = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', code=code)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='at most 10 characters'):
            bag.item(code='ABCDEFGHIJK')

    def test_decimal_min_max(self):
        """Decimal type with Min/Max constraints."""
        Amount = Annotated[Decimal, Min(0), Max(1000)]

        class Builder(BagBuilderBase):
            @element()
            def payment(self, target, tag, value=None, node_label=None, amount: Amount = None, **attr):
                return self.child(target, tag, **attr, _label=node_label, value=value or '', amount=amount)

        bag = Bag(builder=Builder)
        bag.payment(amount=Decimal('500.50'))

        with pytest.raises(ValueError, match='must be >= 0'):
            bag.payment(amount=Decimal('-1'))

        with pytest.raises(ValueError, match='must be <= 1000'):
            bag.payment(amount=Decimal('1001'))
