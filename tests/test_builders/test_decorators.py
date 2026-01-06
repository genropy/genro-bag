# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for builder decorators."""

import pytest
from typing import Literal

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders.decorators import (
    element,
    _parse_tag_spec,
    _extract_attrs_from_signature,
    _annotation_to_attr_spec,
)


class TestParseTagSpec:
    """Tests for _parse_tag_spec function."""

    def test_simple_tag(self):
        """Parses simple tag name."""
        tag, min_c, max_c = _parse_tag_spec('foo')
        assert tag == 'foo'
        assert min_c == 0
        assert max_c is None

    def test_exact_count(self):
        """Parses exact count [n]."""
        tag, min_c, max_c = _parse_tag_spec('foo[2]')
        assert tag == 'foo'
        assert min_c == 2
        assert max_c == 2

    def test_min_only(self):
        """Parses min only [n:]."""
        tag, min_c, max_c = _parse_tag_spec('foo[3:]')
        assert tag == 'foo'
        assert min_c == 3
        assert max_c is None

    def test_max_only(self):
        """Parses max only [:m]."""
        tag, min_c, max_c = _parse_tag_spec('foo[:5]')
        assert tag == 'foo'
        assert min_c == 0
        assert max_c == 5

    def test_range(self):
        """Parses range [n:m]."""
        tag, min_c, max_c = _parse_tag_spec('foo[2:5]')
        assert tag == 'foo'
        assert min_c == 2
        assert max_c == 5

    def test_whitespace(self):
        """Handles whitespace around tag."""
        tag, min_c, max_c = _parse_tag_spec('  foo  [2:5]  ')
        assert tag == 'foo'

    def test_invalid_spec(self):
        """Raises error for invalid spec."""
        with pytest.raises(ValueError, match='Invalid tag specification'):
            _parse_tag_spec('123invalid')


class TestAnnotationToAttrSpec:
    """Tests for _annotation_to_attr_spec function."""

    def test_int_type(self):
        """Converts int annotation."""
        spec = _annotation_to_attr_spec(int)
        assert spec == {'type': 'int'}

    def test_str_type(self):
        """Converts str annotation."""
        spec = _annotation_to_attr_spec(str)
        assert spec == {'type': 'string'}

    def test_bool_type(self):
        """Converts bool annotation."""
        spec = _annotation_to_attr_spec(bool)
        assert spec == {'type': 'bool'}

    def test_literal_type(self):
        """Converts Literal annotation."""
        spec = _annotation_to_attr_spec(Literal['a', 'b', 'c'])
        assert spec == {'type': 'enum', 'values': ['a', 'b', 'c']}

    def test_optional_int(self):
        """Converts Optional[int] annotation."""
        from typing import Optional
        spec = _annotation_to_attr_spec(Optional[int])
        assert spec == {'type': 'int'}


class TestExtractAttrsFromSignature:
    """Tests for _extract_attrs_from_signature function."""

    def test_typed_params(self):
        """Extracts typed parameters."""
        def func(self, target, tag, colspan: int = 1, scope: Literal['row', 'col'] = None):
            pass

        spec = _extract_attrs_from_signature(func)
        assert 'colspan' in spec
        assert spec['colspan']['type'] == 'int'
        assert spec['colspan']['default'] == 1
        assert 'scope' in spec
        assert spec['scope']['type'] == 'enum'

    def test_skips_special_params(self):
        """Skips self, target, tag, label, value."""
        def func(self, target, tag, label, value, custom: str = 'x'):
            pass

        spec = _extract_attrs_from_signature(func)
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

        spec = _extract_attrs_from_signature(func)
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
