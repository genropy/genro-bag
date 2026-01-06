# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for HtmlBuilder."""

import pytest

from genro_bag import Bag
from genro_bag.builders import HtmlBuilder, HtmlHeadBuilder, HtmlBodyBuilder, HtmlPage


class TestHtmlBuilder:
    """Tests for HtmlBuilder."""

    def test_create_bag_with_html_builder(self):
        """Creates Bag with HtmlBuilder."""
        builder = HtmlBuilder()
        bag = Bag(builder=builder)
        assert bag.builder is builder

    def test_valid_html_tags(self):
        """HtmlBuilder knows all HTML5 tags."""
        builder = HtmlBuilder()
        assert 'div' in builder.ALL_TAGS
        assert 'span' in builder.ALL_TAGS
        assert 'p' in builder.ALL_TAGS
        assert 'a' in builder.ALL_TAGS
        assert 'html' in builder.ALL_TAGS

    def test_void_elements(self):
        """HtmlBuilder knows void elements."""
        builder = HtmlBuilder()
        assert 'br' in builder.VOID_ELEMENTS
        assert 'hr' in builder.VOID_ELEMENTS
        assert 'img' in builder.VOID_ELEMENTS
        assert 'input' in builder.VOID_ELEMENTS
        assert 'meta' in builder.VOID_ELEMENTS
        assert 'link' in builder.VOID_ELEMENTS

    def test_create_div(self):
        """Creates div element."""
        bag = Bag(builder=HtmlBuilder())
        div = bag.div(id='main', class_='container')

        assert isinstance(div, Bag)
        node = bag.get_node('div_0')
        assert node.tag == 'div'
        assert node.attr.get('id') == 'main'
        assert node.attr.get('class_') == 'container'

    def test_create_void_element(self):
        """Void elements get empty value automatically."""
        bag = Bag(builder=HtmlBuilder())
        node = bag.br()

        assert node.value == ''
        assert node.tag == 'br'

    def test_create_element_with_value(self):
        """Elements can have text content."""
        bag = Bag(builder=HtmlBuilder())
        node = bag.p(value='Hello, World!')

        assert node.value == 'Hello, World!'
        assert node.tag == 'p'

    def test_nested_elements(self):
        """Creates nested HTML structure."""
        bag = Bag(builder=HtmlBuilder())
        div = bag.div(id='main')
        p = div.p(value='Paragraph text')
        span = div.span(value='Span text')

        assert len(div) == 2
        assert div.get_node('p_0').value == 'Paragraph text'
        assert div.get_node('span_0').value == 'Span text'

    def test_invalid_tag_raises(self):
        """Invalid tag raises AttributeError."""
        bag = Bag(builder=HtmlBuilder())

        with pytest.raises(AttributeError, match="has no attribute 'notarealtag'"):
            bag.notarealtag()

    def test_builder_inheritance_in_nested(self):
        """Nested bags inherit builder."""
        bag = Bag(builder=HtmlBuilder())
        div = bag.div()
        p = div.p(value='test')

        assert div.builder is bag.builder

    def test_auto_label_generation(self):
        """Labels are auto-generated uniquely."""
        bag = Bag(builder=HtmlBuilder())
        bag.div()
        bag.div()
        bag.div()

        labels = list(bag.keys())
        assert labels == ['div_0', 'div_1', 'div_2']


class TestHtmlHeadBuilder:
    """Tests for HtmlHeadBuilder."""

    def test_creates_head_elements(self):
        """HtmlHeadBuilder creates head elements."""
        bag = Bag(builder=HtmlHeadBuilder())
        bag.title(value='My Page')
        bag.meta(charset='utf-8')
        bag.link(rel='stylesheet', href='style.css')

        assert len(bag) == 3
        assert bag.get_node('title_0').value == 'My Page'


