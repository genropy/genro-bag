# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for HtmlBuilder."""

import pytest

from genro_bag import Bag
from genro_bag.builders import HtmlBuilder


class TestHtmlBuilder:
    """Tests for HtmlBuilder."""

    def test_create_bag_with_html_builder(self):
        """Creates Bag with HtmlBuilder."""
        bag = Bag(builder=HtmlBuilder)
        assert isinstance(bag.builder, HtmlBuilder)

    def test_valid_html_tags(self):
        """HtmlBuilder knows common HTML5 tags via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Check tags exist in schema using 'in' operator
        assert "div" in bag.builder
        assert "span" in bag.builder
        assert "p" in bag.builder
        assert "html" in bag.builder

    def test_void_elements(self):
        """HtmlBuilder knows void elements via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Void elements exist in schema
        assert "br" in bag.builder
        assert "hr" in bag.builder
        assert "img" in bag.builder

    def test_create_div(self):
        """Creates div element, returns BagNode."""
        from genro_bag.bagnode import BagNode

        bag = Bag(builder=HtmlBuilder)
        node = bag.div(id="main", class_="container")

        assert isinstance(node, BagNode)
        assert node.tag == "div"
        assert node.attr.get("id") == "main"
        assert node.attr.get("class_") == "container"

    def test_create_void_element(self):
        """Void elements have None value by default."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.br()

        assert node.value is None
        assert node.tag == "br"

    def test_create_element_with_value(self):
        """Elements can have text content."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.p("Hello, World!")

        assert node.value == "Hello, World!"
        assert node.tag == "p"

    def test_nested_elements(self):
        """Creates nested HTML structure."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id="main")
        div.p("Paragraph text")
        div.span("Span text")

        assert len(div.value) == 2
        assert div.value.get_node("p_0").value == "Paragraph text"
        assert div.value.get_node("span_0").value == "Span text"

    def test_invalid_tag_raises(self):
        """Invalid tag raises AttributeError."""
        bag = Bag(builder=HtmlBuilder)

        with pytest.raises(AttributeError, match="has no element 'notarealtag'"):
            bag.notarealtag()

    def test_builder_inheritance_in_nested(self):
        """Nested bags inherit builder."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div()
        div.p("test")

        assert div.value.builder is bag.builder

    def test_auto_label_generation(self):
        """Labels are auto-generated uniquely."""
        bag = Bag(builder=HtmlBuilder)
        bag.div()
        bag.div()
        bag.div()

        labels = list(bag.keys())
        assert labels == ["div_0", "div_1", "div_2"]


class TestHtmlBuilderCompile:
    """Tests for HtmlBuilder.compile()."""

    def test_compile_simple(self):
        """compile() generates HTML string."""
        bag = Bag(builder=HtmlBuilder)
        bag.p("Hello")

        html = bag.builder.compile()

        assert "<p>Hello</p>" in html

    def test_compile_nested(self):
        """compile() handles nested elements."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id="main")
        div.p("Content")

        html = bag.builder.compile()

        assert '<div id="main">' in html
        assert "<p>Content</p>" in html
        assert "</div>" in html

    def test_compile_void_elements(self):
        """Void elements render without closing tag."""
        bag = Bag(builder=HtmlBuilder)
        bag.br()
        bag.meta(charset="utf-8")

        html = bag.builder.compile()

        assert "<br>" in html
        assert "</br>" not in html
        assert '<meta charset="utf-8">' in html
        assert "</meta>" not in html

    def test_compile_to_file(self, tmp_path):
        """compile() can save to file."""
        bag = Bag(builder=HtmlBuilder)
        bag.p("Content")

        dest = tmp_path / "test.html"
        result = bag.builder.compile(destination=dest)

        assert dest.exists()
        assert "<p>Content</p>" in dest.read_text()
        assert result == "<p>Content</p>"

    def test_compile_page_structure(self):
        """compile() generates complete page structure."""
        page = Bag(builder=HtmlBuilder)
        head = page.head()
        head.title("Test")
        head.meta(charset="utf-8")
        body = page.body()
        body.div(id="main").p("Hello")

        html = page.builder.compile()

        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html
        assert "<title>Test</title>" in html
        assert 'id="main"' in html
        assert "<p>Hello</p>" in html


class TestHtmlBuilderIntegration:
    """Integration tests for HTML builder with Bag."""

    def test_complex_html_structure(self):
        """Creates complex HTML structure."""
        page = Bag(builder=HtmlBuilder)

        # Head
        head = page.head()
        head.meta(charset="utf-8")
        head.title("My Website")
        head.link(rel="stylesheet", href="style.css")

        # Body
        body = page.body()
        header = body.header(id="header")
        header.h1("Welcome")
        nav = header.nav()
        ul = nav.ul()
        ul.li("Home")
        ul.li("About")
        ul.li("Contact")

        main = body.main(id="content")
        article = main.article()
        article.h2("Article Title")
        article.p("Article content goes here.")

        footer = body.footer()
        footer.p("Copyright 2025")

        # Verify structure
        assert len(head.value) == 3
        assert len(body.value) == 3  # header, main, footer

        html = page.builder.compile()
        assert '<header id="header">' in html
        assert "<nav>" in html
        assert "<ul>" in html
        assert "<li>Home</li>" in html
        assert '<main id="content">' in html
        assert "<article>" in html
        assert "<footer>" in html
