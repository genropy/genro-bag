# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase and builder decorators.

Tests cover:
- @element decorator with various configurations
- @abstract decorator for inheritance bases
- Ellipsis body detection (handler_name=None vs handler_name='_el_name')
- Schema structure with @ prefix for abstracts
- Inheritance resolution via inherits_from
- Attribute validation via Annotated constraints
"""

import pytest
from decimal import Decimal
from typing import Annotated, Literal

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element, abstract, Range, Regex


# =============================================================================
# Tests for @element decorator - handler detection
# =============================================================================

class TestElementDecoratorHandlerDetection:
    """Tests for @element decorator handler detection."""

    def test_ellipsis_body_sets_handler_name_none(self):
        """@element with ... body sets handler_name=None in schema."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Schema should have handler_name=None
        node = Builder._class_schema.get_node('item')
        assert node is not None
        assert node.attr.get('handler_name') is None

    def test_real_body_sets_handler_name(self):
        """@element with real body sets handler_name='_el_name' in schema."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                attr.setdefault('custom', 'value')
                return self.child(target, tag, **attr)

        # Schema should have handler_name='_el_item'
        node = Builder._class_schema.get_node('item')
        assert node is not None
        assert node.attr.get('handler_name') == '_el_item'
        # Method should be renamed
        assert hasattr(Builder, '_el_item')
        assert not hasattr(Builder, 'item')

    def test_ellipsis_method_removed_from_class(self):
        """@element with ... body removes method from class."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Method should be removed (no _el_item either)
        assert not hasattr(Builder, 'item')
        assert not hasattr(Builder, '_el_item')

    def test_ellipsis_inline_with_params(self):
        """@element with inline ... and parameters sets handler_name=None."""
        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None): ...

        node = Builder._class_schema.get_node('alfa')
        assert node is not None
        assert node.attr.get('handler_name') is None

    def test_ellipsis_newline_with_params(self):
        """@element with ... on separate line sets handler_name=None."""
        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None):
                ...

        node = Builder._class_schema.get_node('alfa')
        assert node is not None
        assert node.attr.get('handler_name') is None

    def test_ellipsis_with_docstring_and_params(self):
        """@element with docstring and ... sets handler_name=None."""
        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None):
                "this is my method"
                ...

        node = Builder._class_schema.get_node('alfa')
        assert node is not None
        assert node.attr.get('handler_name') is None


# =============================================================================
# Tests for @abstract decorator
# =============================================================================

class TestAbstractDecorator:
    """Tests for @abstract decorator."""

    def test_abstract_creates_at_prefixed_entry(self):
        """@abstract creates @name entry in schema."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='span,p')
            def flow(self): ...

        # Schema should have @flow
        node = Builder._class_schema.get_node('@flow')
        assert node is not None
        assert node.attr.get('sub_tags') == 'span,p'

    def test_abstract_method_removed_from_class(self):
        """@abstract removes method from class."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='span,p')
            def flow(self): ...

        assert not hasattr(Builder, 'flow')
        assert not hasattr(Builder, '_el_flow')

    def test_iteration_returns_all_nodes(self):
        """Iteration returns all schema nodes including abstracts."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='span,p')
            def flow(self): ...

            @element()
            def div(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        labels = [node.label for node in bag.builder]
        assert 'div' in labels
        assert 'span' in labels
        assert '@flow' in labels

    def test_abstract_not_in_contains(self):
        """Abstract elements work with 'in' operator."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='span,p')
            def flow(self): ...

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        assert 'div' in bag.builder
        assert '@flow' in bag.builder  # Abstracts are in schema


# =============================================================================
# Tests for inherits_from
# =============================================================================