class TestHtmlBodyBuilder:
    """Tests for HtmlBodyBuilder."""

    def test_creates_body_elements(self):
        """HtmlBodyBuilder creates body elements."""
        bag = Bag(builder=HtmlBodyBuilder())
        bag.h1(value='Welcome')
        div = bag.div(id='content')
        div.p(value='Content here')

        assert len(bag) == 2


class TestHtmlPage:
    """Tests for HtmlPage."""

    def test_creates_page_structure(self):
        """HtmlPage creates html/head/body structure."""
        page = HtmlPage()

        assert page.html is not None
        assert page.head is not None
        assert page.body is not None
        assert 'head' in page.html._nodes
        assert 'body' in page.html._nodes

    def test_head_has_builder(self):
        """Head has HtmlHeadBuilder."""
        page = HtmlPage()
        assert isinstance(page.head.builder, HtmlHeadBuilder)

    def test_body_has_builder(self):
        """Body has HtmlBodyBuilder."""
        page = HtmlPage()
        assert isinstance(page.body.builder, HtmlBodyBuilder)

    def test_add_elements_to_head(self):
        """Can add elements to head."""
        page = HtmlPage()
        page.head.title(value='Test Page')
        page.head.meta(charset='utf-8')

        assert len(page.head) == 2

    def test_add_elements_to_body(self):
        """Can add elements to body."""
        page = HtmlPage()
        div = page.body.div(id='main')
        div.h1(value='Hello')
        div.p(value='World')

        assert len(page.body) == 1
        assert len(div) == 2

    def test_to_html_output(self):
        """to_html generates valid HTML structure."""
        page = HtmlPage()
        page.head.title(value='Test')
        page.body.div(id='main').p(value='Hello')

        html = page.to_html()

        assert '<!DOCTYPE html>' in html
        assert '<html>' in html
        assert '</html>' in html
        assert '<head>' in html
        assert '</head>' in html
        assert '<body>' in html
        assert '</body>' in html
        assert '<title>Test</title>' in html
        assert 'id="main"' in html
        assert '<p>Hello</p>' in html

    def test_to_html_void_elements(self):
        """Void elements render without closing tag."""
        page = HtmlPage()
        page.head.meta(charset='utf-8')
        page.body.br()

        html = page.to_html()

        assert '<meta charset="utf-8">' in html
        assert '</meta>' not in html
        assert '<br>' in html
        assert '</br>' not in html

    def test_to_html_saves_to_file(self, tmp_path):
        """to_html can save to file."""
        page = HtmlPage()
        page.head.title(value='Test')
        page.body.p(value='Content')

        result = page.to_html(filename='test.html', output_dir=str(tmp_path))

        assert result == str(tmp_path / 'test.html')
        content = (tmp_path / 'test.html').read_text()
        assert '<!DOCTYPE html>' in content


class TestHtmlBuilderIntegration:
    """Integration tests for HTML builder with Bag."""

    def test_complex_html_structure(self):
        """Creates complex HTML structure."""
        page = HtmlPage()

        # Head
        page.head.meta(charset='utf-8')
        page.head.title(value='My Website')
        page.head.link(rel='stylesheet', href='style.css')

        # Body
        header = page.body.header(id='header')
        header.h1(value='Welcome')
        nav = header.nav()
        ul = nav.ul()
        ul.li(value='Home')
        ul.li(value='About')
        ul.li(value='Contact')

        main = page.body.main(id='content')
        article = main.article()
        article.h2(value='Article Title')
        article.p(value='Article content goes here.')

        footer = page.body.footer()
        footer.p(value='Copyright 2025')

        # Verify structure
        assert len(page.head) == 3
        assert len(page.body) == 3  # header, main, footer

        html = page.to_html()
        assert '<header id="header">' in html
        assert '<nav>' in html
        assert '<ul>' in html
        assert '<li>Home</li>' in html
        assert '<main id="content">' in html
        assert '<article>' in html
        assert '<footer>' in html
