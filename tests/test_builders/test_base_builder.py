# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase and builder decorators.

Tests cover:
- @element decorator with various configurations
- @abstract decorator for inheritance bases
- Ellipsis body detection (adapter_name=None vs adapter_name='_el_name')
- Schema structure with @ prefix for abstracts
- Inheritance resolution via inherits_from
- Attribute validation via Annotated constraints
"""

from decimal import Decimal
from typing import Annotated, Literal

import pytest

from genro_bag import Bag, BagBuilderBase
from genro_bag.builder import SchemaBuilder
from genro_bag.builders import Range, Regex, abstract, element

# =============================================================================
# Tests for @element decorator - handler detection
# =============================================================================


class TestElementDecoratorHandlerDetection:
    """Tests for @element decorator handler detection."""

    def test_ellipsis_body_sets_adapter_name_none(self):
        """@element with ... body sets adapter_name=None in schema."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Schema should have adapter_name=None
        node = Builder._class_schema.get_node("item")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_real_body_sets_adapter_name(self):
        """@element with real body sets adapter_name='_el_name' in schema."""

        class Builder(BagBuilderBase):
            @element()
            def item(self, **attr):
                attr.setdefault("custom", "value")
                return attr

        # Schema should have adapter_name='_el_item'
        node = Builder._class_schema.get_node("item")
        assert node is not None
        assert node.attr.get("adapter_name") == "_el_item"
        # Method should be renamed
        assert hasattr(Builder, "_el_item")
        assert not hasattr(Builder, "item")

    def test_ellipsis_method_removed_from_class(self):
        """@element with ... body removes method from class."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Method should be removed (no _el_item either)
        assert not hasattr(Builder, "item")
        assert not hasattr(Builder, "_el_item")

    def test_ellipsis_inline_with_params(self):
        """@element with inline ... and parameters sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None): ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_ellipsis_newline_with_params(self):
        """@element with ... on separate line sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None): ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_ellipsis_with_docstring_and_params(self):
        """@element with docstring and ... sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None):
                "this is my method"
                ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None


# =============================================================================
# Tests for @abstract decorator
# =============================================================================


class TestAbstractDecorator:
    """Tests for @abstract decorator."""

    def test_abstract_creates_at_prefixed_entry(self):
        """@abstract creates @name entry in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

        # Schema should have @flow
        node = Builder._class_schema.get_node("@flow")
        assert node is not None
        assert node.attr.get("sub_tags") == "span,p"

    def test_abstract_method_removed_from_class(self):
        """@abstract removes method from class."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

        assert not hasattr(Builder, "flow")
        assert not hasattr(Builder, "_el_flow")

    def test_iteration_returns_all_nodes(self):
        """Iteration returns all schema nodes including abstracts."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

            @element()
            def div(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        labels = [node.label for node in bag.builder]
        assert "div" in labels
        assert "span" in labels
        assert "@flow" in labels

    def test_abstract_not_in_contains(self):
        """Abstract elements work with 'in' operator."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        assert "div" in bag.builder
        assert "@flow" in bag.builder  # Abstracts are in schema


# =============================================================================
# Tests for inherits_from
# =============================================================================