class TestInheritsFrom:
    """Tests for inherits_from inheritance resolution."""

    def test_element_inherits_sub_tags_from_abstract(self):
        """Element inherits sub_tags from abstract via inherits_from."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='span,p,a')
            def phrasing(self): ...

            @element(inherits_from='@phrasing')
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def p(self): ...

            @element()
            def a(self): ...

        bag = Bag(builder=Builder)
        handler, sub_tags, _ = bag.builder.get_schema_info('div')
        assert sub_tags == 'span,p,a'

    def test_element_can_override_inherited_attrs(self):
        """Element attrs override inherited attrs from abstract."""
        class Builder(BagBuilderBase):
            @abstract(sub_tags='a,b,c', sub_tags_order='a>b>c')
            def base(self): ...

            @element(inherits_from='@base', sub_tags_order='c>b>a')
            def custom(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element()
            def c(self): ...

        bag = Bag(builder=Builder)
        handler, sub_tags, _ = bag.builder.get_schema_info('custom')
        # sub_tags inherited, sub_tags_order overridden
        assert sub_tags == 'a,b,c'


# =============================================================================
# Tests for @element decorator - tags parameter
# =============================================================================

class TestElementDecoratorTags:
    """Tests for @element decorator tags parameter."""

    def test_no_tags_uses_method_name(self):
        """@element with no tags uses method name as tag."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        assert Builder._class_schema.get_node('item') is not None

    def test_single_tag_string_adds_to_method_name(self):
        """@element with tags adds them to method name."""
        class Builder(BagBuilderBase):
            @element(tags='product')
            def item(self): ...

        # Both method name and tags are registered
        assert Builder._class_schema.get_node('item') is not None
        assert Builder._class_schema.get_node('product') is not None

    def test_underscore_method_excludes_name(self):
        """@element on _method excludes method name from tags."""
        class Builder(BagBuilderBase):
            @element(tags='product')
            def _item(self): ...

        # Only tags are registered, not _item
        assert Builder._class_schema.get_node('product') is not None
        assert Builder._class_schema.get_node('_item') is None

    def test_multiple_tags_string(self):
        """@element with comma-separated tags string."""
        class Builder(BagBuilderBase):
            @element(tags='apple, banana, cherry')
            def _fruit(self): ...

        assert Builder._class_schema.get_node('apple') is not None
        assert Builder._class_schema.get_node('banana') is not None
        assert Builder._class_schema.get_node('cherry') is not None
        assert Builder._class_schema.get_node('_fruit') is None

    def test_multiple_tags_tuple(self):
        """@element with tuple of tags."""
        class Builder(BagBuilderBase):
            @element(tags=('red', 'green', 'blue'))
            def _color(self): ...

        assert Builder._class_schema.get_node('red') is not None
        assert Builder._class_schema.get_node('green') is not None
        assert Builder._class_schema.get_node('blue') is not None


# =============================================================================
# Tests for BagBuilderBase functionality
# =============================================================================

