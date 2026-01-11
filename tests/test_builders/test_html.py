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
        """HtmlBuilder knows all HTML5 tags via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Check tags exist in schema using 'in' operator
        assert 'div' in bag.builder
        assert 'span' in bag.builder
        assert 'p' in bag.builder
        assert 'a' in bag.builder
        assert 'html' in bag.builder

    def test_void_elements(self):
        """HtmlBuilder knows void elements via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Void elements exist in schema
        assert 'br' in bag.builder
        assert 'hr' in bag.builder
        assert 'img' in bag.builder
        assert 'input' in bag.builder
        assert 'meta' in bag.builder
        assert 'link' in bag.builder

    def test_create_div(self):
        """Creates div element."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id='main', class_='container')

        assert isinstance(div, Bag)
        node = bag.get_node('div_0')
        assert node.tag == 'div'
        assert node.attr.get('id') == 'main'
        assert node.attr.get('class_') == 'container'

    def test_create_void_element(self):
        """Void elements get empty value automatically."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.br()

        assert node.value == ''
        assert node.tag == 'br'

    def test_create_element_with_value(self):
        """Elements can have text content."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.p(value='Hello, World!')

        assert node.value == 'Hello, World!'
        assert node.tag == 'p'

    def test_nested_elements(self):
        """Creates nested HTML structure."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id='main')
        div.p(value='Paragraph text')
        div.span(value='Span text')

        assert len(div) == 2
        assert div.get_node('p_0').value == 'Paragraph text'
        assert div.get_node('span_0').value == 'Span text'

    def test_invalid_tag_raises(self):
        """Invalid tag raises AttributeError."""
        bag = Bag(builder=HtmlBuilder)

        with pytest.raises(AttributeError, match="has no element 'notarealtag'"):
            bag.notarealtag()

    def test_builder_inheritance_in_nested(self):
        """Nested bags inherit builder."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div()
        div.p(value='test')

        assert div.builder is bag.builder

    def test_auto_label_generation(self):
        """Labels are auto-generated uniquely."""
        bag = Bag(builder=HtmlBuilder)
        bag.div()
        bag.div()
        bag.div()

        labels = list(bag.keys())
        assert labels == ['div_0', 'div_1', 'div_2']


class TestHtmlBuilderCompile:
    """Tests for HtmlBuilder.compile()."""

    def test_compile_simple(self):
        """compile() generates HTML string."""
        bag = Bag(builder=HtmlBuilder)
        bag.p(value='Hello')

        html = bag.builder.compile()

        assert '<p>Hello</p>' in html

    def test_compile_nested(self):
        """compile() handles nested elements."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id='main')
        div.p(value='Content')

        html = bag.builder.compile()

        assert '<div id="main">' in html
        assert '<p>Content</p>' in html
        assert '</div>' in html

    def test_compile_void_elements(self):
        """Void elements render without closing tag."""
        bag = Bag(builder=HtmlBuilder)
        bag.br()
        bag.meta(charset='utf-8')

        html = bag.builder.compile()

        assert '<br>' in html
        assert '</br>' not in html
        assert '<meta charset="utf-8">' in html
        assert '</meta>' not in html

    def test_compile_to_file(self, tmp_path):
        """compile() can save to file."""
        bag = Bag(builder=HtmlBuilder)
        bag.p(value='Content')

        dest = tmp_path / 'test.html'
        result = bag.builder.compile(destination=dest)

        assert dest.exists()
        assert '<p>Content</p>' in dest.read_text()
        assert result == '<p>Content</p>'

    def test_compile_page_structure(self):
        """compile() generates complete page structure."""
        page = Bag(builder=HtmlBuilder)
        head = page.head()
        head.title(value='Test')
        head.meta(charset='utf-8')
        body = page.body()
        body.div(id='main').p(value='Hello')

        html = page.builder.compile()

        assert '<head>' in html
        assert '</head>' in html
        assert '<body>' in html
        assert '</body>' in html
        assert '<title>Test</title>' in html
        assert 'id="main"' in html
        assert '<p>Hello</p>' in html


class TestHtmlBuilderIntegration:
    """Integration tests for HTML builder with Bag."""

    def test_complex_html_structure(self):
        """Creates complex HTML structure."""
        page = Bag(builder=HtmlBuilder)

        # Head
        head = page.head()
        head.meta(charset='utf-8')
        head.title(value='My Website')
        head.link(rel='stylesheet', href='style.css')

        # Body
        body = page.body()
        header = body.header(id='header')
        header.h1(value='Welcome')
        nav = header.nav()
        ul = nav.ul()
        ul.li(value='Home')
        ul.li(value='About')
        ul.li(value='Contact')

        main = body.main(id='content')
        article = main.article()
        article.h2(value='Article Title')
        article.p(value='Article content goes here.')

        footer = body.footer()
        footer.p(value='Copyright 2025')

        # Verify structure
        assert len(head) == 3
        assert len(body) == 3  # header, main, footer

        html = page.builder.compile()
        assert '<header id="header">' in html
        assert '<nav>' in html
        assert '<ul>' in html
        assert '<li>Home</li>' in html
        assert '<main id="content">' in html
        assert '<article>' in html
        assert '<footer>' in html
