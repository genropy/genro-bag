# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for @component decorator.

Tests cover:
- @component decorator creates composite structures
- Component receives new Bag with builder
- sub_tags='' returns parent bag (closed/leaf)
- sub_tags defined or absent returns component node (open/container)
- parent_tags validation works same as element
- Nested components work correctly
- Builder override works for internal bag
- SchemaBuilder cannot use @component (code-based only)
"""

import pytest

from genro_bag import Bag, BagBuilderBase
from genro_bag.builder import SchemaBuilder
from genro_bag.builders import component, element


# =============================================================================
# Basic @component decorator tests
# =============================================================================


class TestComponentDecoratorBasic:
    """Basic tests for @component decorator."""

    def test_component_creates_schema_entry(self):
        """@component creates entry in schema with handler_name."""

        class Builder(BagBuilderBase):
            @component()
            def myform(self, component: Bag, **kwargs):
                component.field()
                return component

            @element()
            def field(self): ...

            @element()
            def div(self): ...

        # Schema should have myform
        node = Builder._class_schema.get_node("myform")
        assert node is not None
        # Components use handler_name instead of adapter_name
        assert node.attr.get("handler_name") is not None

    def test_component_receives_new_bag(self):
        """Component method receives a new Bag with builder."""
        received_bag = None

        class Builder(BagBuilderBase):
            @component()
            def myform(self, component: Bag, **kwargs):
                nonlocal received_bag
                received_bag = component
                return component

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.myform()

        assert received_bag is not None
        assert isinstance(received_bag, Bag)
        # Each Bag gets its own builder instance, but same class
        assert type(received_bag.builder) is type(bag.builder)

    def test_component_populates_bag(self):
        """Component populates the internal bag and it becomes node value."""

        class Builder(BagBuilderBase):
            @component()
            def myform(self, component: Bag, **kwargs):
                component.field(name="field1")
                component.field(name="field2")
                return component

            @element()
            def field(self): ...

        bag = Bag(builder=Builder)
        bag.myform()

        # Check the component was added
        node = bag.get_node("myform_0")
        assert node is not None
        assert node.tag == "myform"
        # The value should be the populated bag
        assert isinstance(node.value, Bag)
        assert len(node.value) == 2
        # Check both are field elements
        for child in node.value.nodes:
            assert child.tag == "field"

    def test_component_uses_builder_elements(self):
        """Component can use builder elements inside."""

        class Builder(BagBuilderBase):
            @component()
            def myform(self, component: Bag, **kwargs):
                component.input(name="field1")
                component.input(name="field2")
                return component

            @element()
            def input(self): ...

        bag = Bag(builder=Builder)
        bag.myform()

        node = bag.get_node("myform_0")
        assert isinstance(node.value, Bag)
        assert len(node.value) == 2
        # Check both are input elements
        for child in node.value.nodes:
            assert child.tag == "input"


# =============================================================================
# Tests for sub_tags return behavior
# =============================================================================


class TestComponentSubTagsReturnBehavior:
    """Tests for sub_tags controlling return value."""

    def test_void_sub_tags_returns_parent(self):
        """sub_tags='' (void) returns parent bag for chaining at same level."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def closed_form(self, component: Bag, **kwargs):
                component.internal()
                return component

            @element()
            def internal(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        result = bag.closed_form()

        # Should return parent bag (root in this case)
        assert result is bag
        # Can continue at same level
        result.span()
        assert len(bag) == 2  # closed_form + span

    def test_defined_sub_tags_returns_node(self):
        """sub_tags='item' returns something for adding children."""

        class Builder(BagBuilderBase):
            @component(sub_tags="item")
            def mylist(self, component: Bag, **kwargs):
                component.header()
                return component

            @element()
            def header(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.mylist()

        # Should NOT return parent bag
        assert result is not bag
        # Can add 'item' children with known label
        result.item(node_label="added_item")
        # Check the final structure
        node = bag.get_node("mylist_0")
        assert len(node.value) == 2  # header + item
        assert node.value.get_node("added_item") is not None

    def test_absent_sub_tags_returns_node(self):
        """No sub_tags (absent) returns internal bag - open container."""

        class Builder(BagBuilderBase):
            @component()  # No sub_tags - open container
            def container(self, component: Bag, **kwargs):
                component.internal()
                return component

            @element()
            def internal(self): ...

            @element()
            def anything(self): ...

        bag = Bag(builder=Builder)
        result = bag.container()

        # Should NOT return parent bag
        assert result is not bag
        # Can add children with known label
        result.anything(node_label="added_child")
        # Check the final structure
        node = bag.get_node("container_0")
        assert len(node.value) == 2  # internal + anything
        assert node.value.get_node("added_child") is not None

    def test_none_sub_tags_returns_node(self):
        """sub_tags=None explicitly returns internal bag - open container."""

        class Builder(BagBuilderBase):
            @component(sub_tags=None)
            def container(self, component: Bag, **kwargs):
                return component

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.container()

        # Should NOT return parent bag
        assert result is not bag
        # Can add children with known label
        result.item(node_label="added_item")
        # Check the final structure
        node = bag.get_node("container_0")
        assert len(node.value) == 1  # item
        assert node.value.get_node("added_item") is not None


# =============================================================================
# Tests for parent_tags validation
# =============================================================================


class TestComponentParentTags:
    """Tests for parent_tags validation on components."""

    def test_valid_parent_allowed(self):
        """Component with parent_tags can be placed in valid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def div(self): ...

            @component(sub_tags="", parent_tags="div")
            def myform(self, component: Bag, **kwargs):
                component.field()
                return component

            @element()
            def field(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()
        div.myform()  # Should not raise

        assert len(div.value) == 1

    def test_invalid_parent_rejected(self):
        """Component with parent_tags cannot be placed in invalid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform,span")
            def div(self): ...

            @element(sub_tags="myform")
            def section(self): ...

            @component(sub_tags="", parent_tags="section")
            def myform(self, component: Bag, **kwargs):
                return component

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="parent_tags requires"):
            div.myform()  # div is not valid parent

    def test_parent_tags_at_root_rejected(self):
        """Component with parent_tags cannot be placed at root."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def container(self): ...

            @component(sub_tags="", parent_tags="container")
            def myform(self, component: Bag, **kwargs):
                return component

        bag = Bag(builder=Builder)

        with pytest.raises(ValueError, match="parent_tags requires"):
            bag.myform()  # root not valid

    def test_multiple_parent_tags(self):
        """Component can have multiple valid parents."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def div(self): ...

            @element(sub_tags="myform")
            def section(self): ...

            @component(sub_tags="", parent_tags="div, section")
            def myform(self, component: Bag, **kwargs):
                return component

        bag = Bag(builder=Builder)

        div = bag.div()
        div.myform()  # OK

        section = bag.section()
        section.myform()  # OK

        assert len(div.value) == 1
        assert len(section.value) == 1




# =============================================================================
# Tests for nested components
# =============================================================================


class TestNestedComponents:
    """Tests for using components inside components."""

    def test_component_uses_other_component(self):
        """Component can use another component internally."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def inner(self, component: Bag, **kwargs):
                component.set_item("inner_data", "value")
                return component

            @component(sub_tags="")
            def outer(self, component: Bag, **kwargs):
                component.inner()  # Use another component
                component.set_item("outer_data", "value")
                return component

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.outer()

        outer_node = bag.get_node("outer_0")
        assert isinstance(outer_node.value, Bag)
        # Should have inner component + outer_data
        assert len(outer_node.value) == 2
        # Inner should be a component node
        inner_node = outer_node.value.get_node("inner_0")
        assert inner_node is not None
        assert inner_node.tag == "inner"

    def test_nested_component_chain(self):
        """Multiple levels of component nesting."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def level3(self, component: Bag, **kwargs):
                component.set_item("l3", "data")
                return component

            @component(sub_tags="")
            def level2(self, component: Bag, **kwargs):
                component.level3()
                return component

            @component(sub_tags="")
            def level1(self, component: Bag, **kwargs):
                component.level2()
                return component

        bag = Bag(builder=Builder)
        bag.level1()

        # Navigate through nesting
        l1 = bag.get_node("level1_0")
        assert l1.tag == "level1"
        l2 = l1.value.get_node("level2_0")
        assert l2.tag == "level2"
        l3 = l2.value.get_node("level3_0")
        assert l3.tag == "level3"


# =============================================================================
# Tests for builder override
# =============================================================================


class TestComponentBuilderOverride:
    """Tests for builder override in components."""

    def test_component_with_different_builder(self):
        """Component can use a different builder for its internal bag."""

        class InnerBuilder(BagBuilderBase):
            @element()
            def special(self): ...

        class OuterBuilder(BagBuilderBase):
            @component(builder=InnerBuilder)
            def with_inner(self, component: Bag, **kwargs):
                # comp should have InnerBuilder
                component.special()  # This should work
                return component

            @element()
            def outer_elem(self): ...

        bag = Bag(builder=OuterBuilder)
        result = bag.with_inner()

        # result is the internal bag, not the node
        # The component's internal bag uses InnerBuilder
        assert isinstance(result.builder, InnerBuilder)
        # Has special element
        assert result.get_node("special_0") is not None

    def test_component_builder_override_affects_children(self):
        """Open component with builder override: subsequent additions use new builder."""

        class ChildBuilder(BagBuilderBase):
            @element()
            def child_elem(self): ...

        class ParentBuilder(BagBuilderBase):
            @component(sub_tags="child_elem", builder=ChildBuilder)
            def container(self, component: Bag, **kwargs):
                return component

            @element()
            def parent_elem(self): ...

        bag = Bag(builder=ParentBuilder)
        container = bag.container()

        # container is the internal bag, not the node
        # Now additions to container use ChildBuilder
        container.child_elem(node_label="added_child")  # Should work
        assert container.get_node("added_child") is not None


# =============================================================================
# Tests for SchemaBuilder restrictions
# =============================================================================


class TestSchemaBuilderCannotUseComponent:
    """Tests that SchemaBuilder cannot use @component decorator."""

    def test_schema_builder_no_component_method(self):
        """SchemaBuilder does not have component() method."""
        schema = Bag(builder=SchemaBuilder)

        # SchemaBuilder should not have component capability
        with pytest.raises(AttributeError):
            schema.component()

    def test_component_requires_code_handler(self):
        """@component decorator requires actual code - ellipsis not allowed."""

        with pytest.raises((ValueError, TypeError)):

            class Builder(BagBuilderBase):
                @component()
                def mycomp(self, component: Bag): ...  # Ellipsis body - not allowed


# =============================================================================
# Tests for component attributes
# =============================================================================


class TestComponentAttributes:
    """Tests for passing attributes to components."""

    def test_component_receives_kwargs(self):
        """Component receives kwargs passed at call time."""
        received_kwargs = {}

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, component: Bag, title=None, **kwargs):
                nonlocal received_kwargs
                received_kwargs = {"title": title, **kwargs}
                return component

        bag = Bag(builder=Builder)
        bag.myform(title="My Form", extra="data")

        assert received_kwargs["title"] == "My Form"
        assert received_kwargs["extra"] == "data"

    def test_component_attrs_stored_on_node(self):
        """Component attributes are stored on the node."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, component: Bag, title=None, **kwargs):
                return {"node_value": component, "title": title, **kwargs}

        bag = Bag(builder=Builder)
        bag.myform(title="Form Title", css_class="my-form")

        node = bag.get_node("myform_0")
        assert node.attr.get("title") == "Form Title"
        assert node.attr.get("css_class") == "my-form"


# =============================================================================
# Tests for validation on component kwargs
# =============================================================================


class TestComponentKwargsValidation:
    """Tests for kwargs validation on components."""

    def test_component_validates_typed_kwargs(self):
        """Component validates typed kwargs before method execution."""
        from typing import Annotated

        from genro_bag.builders import Range

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(
                self, component: Bag, cols: Annotated[int, Range(ge=1, le=12)] = None, **kwargs
            ):
                return component

        bag = Bag(builder=Builder)

        # Valid
        bag.myform(cols=6)

        # Invalid
        with pytest.raises(ValueError, match="must be >= 1"):
            bag.myform(cols=0)

        with pytest.raises(ValueError, match="must be <= 12"):
            bag.myform(cols=20)


# =============================================================================
# Tests for component with elements mixed
# =============================================================================


class TestComponentWithElements:
    """Tests for mixing components and elements."""

    def test_component_and_elements_in_same_builder(self):
        """Builder can have both components and elements."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def form(self, component: Bag, **kwargs):
                component.input(name="field1")
                return component

            @element()
            def input(self): ...

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.div()
        bag.form()
        bag.div()

        assert len(bag) == 3
        nodes = list(bag.nodes)
        assert nodes[0].tag == "div"
        assert nodes[1].tag == "form"
        assert nodes[2].tag == "div"

    def test_component_inside_element(self):
        """Component can be placed inside an element."""

        class Builder(BagBuilderBase):
            @element(sub_tags="form")
            def div(self): ...

            @component(sub_tags="")
            def form(self, component: Bag, **kwargs):
                component.set_item("field", "value")
                return component

        bag = Bag(builder=Builder)
        div = bag.div()
        div.form()

        assert len(div.value) == 1
        form_node = div.value.get_node("form_0")
        assert form_node.tag == "form"
