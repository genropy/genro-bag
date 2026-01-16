# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for MarkdownBuilder.

Tests cover:
- Heading elements (h1-h6)
- Paragraph and text blocks
- Code blocks with language
- Tables with headers and rows
- Lists (ordered and unordered)
- Inline elements (bold, italic, link)
- compile() output
"""

from genro_bag import Bag
from genro_bag.builders import MarkdownBuilder


class TestMarkdownHeadings:
    """Tests for Markdown heading elements."""

    def test_h1(self):
        """h1 generates # prefix."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h1("Title")
        result = doc.builder.compile()
        assert result == "# Title"

    def test_h2(self):
        """h2 generates ## prefix."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h2("Subtitle")
        result = doc.builder.compile()
        assert result == "## Subtitle"

    def test_h3(self):
        """h3 generates ### prefix."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h3("Section")
        result = doc.builder.compile()
        assert result == "### Section"

    def test_multiple_headings(self):
        """Multiple headings separated by blank lines."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h1("Title")
        doc.h2("Subtitle")
        result = doc.builder.compile()
        assert "# Title" in result
        assert "## Subtitle" in result
        assert "\n\n" in result


class TestMarkdownParagraph:
    """Tests for Markdown paragraph element."""

    def test_paragraph(self):
        """p generates plain text."""
        doc = Bag(builder=MarkdownBuilder)
        doc.p("This is a paragraph.")
        result = doc.builder.compile()
        assert result == "This is a paragraph."

    def test_multiple_paragraphs(self):
        """Multiple paragraphs separated by blank lines."""
        doc = Bag(builder=MarkdownBuilder)
        doc.p("First paragraph.")
        doc.p("Second paragraph.")
        result = doc.builder.compile()
        assert "First paragraph." in result
        assert "Second paragraph." in result
        assert "\n\n" in result


class TestMarkdownCode:
    """Tests for Markdown code block element."""

    def test_code_block(self):
        """code generates fenced code block."""
        doc = Bag(builder=MarkdownBuilder)
        doc.code("print('hello')")
        result = doc.builder.compile()
        assert "```" in result
        assert "print('hello')" in result

    def test_code_block_with_language(self):
        """code with lang attribute adds language."""
        doc = Bag(builder=MarkdownBuilder)
        doc.code("def foo(): pass", lang="python")
        result = doc.builder.compile()
        assert "```python" in result
        assert "def foo(): pass" in result


class TestMarkdownBlockquote:
    """Tests for Markdown blockquote element."""

    def test_blockquote(self):
        """blockquote generates > prefix."""
        doc = Bag(builder=MarkdownBuilder)
        doc.blockquote("A quote.")
        result = doc.builder.compile()
        assert result == "> A quote."

    def test_blockquote_multiline(self):
        """blockquote handles multiple lines."""
        doc = Bag(builder=MarkdownBuilder)
        doc.blockquote("Line 1\nLine 2")
        result = doc.builder.compile()
        assert "> Line 1" in result
        assert "> Line 2" in result


class TestMarkdownHorizontalRule:
    """Tests for Markdown horizontal rule element."""

    def test_hr(self):
        """hr generates ---."""
        doc = Bag(builder=MarkdownBuilder)
        doc.hr()
        result = doc.builder.compile()
        assert result == "---"


class TestMarkdownTable:
    """Tests for Markdown table elements."""

    def test_simple_table(self):
        """Table with header and rows."""
        doc = Bag(builder=MarkdownBuilder)
        table = doc.table()
        header = table.tr()
        header.th("Name")
        header.th("Value")
        row = table.tr()
        row.td("foo")
        row.td("bar")

        result = doc.builder.compile()
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| foo | bar |" in result

    def test_table_multiple_rows(self):
        """Table with multiple data rows."""
        doc = Bag(builder=MarkdownBuilder)
        table = doc.table()
        header = table.tr()
        header.th("A")
        header.th("B")
        for i in range(3):
            row = table.tr()
            row.td(f"a{i}")
            row.td(f"b{i}")

        result = doc.builder.compile()
        assert "| a0 | b0 |" in result
        assert "| a1 | b1 |" in result
        assert "| a2 | b2 |" in result


class TestMarkdownLists:
    """Tests for Markdown list elements."""

    def test_unordered_list(self):
        """ul generates - prefix."""
        doc = Bag(builder=MarkdownBuilder)
        ul = doc.ul()
        ul.li("Item 1")
        ul.li("Item 2")
        ul.li("Item 3")

        result = doc.builder.compile()
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_ordered_list(self):
        """ol generates numbered prefix."""
        doc = Bag(builder=MarkdownBuilder)
        ol = doc.ol()
        ol.li("First")
        ol.li("Second")
        ol.li("Third")

        result = doc.builder.compile()
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result


class TestMarkdownInline:
    """Tests for Markdown inline elements."""

    def test_link(self):
        """link generates [text](href)."""
        doc = Bag(builder=MarkdownBuilder)
        doc.link("Click here", href="https://example.com")

        result = doc.builder.compile()
        assert "[Click here](https://example.com)" in result

    def test_img(self):
        """img generates ![alt](src)."""
        doc = Bag(builder=MarkdownBuilder)
        doc.img(src="image.png", alt="My Image")

        result = doc.builder.compile()
        assert "![My Image](image.png)" in result

    def test_bold(self):
        """bold generates **text**."""
        doc = Bag(builder=MarkdownBuilder)
        doc.bold("important")

        result = doc.builder.compile()
        assert "**important**" in result

    def test_italic(self):
        """italic generates *text*."""
        doc = Bag(builder=MarkdownBuilder)
        doc.italic("emphasis")

        result = doc.builder.compile()
        assert "*emphasis*" in result


class TestMarkdownCompile:
    """Tests for MarkdownBuilder.compile()."""

    def test_compile_returns_string(self):
        """compile() returns markdown string."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h1("Test")
        doc.p("Content")

        result = doc.builder.compile()
        assert isinstance(result, str)
        assert "# Test" in result
        assert "Content" in result

    def test_compile_to_file(self, tmp_path):
        """compile() can write to file."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h1("File Test")

        output_file = tmp_path / "test.md"
        result = doc.builder.compile(destination=output_file)

        assert output_file.exists()
        assert output_file.read_text() == result


class TestMarkdownCompleteDocument:
    """Tests for complete Markdown documents."""

    def test_full_document(self):
        """Build a complete document with multiple elements."""
        doc = Bag(builder=MarkdownBuilder)
        doc.h1("My Document")
        doc.p("Introduction paragraph.")

        doc.h2("Code Example")
        doc.code("x = 1 + 2", lang="python")

        doc.h2("Data Table")
        table = doc.table()
        header = table.tr()
        header.th("Column A")
        header.th("Column B")
        row = table.tr()
        row.td("value1")
        row.td("value2")

        doc.h2("Steps")
        ol = doc.ol()
        ol.li("First step")
        ol.li("Second step")

        result = doc.builder.compile()

        assert "# My Document" in result
        assert "## Code Example" in result
        assert "```python" in result
        assert "| Column A | Column B |" in result
        assert "1. First step" in result