class TestInheritsFrom:
    """Tests for inherits_from inheritance resolution."""

    def test_element_inherits_sub_tags_from_abstract(self):
        """Element inherits sub_tags from abstract via inherits_from."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p,a")
            def phrasing(self): ...

            @element(inherits_from="@phrasing")
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def p(self): ...

            @element()
            def a(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("div")
        assert info.get("sub_tags") == "span,p,a"

    def test_element_can_override_inherited_attrs(self):
        """Element attrs override inherited attrs from abstract."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b,c")
            def base(self): ...

            @element(inherits_from="@base", sub_tags="x,y,z")
            def custom(self): ...

            @element()
            def x(self): ...

            @element()
            def y(self): ...

            @element()
            def z(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("custom")
        # sub_tags overridden
        assert info.get("sub_tags") == "x,y,z"

    def test_multiple_inheritance_comma_separated(self):
        """Element can inherit from multiple abstracts via comma-separated list."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b")
            def base_tags(self): ...

            @abstract(parent_tags="container")
            def base_parent(self): ...

            @element(inherits_from="@base_tags,@base_parent")
            def multi(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element(sub_tags="multi")
            def container(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("multi")
        # Inherits from both abstracts
        assert info.get("sub_tags") == "a,b"
        assert info.get("parent_tags") == "container"

    def test_multiple_inheritance_first_wins(self):
        """In multiple inheritance, first parent wins (closest to element)."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b", parent_tags="first")
            def first(self): ...

            @abstract(sub_tags="x,y", parent_tags="second")
            def second(self): ...

            @element(inherits_from="@first,@second")
            def derived(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("derived")
        # @first wins over @second (first is closest)
        assert info.get("sub_tags") == "a,b"
        assert info.get("parent_tags") == "first"


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

        assert Builder._class_schema.get_node("item") is not None

    def test_single_tag_string_adds_to_method_name(self):
        """@element with tags adds them to method name."""

        class Builder(BagBuilderBase):
            @element(tags="product")
            def item(self): ...

        # Both method name and tags are registered
        assert Builder._class_schema.get_node("item") is not None
        assert Builder._class_schema.get_node("product") is not None

    def test_underscore_method_excludes_name(self):
        """@element on _method excludes method name from tags."""

        class Builder(BagBuilderBase):
            @element(tags="product")
            def _item(self): ...

        # Only tags are registered, not _item
        assert Builder._class_schema.get_node("product") is not None
        assert Builder._class_schema.get_node("_item") is None

    def test_multiple_tags_string(self):
        """@element with comma-separated tags string."""

        class Builder(BagBuilderBase):
            @element(tags="apple, banana, cherry")
            def _fruit(self): ...

        assert Builder._class_schema.get_node("apple") is not None
        assert Builder._class_schema.get_node("banana") is not None
        assert Builder._class_schema.get_node("cherry") is not None
        assert Builder._class_schema.get_node("_fruit") is None

    def test_multiple_tags_tuple(self):
        """@element with tuple of tags."""

        class Builder(BagBuilderBase):
            @element(tags=("red", "green", "blue"))
            def _color(self): ...

        assert Builder._class_schema.get_node("red") is not None
        assert Builder._class_schema.get_node("green") is not None
        assert Builder._class_schema.get_node("blue") is not None


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
        bag["test"] = "value"
        assert bag["test"] == "value"

    def test_builder_creates_node_with_tag(self):
        """Builder creates nodes with correct tag."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name="test")

        assert node.tag == "item"
        assert node.label == "item_0"
        assert node.attr.get("name") == "test"

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
        assert labels == ["item_0", "item_1", "item_2"]

    def test_builder_custom_handler_called(self):
        """Builder calls custom handler when present."""

        class Builder(BagBuilderBase):
            @element()
            def item(self, **attr):
                attr["custom"] = "injected"
                return attr

        bag = Bag(builder=Builder)
        node = bag.item()

        assert node.attr.get("custom") == "injected"

    def test_builder_default_handler_used(self):
        """Builder uses default handler for ellipsis methods."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name="test")

        # Default handler should work
        assert node.tag == "item"
        assert node.attr.get("name") == "test"


# =============================================================================
# Tests for lazy Bag creation
# =============================================================================


class TestLazyBagCreation:
    """Tests for lazy Bag creation on branch nodes."""

    def test_branch_node_starts_with_none_value(self):
        """Branch node starts with value=None (lazy)."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()

        assert container.value is None

    def test_bag_created_on_first_child(self):
        """Bag created lazily when first child is added."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
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
            @element(sub_tags="span,p")
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
            @element(sub_tags="span")
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def img(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="not allowed"):
            div.img()

    def test_void_element_rejects_children(self):
        """Bug: sub_tags='' (void element) should reject ALL children.

        Empty string means "no children allowed", but was being treated
        as "no validation" because '' is falsy in Python.
        """

        class Builder(BagBuilderBase):
            @element(sub_tags="")  # void element - no children allowed
            def br(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        br = bag.br()

        # void element should reject any child
        with pytest.raises(ValueError, match="not allowed"):
            br.span()


# =============================================================================
# Tests for parent_tags validation
# =============================================================================


class TestParentTagsValidation:
    """Tests for parent_tags validation (child declares valid parents)."""

    def test_valid_parent_allowed(self):
        """Child with parent_tags can be placed in valid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")
            def li(self): ...

        bag = Bag(builder=Builder)
        ul = bag.ul()
        ul.li()  # Should not raise

        assert len(ul.value) == 1

    def test_invalid_parent_rejected(self):
        """Child with parent_tags cannot be placed in invalid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li,span")
            def div(self): ...

            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")  # li can only be in ul
            def li(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="parent_tags requires"):
            div.li()  # div is not a valid parent for li

    def test_parent_tags_at_root_rejected(self):
        """Child with parent_tags cannot be placed at root if root not in list."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")  # li can only be in ul
            def li(self): ...

        bag = Bag(builder=Builder)

        with pytest.raises(ValueError, match="parent_tags requires"):
            bag.li()  # root is not a valid parent for li

    def test_parent_tags_multiple_valid_parents(self):
        """Child with multiple parent_tags can be placed in any of them."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(sub_tags="li")
            def ol(self): ...

            @element(parent_tags="ul, ol")  # li can be in ul or ol
            def li(self): ...

        bag = Bag(builder=Builder)
        ul = bag.ul()
        ul.li()  # ul is valid

        ol = bag.ol()
        ol.li()  # ol is valid

        assert len(ul.value) == 1
        assert len(ol.value) == 1

    def test_no_parent_tags_allows_anywhere(self):
        """Element without parent_tags can be placed anywhere."""

        class Builder(BagBuilderBase):
            @element(sub_tags="span")
            def div(self): ...

            @element()  # no parent_tags - can be placed anywhere
            def span(self): ...

        bag = Bag(builder=Builder)
        bag.span()  # at root - OK
        div = bag.div()
        div.span()  # in div - OK

        assert len(bag) == 2


# =============================================================================
# Tests for attribute validation via Annotated
# =============================================================================


class TestAnnotatedValidation:
    """Tests for attribute validation via Annotated constraints."""

    def test_range_valid(self):
        """Range constraint accepts valid value."""

        class Builder(BagBuilderBase):
            @element()
            def td(self, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return {"colspan": colspan, **attr}

        bag = Bag(builder=Builder)
        bag.td(colspan=5)  # Should not raise

    def test_range_min_invalid(self):
        """Range constraint rejects value below minimum."""

        class Builder(BagBuilderBase):
            @element()
            def td(self, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return {"colspan": colspan, **attr}

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must be >= 1"):
            bag.td(colspan=0)

    def test_range_max_invalid(self):
        """Range constraint rejects value above maximum."""

        class Builder(BagBuilderBase):
            @element()
            def td(self, colspan: Annotated[int, Range(ge=1, le=10)] = None, **attr):
                return {"colspan": colspan, **attr}

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must be <= 10"):
            bag.td(colspan=20)

    def test_literal_valid(self):
        """Literal constraint accepts valid value."""

        class Builder(BagBuilderBase):
            @element()
            def td(self, scope: Literal["row", "col"] = None, **attr):
                return {"scope": scope, **attr}

        bag = Bag(builder=Builder)
        bag.td(scope="row")  # Should not raise

    def test_literal_invalid(self):
        """Literal constraint rejects invalid value."""

        class Builder(BagBuilderBase):
            @element()
            def td(self, scope: Literal["row", "col"] = None, **attr):
                return {"scope": scope, **attr}

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="expected"):
            bag.td(scope="invalid")

    def test_regex_valid(self):
        """Regex constraint accepts matching value."""

        class Builder(BagBuilderBase):
            @element()
            def email(
                self,
                address: Annotated[str, Regex(r"^[\w\.-]+@[\w\.-]+\.\w+$")] = None,
                **attr,
            ):
                return {"address": address, **attr}

        bag = Bag(builder=Builder)
        bag.email(address="test@example.com")  # Should not raise

    def test_regex_invalid(self):
        """Regex constraint rejects non-matching value."""

        class Builder(BagBuilderBase):
            @element()
            def email(
                self,
                address: Annotated[str, Regex(r"^[\w\.-]+@[\w\.-]+\.\w+$")] = None,
                **attr,
            ):
                return {"address": address, **attr}

        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must match pattern"):
            bag.email(address="not-an-email")

    def test_decimal_range(self):
        """Decimal type with Range constraints."""

        class Builder(BagBuilderBase):
            @element()
            def payment(
                self, amount: Annotated[Decimal, Range(ge=0, le=1000)] = None, **attr
            ):
                return {"amount": amount, **attr}

        bag = Bag(builder=Builder)
        bag.payment(amount=Decimal("500.50"))  # Should not raise

        with pytest.raises(ValueError, match="must be >= 0"):
            bag.payment(amount=Decimal("-1"))

        with pytest.raises(ValueError, match="must be <= 1000"):
            bag.payment(amount=Decimal("1001"))


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

            @abstract(sub_tags="div,span")
            def flow(self): ...

        bag = Bag(builder=Builder)
        repr_str = repr(bag.builder)

        assert "Builder" in repr_str
        assert "3 elements" in repr_str  # Includes @flow

    def test_get_schema_info_raises_on_unknown(self):
        """get_schema_info raises KeyError for unknown element."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(KeyError, match="not found"):
            bag.builder.get_schema_info("unknown")

    def test_getattr_raises_on_unknown_element(self):
        """Accessing unknown element raises AttributeError."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(AttributeError, match="has no element 'unknown'"):
            bag.unknown()


# =============================================================================
# Tests for node_value validation (node content vs attributes)
# =============================================================================


class TestValueValidation:
    """Tests for node_value validation for node content."""

    def test_value_positional_basic(self):
        """node_value passed positionally becomes node.value."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item("contenuto")
        assert node.value == "contenuto"

    def test_value_keyword_basic(self):
        """node_value can also be passed as keyword."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(node_value="contenuto")
        assert node.value == "contenuto"

    def test_value_and_attr_disambiguation(self):
        """node_value (content) and arbitrary attr are separate."""

        class Builder(BagBuilderBase):
            @element()
            def input(self, node_value=None, *, default=None, **attr):
                # default è un attributo, node_value è il contenuto
                if default is not None:
                    attr["default"] = default
                if node_value is not None:
                    attr["node_value"] = node_value
                return attr

        bag = Bag(builder=Builder)
        node = bag.input("node content", default="attr value")
        assert node.value == "node content"
        assert node.attr["default"] == "attr value"

    def test_value_validation_type(self):
        """node_value type is validated."""

        class Builder(BagBuilderBase):
            @element()
            def number(self, node_value: int = None, **attr):
                return {"node_value": node_value, **attr}

        bag = Bag(builder=Builder)
        node = bag.number(42)
        assert node.value == 42

        with pytest.raises(ValueError, match=r"expected.*int"):
            bag.number("not a number")

    def test_value_validation_annotated_range(self):
        """node_value with Annotated Range validator."""

        class Builder(BagBuilderBase):
            @element()
            def amount(
                self, node_value: Annotated[Decimal, Range(ge=0)] = None, **attr
            ):
                return {"node_value": node_value, **attr}

        bag = Bag(builder=Builder)
        node = bag.amount(Decimal("10"))
        assert node.value == Decimal("10")

        with pytest.raises(ValueError, match="must be >= 0"):
            bag.amount(Decimal("-5"))

    def test_value_validation_annotated_regex(self):
        """node_value with Annotated Regex validator."""

        class Builder(BagBuilderBase):
            @element()
            def code(
                self, node_value: Annotated[str, Regex(r"^[A-Z]{3}$")] = None, **attr
            ):
                return {"node_value": node_value, **attr}

        bag = Bag(builder=Builder)
        node = bag.code("ABC")
        assert node.value == "ABC"

        with pytest.raises(ValueError, match="must match pattern"):
            bag.code("abc")

    def test_value_default_element_positional(self):
        """Default element handler accepts node_value positionally."""

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
            def input(self, default: str = None, **attr):
                # default è un attributo con validazione tipo
                if default is not None:
                    attr["default"] = default
                return attr

        bag = Bag(builder=Builder)
        node = bag.input(default="text")
        assert node.attr["default"] == "text"

        with pytest.raises(ValueError, match=r"expected.*str"):
            bag.input(default=123)


# =============================================================================
# Tests for builder.check()
# =============================================================================


class TestBuilderCheck:
    """Tests for builder.check() validation method."""

    def test_check_empty_bag_returns_empty_list(self):
        """check() on empty bag returns empty list."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.builder.check()
        assert result == []

    def test_check_valid_bag_returns_empty_list(self):
        """check() on valid bag returns empty list."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        outer_node = bag.outer()
        outer_node.inner()

        result = bag.builder.check()
        assert result == []

    def test_check_finds_invalid_nodes(self):
        """check() finds nodes with missing required children."""

        class Builder(BagBuilderBase):
            @element(sub_tags="required[1]")
            def container(self): ...

            @element(sub_tags="")
            def required(self): ...

        bag = Bag(builder=Builder)
        bag.container()  # Missing required child

        result = bag.builder.check()
        assert len(result) == 1
        path, node, reasons = result[0]
        assert "container_0" in path
        assert "required" in reasons

    def test_check_walks_nested_bags(self):
        """check() recursively walks nested Bag structures."""

        class Builder(BagBuilderBase):
            @element(sub_tags="middle")
            def wrapper(self): ...

            @element(sub_tags="leaf[1]")
            def middle(self): ...

            @element(sub_tags="")
            def leaf(self): ...

        bag = Bag(builder=Builder)
        wrapper_node = bag.wrapper()
        wrapper_node.middle()  # Missing required leaf

        result = bag.builder.check()
        assert len(result) == 1
        path, node, reasons = result[0]
        assert "middle" in path
        assert "leaf" in reasons

    def test_check_accepts_explicit_bag(self):
        """check() can validate an explicit bag parameter."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner[1]")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        bag.outer()  # Missing required child

        other_bag = Bag(builder=Builder)
        outer_node = other_bag.outer()
        outer_node.inner()  # Valid

        # Check the invalid bag explicitly
        result = bag.builder.check(bag)
        assert len(result) == 1

        # Check the valid bag explicitly
        result = bag.builder.check(other_bag)
        assert result == []


# =============================================================================
# Tests for builder.compile()
# =============================================================================


class TestBuilderCompile:
    """Tests for builder.compile() output method."""

    def test_compile_defaults_to_xml(self):
        """compile() defaults to XML format."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item("content")

        result = bag.builder.compile()
        # XML uses tag name, not label
        assert "<item" in result
        assert "content" in result

    def test_compile_xml_format(self):
        """compile(format='xml') produces valid XML."""

        class Builder(BagBuilderBase):
            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.div("hello")

        result = bag.builder.compile(format="xml")
        assert result.startswith("<")
        # XML uses tag name
        assert "<div" in result

    def test_compile_json_format(self):
        """compile(format='json') produces JSON."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item("value")

        result = bag.builder.compile(format="json")
        assert "item_0" in result
        assert "value" in result

    def test_compile_unknown_format_raises(self):
        """compile() raises ValueError for unknown format."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item()

        with pytest.raises(ValueError, match="Unknown format"):
            bag.builder.compile(format="yaml")


# =============================================================================
# Tests for compile_kwargs
# =============================================================================


class TestCompileKwargs:
    """Tests for compile_kwargs in @element and @abstract decorators."""

    def test_element_compile_kwargs_dict(self):
        """@element with compile_kwargs dict stores in schema."""

        class Builder(BagBuilderBase):
            @element(compile_kwargs={"module": "textual.containers", "class": "Vertical"})
            def vertical(self): ...

        info = Builder._class_schema.get_attr("vertical")
        assert info["compile_kwargs"] == {"module": "textual.containers", "class": "Vertical"}

    def test_element_compile_separate_params(self):
        """@element with compile_* params extracts and merges."""

        class Builder(BagBuilderBase):
            @element(compile_module="textual.widgets", compile_class="Button")
            def button(self): ...

        info = Builder._class_schema.get_attr("button")
        assert info["compile_kwargs"] == {"module": "textual.widgets", "class": "Button"}

    def test_element_compile_mixed(self):
        """@element with both compile_kwargs and compile_* params merges."""

        class Builder(BagBuilderBase):
            @element(
                compile_kwargs={"module": "textual.containers"},
                compile_class="Horizontal",
            )
            def horizontal(self): ...

        info = Builder._class_schema.get_attr("horizontal")
        assert info["compile_kwargs"] == {"module": "textual.containers", "class": "Horizontal"}

    def test_abstract_compile_kwargs(self):
        """@abstract with compile_* params stores in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child", compile_module="textual.containers")
            def base_container(self): ...

        info = Builder._class_schema.get_attr("@base_container")
        assert info["compile_kwargs"] == {"module": "textual.containers"}

    def test_inherits_compile_kwargs_merge(self):
        """Element inherits and merges compile_kwargs from abstract."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child", compile_module="textual.containers")
            def base_container(self): ...

            @element(inherits_from="@base_container", compile_class="Vertical")
            def vertical(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("vertical")

        # Should have merged: module from abstract + class from element
        assert info["compile_kwargs"] == {"module": "textual.containers", "class": "Vertical"}

    def test_inherits_compile_kwargs_override(self):
        """Element can override inherited compile_kwargs values."""

        class Builder(BagBuilderBase):
            @abstract(
                sub_tags="child",
                compile_module="textual.containers",
                compile_class="Container",
            )
            def base_container(self): ...

            @element(inherits_from="@base_container", compile_class="Vertical")
            def vertical(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("vertical")

        # class should be overridden, module inherited
        assert info["compile_kwargs"]["module"] == "textual.containers"
        assert info["compile_kwargs"]["class"] == "Vertical"

    def test_element_without_compile_kwargs(self):
        """Element without compile_kwargs has no compile_kwargs in schema."""

        class Builder(BagBuilderBase):
            @element()
            def simple(self): ...

        info = Builder._class_schema.get_attr("simple")
        assert "compile_kwargs" not in info or info.get("compile_kwargs") is None


class TestSchemaBuilderCompileKwargs:
    """Tests for compile_kwargs in SchemaBuilder.item()."""

    def test_schema_builder_item_compile_kwargs_dict(self):
        """SchemaBuilder.item() with compile_kwargs dict stores in schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("widget", compile_kwargs={"module": "textual.widgets", "class": "Button"})

        info = schema.get_attr("widget")
        assert info["compile_kwargs"] == {"module": "textual.widgets", "class": "Button"}

    def test_schema_builder_item_compile_separate_params(self):
        """SchemaBuilder.item() with compile_* params extracts and merges."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("container", compile_module="textual.containers", compile_class="Vertical")

        info = schema.get_attr("container")
        assert info["compile_kwargs"] == {"module": "textual.containers", "class": "Vertical"}

    def test_schema_builder_item_compile_mixed(self):
        """SchemaBuilder.item() with both compile_kwargs and compile_* params merges."""
        schema = Bag(builder=SchemaBuilder)
        schema.item(
            "horizontal",
            compile_kwargs={"module": "textual.containers"},
            compile_class="Horizontal",
        )

        info = schema.get_attr("horizontal")
        assert info["compile_kwargs"] == {"module": "textual.containers", "class": "Horizontal"}

    def test_schema_builder_item_without_compile_kwargs(self):
        """SchemaBuilder.item() without compile_kwargs has no compile_kwargs."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("simple", sub_tags="child")

        info = schema.get_attr("simple")
        assert "compile_kwargs" not in info or info.get("compile_kwargs") is None


# =============================================================================
# Tests for documentation extraction
# =============================================================================


class TestDocumentation:
    """Tests for documentation extraction from decorated methods."""

    def test_element_docstring_stored_in_schema(self):
        """@element method docstring is saved as documentation in schema."""

        class Builder(BagBuilderBase):
            @element()
            def button(self):
                """A clickable button element."""
                ...

        info = Builder._class_schema.get_attr("button")
        assert info["documentation"] == "A clickable button element."

    def test_element_no_docstring_has_none(self):
        """@element method without docstring has documentation=None."""

        class Builder(BagBuilderBase):
            @element()
            def simple(self): ...

        info = Builder._class_schema.get_attr("simple")
        assert info.get("documentation") is None

    def test_abstract_docstring_stored_in_schema(self):
        """@abstract method docstring is saved as documentation in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child")
            def container(self):
                """Base container for layout elements."""
                ...

        info = Builder._class_schema.get_attr("@container")
        assert info["documentation"] == "Base container for layout elements."

    def test_schema_builder_documentation_param(self):
        """SchemaBuilder.item() with documentation param stores in schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("widget", documentation="A generic widget element.")

        info = schema.get_attr("widget")
        assert info["documentation"] == "A generic widget element."

    def test_schema_builder_no_documentation(self):
        """SchemaBuilder.item() without documentation has None."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("simple")

        info = schema.get_attr("simple")
        assert info.get("documentation") is None

    def test_get_schema_info_includes_documentation(self):
        """get_schema_info() returns documentation from schema."""

        class Builder(BagBuilderBase):
            @element()
            def input(self):
                """Text input field."""
                ...

        bag = Bag(builder=Builder)
        info = bag.builder.get_schema_info("input")
        assert info["documentation"] == "Text input field."


# =============================================================================
# Tests for schema_to_md()
# =============================================================================


class TestSchemaToMd:
    """Tests for schema_to_md() method."""

    def test_schema_to_md_basic(self):
        """schema_to_md() generates markdown with elements."""

        class Builder(BagBuilderBase):
            @element()
            def button(self):
                """A clickable button."""
                ...

            @element(sub_tags="span,p")
            def div(self):
                """A container element."""
                ...

        bag = Bag(builder=Builder)
        md = bag.builder.schema_to_md()

        assert "# Schema: Builder" in md
        assert "## Elements" in md
        assert "`button`" in md
        assert "`div`" in md
        assert "A clickable button." in md
        assert "A container element." in md

    def test_schema_to_md_with_abstracts(self):
        """schema_to_md() includes abstract elements section."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self):
                """Flow content model."""
                ...

            @element(inherits_from="@flow")
            def div(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder.schema_to_md()

        assert "## Abstract Elements" in md
        assert "`@flow`" in md
        assert "Flow content model." in md
        assert "## Elements" in md
        assert "`div`" in md

    def test_schema_to_md_with_compile_kwargs(self):
        """schema_to_md() shows compile_kwargs."""

        class Builder(BagBuilderBase):
            @element(compile_module="textual.widgets", compile_class="Button")
            def button(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder.schema_to_md()

        assert "module: textual.widgets" in md
        assert "class: Button" in md

    def test_schema_to_md_custom_title(self):
        """schema_to_md() accepts custom title."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder.schema_to_md(title="My Custom Builder")

        assert "# Schema: My Custom Builder" in md

    def test_schema_to_md_table_format(self):
        """schema_to_md() generates valid markdown tables."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self):
                """Container element."""
                ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder.schema_to_md()

        # Check table structure
        assert "| Name |" in md
        assert "| --- |" in md
        assert "| `container` |" in md
        assert "| `item` |" in md


# =============================================================================
# Tests for Range and Regex validators (coverage for lines 373, 389, 395, 397)
# =============================================================================


class TestValidatorClasses:
    """Tests for Range and Regex validator classes."""

    def test_regex_non_string_raises_type_error(self):
        """Regex validator raises TypeError for non-string value."""
        validator = Regex(pattern=r"\d+")

        with pytest.raises(TypeError, match="requires a str"):
            validator(123)  # Not a string

    def test_range_non_numeric_raises_type_error(self):
        """Range validator raises TypeError for non-numeric value."""
        validator = Range(ge=0, le=10)

        with pytest.raises(TypeError, match="requires int, float or Decimal"):
            validator("not a number")

    def test_range_gt_constraint(self):
        """Range validator with gt (greater than) constraint."""
        validator = Range(gt=5)

        validator(6)  # OK
        validator(100)  # OK

        with pytest.raises(ValueError, match="must be > 5"):
            validator(5)  # Equal to gt, should fail

    def test_range_lt_constraint(self):
        """Range validator with lt (less than) constraint."""
        validator = Range(lt=10)

        validator(9)  # OK
        validator(0)  # OK

        with pytest.raises(ValueError, match="must be < 10"):
            validator(10)  # Equal to lt, should fail


# =============================================================================
# Tests for _check_type function (coverage for lines 1190, 1202-1250)
# =============================================================================


class TestCheckTypeFunction:
    """Tests for _check_type internal function."""

    def test_literal_type_checking(self):
        """_check_type works with Literal type."""
        from genro_bag.builder import _check_type

        assert _check_type("a", Literal["a", "b", "c"]) is True
        assert _check_type("d", Literal["a", "b", "c"]) is False

    def test_list_type_checking(self):
        """_check_type works with list[T] type."""
        from genro_bag.builder import _check_type

        assert _check_type([1, 2, 3], list[int]) is True
        assert _check_type(["a", "b"], list[str]) is True
        assert _check_type([1, "mixed"], list[int]) is False
        assert _check_type("not a list", list[int]) is False
        # Empty list is valid
        assert _check_type([], list[int]) is True

    def test_dict_type_checking(self):
        """_check_type works with dict[K, V] type."""
        from genro_bag.builder import _check_type

        assert _check_type({"a": 1, "b": 2}, dict[str, int]) is True
        assert _check_type({1: "a", 2: "b"}, dict[int, str]) is True
        assert _check_type({"a": "b"}, dict[str, int]) is False
        assert _check_type("not a dict", dict[str, int]) is False
        # Empty dict is valid
        assert _check_type({}, dict[str, int]) is True

    def test_tuple_type_checking(self):
        """_check_type works with tuple[T, ...] type."""
        from genro_bag.builder import _check_type

        # Fixed-length tuple
        assert _check_type((1, "a"), tuple[int, str]) is True
        assert _check_type((1, 2), tuple[int, str]) is False
        assert _check_type("not a tuple", tuple[int, str]) is False

        # Variable-length tuple with ellipsis
        assert _check_type((1, 2, 3), tuple[int, ...]) is True
        assert _check_type((1, "mixed"), tuple[int, ...]) is False

    def test_set_type_checking(self):
        """_check_type works with set[T] type."""
        from genro_bag.builder import _check_type

        assert _check_type({1, 2, 3}, set[int]) is True
        assert _check_type({"a", "b"}, set[str]) is True
        assert _check_type({1, "mixed"}, set[int]) is False
        assert _check_type("not a set", set[int]) is False
        # Empty set is valid
        assert _check_type(set(), set[int]) is True

    def test_union_type_checking(self):
        """_check_type works with Union and | types."""
        from genro_bag.builder import _check_type

        # Using | syntax (Python 3.10+)
        assert _check_type(1, int | str) is True
        assert _check_type("hello", int | str) is True
        assert _check_type(1.5, int | str) is False

    def test_any_type_accepts_everything(self):
        """_check_type with Any accepts everything."""
        from typing import Any

        from genro_bag.builder import _check_type

        assert _check_type(1, Any) is True
        assert _check_type("string", Any) is True
        assert _check_type(None, Any) is True
        assert _check_type([1, 2, 3], Any) is True

    def test_none_type_checking(self):
        """_check_type with NoneType."""
        from genro_bag.builder import _check_type

        assert _check_type(None, type(None)) is True
        assert _check_type("not none", type(None)) is False


# =============================================================================
# Tests for _split_annotated with Optional (coverage for lines 1166-1174)
# =============================================================================


class TestSplitAnnotated:
    """Tests for _split_annotated internal function."""

    def test_optional_annotated_type(self):
        """_split_annotated handles Optional[Annotated[T, ...]]."""
        from typing import Optional

        from genro_bag.builder import _split_annotated

        # Optional[Annotated[int, Range(ge=0)]] is Union[Annotated[int, Range(ge=0)], None]
        tp = Optional[Annotated[int, Range(ge=0)]]
        base, validators = _split_annotated(tp)

        assert base == int
        assert len(validators) == 1
        assert isinstance(validators[0], Range)


# =============================================================================
# Tests for _parse_sub_tags_spec (coverage for lines 1327-1331, 1342)
# =============================================================================


class TestParseSubTagsSpec:
    """Tests for _parse_sub_tags_spec internal function."""

    def test_range_syntax(self):
        """_parse_sub_tags_spec handles [min:max] syntax."""
        from genro_bag.builder import _parse_sub_tags_spec

        result = _parse_sub_tags_spec("item[1:3]")
        assert result == {"item": (1, 3)}

        result = _parse_sub_tags_spec("item[0:]")
        import sys

        assert result == {"item": (0, sys.maxsize)}

        result = _parse_sub_tags_spec("item[:5]")
        assert result == {"item": (0, 5)}

    def test_invalid_empty_brackets_raises(self):
        """_parse_sub_tags_spec raises for invalid [] syntax."""
        from genro_bag.builder import _parse_sub_tags_spec

        with pytest.raises(ValueError, match="Invalid sub_tags syntax"):
            _parse_sub_tags_spec("item[]")


# =============================================================================
# Tests for _pop_decorated_methods tags tuple (coverage for lines 1367-1370)
# =============================================================================


class TestPopDecoratedMethodsTags:
    """Tests for _pop_decorated_methods with tuple tags."""

    def test_element_with_tags_tuple(self):
        """@element with tags as tuple."""

        class Builder(BagBuilderBase):
            @element(tags=("alias1", "alias2"))
            def _internal(self): ...

        # Both aliases should be in schema
        assert Builder._class_schema.get_node("alias1") is not None
        assert Builder._class_schema.get_node("alias2") is not None


# =============================================================================
# Tests for _rename_colliding_schema_tags (coverage for lines 1404-1419)
# =============================================================================


class TestRenameCollidingTags:
    """Tests for _rename_colliding_schema_tags."""

    def test_colliding_tag_renamed(self):
        """Schema tags colliding with Bag methods are renamed."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            class Builder(BagBuilderBase):
                @element()
                def keys(self):  # 'keys' is a Bag method
                    ...

            # Should have warning
            assert len(w) == 1
            assert "renamed" in str(w[0].message).lower()
            assert "keys" in str(w[0].message)

            # Tag should be renamed to 'el_keys'
            assert Builder._class_schema.get_node("el_keys") is not None
            assert Builder._class_schema.get_node("keys") is None


# =============================================================================
# Tests for SchemaBuilder.compile (coverage for lines 1508-1509)
# =============================================================================


class TestSchemaBuilderCompile:
    """Tests for SchemaBuilder.compile method."""

    def test_compile_saves_msgpack(self, tmp_path):
        """SchemaBuilder.compile saves schema to msgpack file."""
        schema = Bag(builder=SchemaBuilder)
        schema.item("div", sub_tags="span")
        schema.item("span")

        # Use correct extension for msgpack files
        output_file = tmp_path / "test_schema.bag.mp"
        schema.builder.compile(output_file)

        # File should exist and contain msgpack data
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Should be loadable
        loaded = Bag().fill_from(output_file)
        assert loaded.get_node("div") is not None
        assert loaded.get_node("span") is not None


# =============================================================================
# Tests for _render_value (coverage for lines 1097-1126)
# =============================================================================


class TestRenderValue:
    """Tests for _render_value method."""

    def test_value_format_attribute(self):
        """_render_value applies value_format from node attribute.

        value_format is a Python format string applied to the node value.
        The format uses .format() method, so for numeric formatting we need {}.
        """

        class Builder(BagBuilderBase):
            @element()
            def price(self): ...

        bag = Bag(builder=Builder)
        # Use format that adds prefix/suffix
        bag.price(node_value="42.50", value_format="Price: {}")

        node = bag.get_node("price_0")
        result = bag.builder._render_value(node)

        assert result == "Price: 42.50"

    def test_value_template_attribute(self):
        """_render_value applies value_template from node attribute."""

        class Builder(BagBuilderBase):
            @element()
            def greeting(self): ...

        bag = Bag(builder=Builder)
        bag.greeting(node_value="World", value_template="Hello, {node_value}!")

        node = bag.get_node("greeting_0")
        result = bag.builder._render_value(node)

        assert result == "Hello, World!"

    def test_compile_callback(self):
        """_render_value calls compile_callback to modify context."""

        class Builder(BagBuilderBase):
            @element(compile_callback="uppercase_value")
            def loud(self): ...

            def uppercase_value(self, ctx):
                ctx["node_value"] = ctx["node_value"].upper()

        bag = Bag(builder=Builder)
        bag.loud(node_value="hello")

        node = bag.get_node("loud_0")
        result = bag.builder._render_value(node)

        assert result == "HELLO"

    def test_compile_format_schema(self):
        """_render_value applies compile_format from schema."""

        class Builder(BagBuilderBase):
            @element(compile_format="[{}]")
            def bracketed(self): ...

        bag = Bag(builder=Builder)
        bag.bracketed(node_value="content")

        node = bag.get_node("bracketed_0")
        result = bag.builder._render_value(node)

        assert result == "[content]"


# =============================================================================
# Tests for builder __str__ and __iter__ (coverage for lines 869, 901)
# =============================================================================


class TestBuilderStringRepresentation:
    """Tests for builder __str__ and __iter__."""

    def test_builder_str(self):
        """Builder __str__ returns schema structure."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = str(bag.builder)

        # Should include schema node
        assert "item" in result

    def test_builder_iter(self):
        """Builder __iter__ iterates over schema nodes."""

        class Builder(BagBuilderBase):
            @element()
            def alpha(self): ...

            @element()
            def beta(self): ...

        bag = Bag(builder=Builder)
        tags = [node.label for node in bag.builder]

        assert "alpha" in tags
        assert "beta" in tags


# =============================================================================
# Tests for _get_call_args_validations (coverage for lines 1141-1144)
# =============================================================================


class TestGetCallArgsValidations:
    """Tests for _get_call_args_validations."""

    def test_returns_none_for_unknown_tag(self):
        """_get_call_args_validations returns None for unknown tag."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.builder._get_call_args_validations("nonexistent")

        assert result is None

    def test_returns_validations_for_known_tag(self):
        """_get_call_args_validations returns validations for known tag."""

        class Builder(BagBuilderBase):
            @element()
            def item(self, name: str = None): ...

        bag = Bag(builder=Builder)
        result = bag.builder._get_call_args_validations("item")

        assert result is not None
        assert "name" in result


# =============================================================================
# Tests for compile method formats (coverage for compile method)
# =============================================================================


class TestBuilderCompile:
    """Tests for builder compile method."""

    def test_compile_json_format(self):
        """Builder compile with format='json'."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item(node_value="test")

        result = bag.builder.compile(format="json")

        # JSON output includes label and value
        assert "item_0" in result
        assert "test" in result

    def test_compile_unknown_format_raises(self):
        """Builder compile with unknown format raises ValueError."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)

        with pytest.raises(ValueError, match="Unknown format"):
            bag.builder.compile(format="unknown")