class TestBagBuilderBase:
    """Tests for BagBuilderBase functionality."""

    def test_bag_with_builder(self):
        """Bag can be created with a builder class."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        assert isinstance(bag.builder, Builder)

    def test_bag_without_builder(self):
        """Bag without builder works normally."""
        bag = Bag()
        assert bag.builder is None
        bag['test'] = 'value'
        assert bag['test'] == 'value'

    def test_builder_creates_node_with_tag(self):
        """Builder creates nodes with correct tag."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name='test')

        assert node.tag == 'item'
        assert node.label == 'item_0'
        assert node.attr.get('name') == 'test'

    def test_builder_auto_label_generation(self):
        """Builder auto-generates unique labels."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item()
        bag.item()
        bag.item()

        labels = list(bag.keys())
        assert labels == ['item_0', 'item_1', 'item_2']

    def test_builder_custom_handler_called(self):
        """Builder calls custom handler when present."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, **attr):
                attr['custom'] = 'injected'
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        node = bag.item()

        assert node.attr.get('custom') == 'injected'

    def test_builder_default_handler_used(self):
        """Builder uses default handler for ellipsis methods."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name='test')

        # Default handler should work
        assert node.tag == 'item'
        assert node.attr.get('name') == 'test'


# =============================================================================
# Tests for lazy Bag creation
# =============================================================================

class TestLazyBagCreation:
    """Tests for lazy Bag creation on branch nodes."""

    def test_branch_node_starts_with_none_value(self):
        """Branch node starts with value=None (lazy)."""
        class Builder(BagBuilderBase):
            @element(sub_tags='item')
            def container(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()

        assert container.value is None

    def test_bag_created_on_first_child(self):
        """Bag created lazily when first child is added."""
        class Builder(BagBuilderBase):
            @element(sub_tags='item')
            def container(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        container.item()

        assert isinstance(container.value, Bag)
        assert container.value.builder is bag.builder


# =============================================================================
# Tests for sub_tags validation
# =============================================================================

class TestSubTagsValidation:
    """Tests for sub_tags validation."""

    def test_valid_child_allowed(self):
        """Valid child tag is allowed."""
        class Builder(BagBuilderBase):
            @element(sub_tags='span,p')
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def p(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()
        div.span()  # Should not raise
        div.p()  # Should not raise

        assert len(div.value) == 2

    def test_invalid_child_rejected(self):
        """Invalid child tag is rejected."""
        class Builder(BagBuilderBase):
            @element(sub_tags='span')
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def img(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match='not allowed'):
            div.img()


# =============================================================================
# Tests for attribute validation via Annotated
# =============================================================================

class TestAnnotatedValidation:
    """Tests for attribute validation via Annotated constraints."""

    def test_range_valid(self):
        """Range constraint accepts valid value."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return self.child(target, tag, colspan=colspan, **attr)

        bag = Bag(builder=Builder)
        bag.td(colspan=5)  # Should not raise

    def test_range_min_invalid(self):
        """Range constraint rejects value below minimum."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return self.child(target, tag, colspan=colspan, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be >= 1'):
            bag.td(colspan=0)

    def test_range_max_invalid(self):
        """Range constraint rejects value above maximum."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return self.child(target, tag, colspan=colspan, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must be <= 10'):
            bag.td(colspan=20)

    def test_literal_valid(self):
        """Literal constraint accepts valid value."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, scope: Literal['row', 'col'] = None, **attr):
                return self.child(target, tag, scope=scope, **attr)

        bag = Bag(builder=Builder)
        bag.td(scope='row')  # Should not raise

    def test_literal_invalid(self):
        """Literal constraint rejects invalid value."""
        class Builder(BagBuilderBase):
            @element()
            def td(self, target, tag, scope: Literal['row', 'col'] = None, **attr):
                return self.child(target, tag, scope=scope, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='expected'):
            bag.td(scope='invalid')

    def test_regex_valid(self):
        """Regex constraint accepts matching value."""
        class Builder(BagBuilderBase):
            @element()
            def email(self, target, tag,
                      address: Annotated[str, Regex(r'^[\w\.-]+@[\w\.-]+\.\w+$')] = None,
                      **attr):
                return self.child(target, tag, address=address, **attr)

        bag = Bag(builder=Builder)
        bag.email(address='test@example.com')  # Should not raise

    def test_regex_invalid(self):
        """Regex constraint rejects non-matching value."""
        class Builder(BagBuilderBase):
            @element()
            def email(self, target, tag,
                      address: Annotated[str, Regex(r'^[\w\.-]+@[\w\.-]+\.\w+$')] = None,
                      **attr):
                return self.child(target, tag, address=address, **attr)

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match='must match pattern'):
            bag.email(address='not-an-email')

    def test_decimal_range(self):
        """Decimal type with Range constraints."""
        class Builder(BagBuilderBase):
            @element()
            def payment(self, target, tag, amount: Annotated[Decimal, Range(ge=0, le=1000)] = None, **attr):
                return self.child(target, tag, amount=amount, **attr)

        bag = Bag(builder=Builder)
        bag.payment(amount=Decimal('500.50'))  # Should not raise

        with pytest.raises(ValueError, match='must be >= 0'):
            bag.payment(amount=Decimal('-1'))

        with pytest.raises(ValueError, match='must be <= 1000'):
            bag.payment(amount=Decimal('1001'))


# =============================================================================
# Tests for builder introspection
# =============================================================================

class TestBuilderIntrospection:
    """Tests for builder introspection methods."""

    def test_repr_shows_element_count(self):
        """__repr__ shows element count."""
        class Builder(BagBuilderBase):
            @element()
            def div(self): ...

            @element()
            def span(self): ...

            @abstract(sub_tags='div,span')
            def flow(self): ...

        bag = Bag(builder=Builder)
        repr_str = repr(bag.builder)

        assert 'Builder' in repr_str
        assert '3 elements' in repr_str  # Includes @flow

    def test_get_schema_info_raises_on_unknown(self):
        """get_schema_info raises KeyError for unknown element."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(KeyError, match='not found'):
            bag.builder.get_schema_info('unknown')

    def test_getattr_raises_on_unknown_element(self):
        """Accessing unknown element raises AttributeError."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(AttributeError, match="has no element 'unknown'"):
            bag.unknown()


# =============================================================================
# Tests for sub_tags_order pattern validation (list[str] format)
# =============================================================================

class TestSubTagsOrderPattern:
    """Tests for sub_tags_order with pattern list format."""

    def test_pattern_header_any_footer(self):
        """Pattern ['^header$', '*', '^footer$'] requires header first, footer last."""
        class Builder(BagBuilderBase):
            @element(sub_tags='header,content,footer', sub_tags_order=['^header$', '*', '^footer$'])
            def page(self): ...

            @element()
            def header(self): ...

            @element()
            def content(self): ...

            @element()
            def footer(self): ...

        bag = Bag(builder=Builder)
        page = bag.page()

        page.header()
        page.content()
        page.footer()

        assert len(page.value) == 3

    def test_pattern_rejects_wrong_order(self):
        """Pattern rejects elements in wrong order."""
        class Builder(BagBuilderBase):
            @element(sub_tags='header,footer', sub_tags_order=['^header$', '^footer$'])
            def page(self): ...

            @element()
            def header(self): ...

            @element()
            def footer(self): ...

        bag = Bag(builder=Builder)
        page = bag.page()

        # footer as first element violates pattern (must start with header)
        with pytest.raises(ValueError, match='not allowed'):
            page.footer()

    def test_pattern_wildcard_at_start(self):
        """Pattern ['*', '^footer$'] allows anything before footer."""
        class Builder(BagBuilderBase):
            @element(sub_tags='a[0:],b[0:],footer', sub_tags_order=['*', '^footer$'])
            def page(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element()
            def footer(self): ...

        bag = Bag(builder=Builder)
        page = bag.page()

        page.a()
        page.b()
        page.a()
        page.footer()

        assert len(page.value) == 4

    def test_pattern_wildcard_at_end(self):
        """Pattern ['^header$', '*'] allows anything after header."""
        class Builder(BagBuilderBase):
            @element(sub_tags='header,a[],b[]', sub_tags_order=['^header$', '*'])
            def page(self): ...

            @element()
            def header(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

        bag = Bag(builder=Builder)
        page = bag.page()

        page.header()
        page.a()
        page.b()
        page.a()

        assert len(page.value) == 4

    def test_pattern_exact_sequence(self):
        """Pattern ['^a$', '^b$', '^c$'] requires exact sequence."""
        class Builder(BagBuilderBase):
            @element(sub_tags='a,b,c', sub_tags_order=['^a$', '^b$', '^c$'])
            def seq(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element()
            def c(self): ...

        bag = Bag(builder=Builder)
        seq = bag.seq()

        seq.a()
        seq.b()
        seq.c()

        assert len(seq.value) == 3

    def test_pattern_regex_any_single_tag(self):
        """Pattern ['.*'] matches exactly one tag of any name."""
        class Builder(BagBuilderBase):
            @element(sub_tags='x,y,z', sub_tags_order=['.*'])
            def single(self): ...

            @element()
            def x(self): ...

            @element()
            def y(self): ...

            @element()
            def z(self): ...

        bag = Bag(builder=Builder)
        single = bag.single()

        single.x()
        assert len(single.value) == 1

        # Try to add a second - should fail (pattern expects exactly 1)
        with pytest.raises(ValueError, match='not allowed'):
            single.y()

    def test_pattern_empty_wildcard_only(self):
        """Pattern ['*'] matches any sequence (0..N)."""
        class Builder(BagBuilderBase):
            @element(sub_tags='a[],b[]', sub_tags_order=['*'])
            def any_seq(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

        bag = Bag(builder=Builder)
        seq = bag.any_seq()

        # Empty is ok
        assert seq.value is None

        seq.a()
        seq.b()
        seq.a()

        assert len(seq.value) == 3

    def test_legacy_string_still_works(self):
        """Legacy string format 'a>b>c' still works."""
        class Builder(BagBuilderBase):
            @element(sub_tags='a,b,c', sub_tags_order='a>b>c')
            def legacy(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element()
            def c(self): ...

        bag = Bag(builder=Builder)
        leg = bag.legacy()

        leg.a()
        leg.b()
        leg.c()

        assert len(leg.value) == 3


# =============================================================================
# Tests for __value__ validation (node content vs attributes)
# =============================================================================

class TestValueValidation:
    """Tests for __value__ validation for node content."""

    def test_value_positional_basic(self):
        """__value__ passed positionally becomes node.value."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, __value__=None, **attr):
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.item("contenuto")
        assert node.value == "contenuto"

    def test_value_keyword_basic(self):
        """__value__ can also be passed as keyword."""
        class Builder(BagBuilderBase):
            @element()
            def item(self, target, tag, __value__=None, **attr):
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.item(__value__="contenuto")
        assert node.value == "contenuto"

    def test_value_and_attr_disambiguation(self):
        """__value__ (content) and arbitrary attr are separate."""
        class Builder(BagBuilderBase):
            @element()
            def input(self, target, tag, __value__=None, *, default=None, **attr):
                # default è un attributo, __value__ è il contenuto
                if default is not None:
                    attr['default'] = default
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.input("node content", default="attr value")
        assert node.value == "node content"
        assert node.attr['default'] == "attr value"

    def test_value_validation_type(self):
        """__value__ type is validated."""
        class Builder(BagBuilderBase):
            @element()
            def number(self, target, tag, __value__: int = None, **attr):
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.number(42)
        assert node.value == 42

        with pytest.raises(ValueError, match=r"expected.*int"):
            bag.number("not a number")

    def test_value_validation_annotated_range(self):
        """__value__ with Annotated Range validator."""
        class Builder(BagBuilderBase):
            @element()
            def amount(self, target, tag,
                       __value__: Annotated[Decimal, Range(ge=0)] = None,
                       **attr):
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.amount(Decimal("10"))
        assert node.value == Decimal("10")

        with pytest.raises(ValueError, match="must be >= 0"):
            bag.amount(Decimal("-5"))

    def test_value_validation_annotated_regex(self):
        """__value__ with Annotated Regex validator."""
        class Builder(BagBuilderBase):
            @element()
            def code(self, target, tag,
                     __value__: Annotated[str, Regex(r'^[A-Z]{3}$')] = None,
                     **attr):
                return self.child(target, tag, value=__value__, **attr)

        bag = Bag(builder=Builder)
        node = bag.code("ABC")
        assert node.value == "ABC"

        with pytest.raises(ValueError, match="must match pattern"):
            bag.code("abc")

    def test_value_default_element_positional(self):
        """Default element handler accepts __value__ positionally."""
        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item("my value")
        assert node.value == "my value"

    def test_attr_validated_when_typed(self):
        """Typed attributes are validated."""
        class Builder(BagBuilderBase):
            @element()
            def input(self, target, tag, default: str = None, **attr):
                # default è un attributo con validazione tipo
                if default is not None:
                    attr['default'] = default
                return self.child(target, tag, **attr)

        bag = Bag(builder=Builder)
        node = bag.input(default="text")
        assert node.attr['default'] == "text"

        with pytest.raises(ValueError, match=r"expected.*str"):
            bag.input(default=123)
