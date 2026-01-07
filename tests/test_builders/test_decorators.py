# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for builder decorators."""

import pytest
from decimal import Decimal
from typing import Annotated, Literal

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders.decorators import element
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


class TestElementDecorator:
    """Tests for @element decorator."""

    def test_single_tag(self):
        """Registers method for single tag."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        assert 'item' in Builder._element_tags
        assert Builder._element_tags['item'] == 'item'

    def test_multiple_tags(self):
        """Registers method for multiple tags."""
        class Builder(BagBuilderBase):
            @element(tags='apple, banana, cherry')
            def fruit(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        assert 'apple' in Builder._element_tags
        assert 'banana' in Builder._element_tags
        assert 'cherry' in Builder._element_tags
        assert Builder._element_tags['apple'] == 'fruit'

    def test_children_spec(self):
        """Stores children validation spec."""
        class Builder(BagBuilderBase):
            @element(children='item[1:], header[:1]')
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        method = Builder.container
        assert 'item' in method._valid_children
        assert 'header' in method._valid_children
        assert method._child_cardinality['item'] == (1, None)
        assert method._child_cardinality['header'] == (0, 1)

    def test_attr_validation_from_signature(self):
        """Validates attributes from type hints."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: int = 1,
                   scope: Literal['row', 'col'] | None = None, **attr):
                return self.child(target, tag, colspan=colspan, scope=scope, **attr)

        bag = Bag(builder=Builder())

        # Valid call
        bag.td(colspan=2, scope='row')

        # Invalid scope should raise
        with pytest.raises(ValueError, match='must be one of'):
            bag.td(scope='invalid')

    def test_validate_false_skips_validation(self):
        """validate=False disables attribute validation."""
        class Builder(BagBuilderBase):
            @element(validate=False)
            def td(self, target, tag, colspan: int = 1, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder())
        # This should not raise even with invalid type
        bag.td(colspan='not-an-int')


class TestElementDecoratorIntegration:
    """Integration tests for @element with Bag."""

    def test_leaf_element(self):
        """Leaf element creates node with value."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, value='', **attr)

        bag = Bag(builder=Builder())
        node = bag.item(name='test')

        assert node.value == ''
        assert node.tag == 'item'

    def test_branch_element(self):
        """Branch element creates nested Bag."""
        class Builder(BagBuilderBase):
            @element()
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder())
        container = bag.container()

        assert isinstance(container, Bag)
        assert container.builder is bag.builder


class TestAnnotatedValidation:
    """Tests for validation with Annotated constraints."""

    def test_pattern_valid(self):
        """Pattern constraint accepts valid value."""
        Email = Annotated[str, Pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, email: Email = None, **attr):
                return self.child(target, tag, value='', email=email, **attr)

        bag = Bag(builder=Builder())
        bag.contact(email='test@example.com')

    def test_pattern_invalid(self):
        """Pattern constraint rejects invalid value."""
        Email = Annotated[str, Pattern(r'^[\w\.-]+@[\w\.-]+\.\w+$')]

        class Builder(BagBuilderBase):
            @element()
            def contact(self, target, tag, email: Email = None, **attr):
                return self.child(target, tag, value='', email=email, **attr)

        bag = Bag(builder=Builder())
        with pytest.raises(ValueError, match='must match pattern'):
            bag.contact(email='not-an-email')

    def test_min_max_valid(self):
        """Min/Max constraints accept valid value."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, value='', peso=peso, **attr)

        bag = Bag(builder=Builder())
        bag.item(peso=5)

    def test_min_invalid(self):
        """Min constraint rejects value below minimum."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, value='', peso=peso, **attr)

        bag = Bag(builder=Builder())
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.item(peso=0)

    def test_max_invalid(self):
        """Max constraint rejects value above maximum."""
        Peso = Annotated[int, Min(1), Max(13)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, peso: Peso = None, **attr):
                return self.child(target, tag, value='', peso=peso, **attr)

        bag = Bag(builder=Builder())
        with pytest.raises(ValueError, match='must be <= 13'):
            bag.item(peso=20)

    def test_min_length_valid(self):
        """MinLength constraint accepts valid value."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, code: Code = None, **attr):
                return self.child(target, tag, value='', code=code, **attr)

        bag = Bag(builder=Builder())
        bag.item(code='ABC123')

    def test_min_length_invalid(self):
        """MinLength constraint rejects value too short."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, code: Code = None, **attr):
                return self.child(target, tag, value='', code=code, **attr)

        bag = Bag(builder=Builder())
        with pytest.raises(ValueError, match='at least 3 characters'):
            bag.item(code='AB')

    def test_max_length_invalid(self):
        """MaxLength constraint rejects value too long."""
        Code = Annotated[str, MinLength(3), MaxLength(10)]

        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, code: Code = None, **attr):
                return self.child(target, tag, value='', code=code, **attr)

        bag = Bag(builder=Builder())
        with pytest.raises(ValueError, match='at most 10 characters'):
            bag.item(code='ABCDEFGHIJK')

    def test_decimal_min_max(self):
        """Decimal type with Min/Max constraints."""
        Amount = Annotated[Decimal, Min(0), Max(1000)]

        class Builder(BagBuilderBase):
            @element()
            def payment(self, target, tag, amount: Amount = None, **attr):
                return self.child(target, tag, value='', amount=amount, **attr)

        bag = Bag(builder=Builder())
        bag.payment(amount=Decimal('500.50'))

        with pytest.raises(ValueError, match='must be >= 0'):
            bag.payment(amount=Decimal('-1'))

        with pytest.raises(ValueError, match='must be <= 1000'):
            bag.payment(amount=Decimal('1001'))
