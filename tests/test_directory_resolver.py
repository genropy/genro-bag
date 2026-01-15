# Copyright 2025 Softwell S.r.l. - Genropy Team
# Licensed under the Apache License, Version 2.0

"""Tests for DirectoryResolver."""

import pytest

from genro_bag import Bag
from genro_bag.resolvers.directory_resolver import DirectoryResolver


@pytest.fixture(autouse=True)
def reset_smartasync_cache():
    """Reset smartasync cache before each test."""
    from genro_bag.resolver import BagResolver

    if hasattr(DirectoryResolver.load, "_smartasync_reset_cache"):
        DirectoryResolver.load._smartasync_reset_cache()
    if hasattr(BagResolver.__call__, "_smartasync_reset_cache"):
        BagResolver.__call__._smartasync_reset_cache()
    yield


class TestDirectoryResolverBasic:
    """Basic DirectoryResolver functionality."""

    def test_load_empty_directory(self, tmp_path):
        """Loading an empty directory returns empty Bag."""
        resolver = DirectoryResolver(str(tmp_path))
        result = resolver.load()
        assert isinstance(result, Bag)
        assert len(result) == 0

    def test_load_directory_with_files(self, tmp_path):
        """Loading directory with files creates nodes."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        assert len(result) == 2
        assert "file1_txt" in result
        assert "file2_txt" in result

    def test_load_nonexistent_directory(self, tmp_path):
        """Loading nonexistent directory returns empty Bag."""
        resolver = DirectoryResolver(str(tmp_path / "nonexistent"))
        result = resolver.load()
        assert len(result) == 0

    def test_node_attributes(self, tmp_path):
        """Nodes have expected file attributes."""
        filepath = tmp_path / "test.txt"
        filepath.write_text("test content")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        node = result.get_node("test_txt")
        assert node.get_attr("file_name") == "test"
        assert node.get_attr("file_ext") == "txt"
        assert node.get_attr("abs_path") == str(filepath)
        assert node.get_attr("size") == len("test content")
        assert node.get_attr("mtime") is not None


class TestDirectoryResolverFiltering:
    """File filtering functionality."""

    def test_invisible_files_excluded_by_default(self, tmp_path):
        """Hidden files (starting with .) are excluded by default."""
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden.txt").write_text("hidden")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        assert len(result) == 1
        assert "visible_txt" in result

    def test_invisible_files_included_when_enabled(self, tmp_path):
        """Hidden files included when invisible=True."""
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden.txt").write_text("hidden")

        resolver = DirectoryResolver(str(tmp_path), ext="txt", invisible=True)
        result = resolver.load()

        assert len(result) == 2

    def test_journal_files_excluded(self, tmp_path):
        """Journal files (#file#, file~) are always excluded."""
        (tmp_path / "normal.txt").write_text("normal")
        (tmp_path / "#journal#").write_text("journal")
        (tmp_path / "backup~").write_text("backup")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        assert len(result) == 1
        assert "normal_txt" in result

    def test_include_filter(self, tmp_path):
        """Include filter limits files to matching patterns."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "other.txt").write_text("3")

        resolver = DirectoryResolver(str(tmp_path), ext="txt", include="file*")
        result = resolver.load()

        assert len(result) == 2
        assert "file1_txt" in result
        assert "file2_txt" in result
        assert "other_txt" not in result

    def test_exclude_filter(self, tmp_path):
        """Exclude filter removes matching files."""
        (tmp_path / "keep.txt").write_text("keep")
        (tmp_path / "skip.txt").write_text("skip")

        resolver = DirectoryResolver(str(tmp_path), ext="txt", exclude="skip*")
        result = resolver.load()

        assert len(result) == 1
        assert "keep_txt" in result


class TestDirectoryResolverExtensions:
    """Extension handling."""

    def test_multiple_extensions(self, tmp_path):
        """Multiple extensions can be specified."""
        (tmp_path / "doc.txt").write_text("text")
        (tmp_path / "doc.md").write_text("markdown")
        (tmp_path / "doc.json").write_text("{}")

        resolver = DirectoryResolver(str(tmp_path), ext="txt,md")
        result = resolver.load()

        # Only txt and md should be processed (json uses default processor)
        labels = list(result.keys())
        assert "doc_txt" in labels
        assert "doc_md" in labels

    def test_dropext_removes_extension_from_label(self, tmp_path):
        """dropext=True omits extension from node labels."""
        (tmp_path / "file.txt").write_text("content")

        resolver = DirectoryResolver(str(tmp_path), ext="txt", dropext=True)
        result = resolver.load()

        assert "file" in result
        assert "file_txt" not in result


class TestDirectoryResolverSubdirectories:
    """Subdirectory handling."""

    def test_subdirectory_creates_resolver(self, tmp_path):
        """Subdirectories get DirectoryResolver as resolver."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        resolver = DirectoryResolver(str(tmp_path))
        result = resolver.load()

        assert "subdir" in result
        node = result.get_node("subdir")
        # Resolver should be a DirectoryResolver (lazy)
        assert isinstance(node.resolver, DirectoryResolver)

    def test_nested_directory_traversal(self, tmp_path):
        """Can traverse nested directories."""
        subdir = tmp_path / "level1"
        subdir.mkdir()
        (subdir / "file.txt").write_text("nested")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        # Get the subdirectory - use static=False to trigger resolver
        subdir_bag = result.get_item("level1", static=False)
        assert isinstance(subdir_bag, Bag)
        assert "file_txt" in subdir_bag


class TestDirectoryResolverProcessors:
    """File processor functionality."""

    def test_processor_txt_creates_resolver(self, tmp_path):
        """TXT files get TxtDocResolver as resolver."""
        from genro_bag.resolvers import TxtDocResolver

        (tmp_path / "doc.txt").write_text("hello")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        node = result.get_node("doc_txt")
        assert isinstance(node.resolver, TxtDocResolver)

    def test_processor_txt_loads_content(self, tmp_path):
        """TxtDocResolver loads file content when accessed."""
        (tmp_path / "doc.txt").write_text("hello world")

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        # Accessing value triggers the resolver (static=False required)
        content = result.get_item("doc_txt", static=False)
        assert content == b"hello world"

    def test_processor_xml_creates_resolver(self, tmp_path):
        """XML files get SerializedBagResolver as resolver."""
        from genro_bag.resolvers import SerializedBagResolver

        (tmp_path / "data.xml").write_text("<root><item>value</item></root>")

        resolver = DirectoryResolver(str(tmp_path), ext="xml")
        result = resolver.load()

        node = result.get_node("data_xml")
        assert isinstance(node.resolver, SerializedBagResolver)

    def test_processor_xml_loads_bag(self, tmp_path):
        """SerializedBagResolver loads XML as Bag when accessed."""
        (tmp_path / "data.xml").write_text("<root><item>value</item></root>")

        resolver = DirectoryResolver(str(tmp_path), ext="xml")
        result = resolver.load()

        # Accessing value triggers the resolver (static=False required)
        bag = result.get_item("data_xml", static=False)
        assert isinstance(bag, Bag)
        assert bag["root.item"] == "value"

    def test_processor_default_returns_none_for_non_xml(self, tmp_path):
        """Unknown extensions with non-XML content get None value."""
        (tmp_path / "file.unknown").write_text("plain text data")

        resolver = DirectoryResolver(str(tmp_path), ext="")
        result = resolver.load()

        node = result.get_node("file_unknown")
        assert node.value is None

    def test_processor_default_sniffs_xml_content(self, tmp_path):
        """Files with XML content are auto-detected regardless of extension."""
        from genro_bag.resolvers import SerializedBagResolver

        # XSD file (XML content with non-xml extension)
        (tmp_path / "schema.xsd").write_text('<?xml version="1.0"?><schema/>')
        # RNG file (XML content)
        (tmp_path / "grammar.rng").write_text(
            '<grammar xmlns="http://relaxng.org/ns/structure/1.0"/>'
        )
        # SVG file (XML content without declaration)
        (tmp_path / "image.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')

        resolver = DirectoryResolver(str(tmp_path), ext="")
        result = resolver.load()

        # All should be detected as XML and get SerializedBagResolver
        assert isinstance(result.get_node("schema_xsd").resolver, SerializedBagResolver)
        assert isinstance(result.get_node("grammar_rng").resolver, SerializedBagResolver)
        assert isinstance(result.get_node("image_svg").resolver, SerializedBagResolver)

    def test_processor_default_loads_sniffed_xml_as_bag(self, tmp_path):
        """Sniffed XML files load as Bag when accessed."""
        (tmp_path / "data.xsd").write_text("<root><item>value</item></root>")

        resolver = DirectoryResolver(str(tmp_path), ext="")
        result = resolver.load()

        # Accessing value triggers resolver (static=False required)
        bag = result.get_item("data_xsd", static=False)
        assert isinstance(bag, Bag)
        assert bag["root.item"] == "value"

    def test_custom_processor(self, tmp_path):
        """Custom processor can be provided."""
        (tmp_path / "data.csv").write_text("a,b,c")

        def csv_processor(path):
            with open(path) as f:
                return f.read().split(",")

        resolver = DirectoryResolver(str(tmp_path), ext="csv", processors={"csv": csv_processor})
        result = resolver.load()

        assert result.get_item("data_csv", static=False) == ["a", "b", "c"]

    def test_processor_disabled_with_false(self, tmp_path):
        """Processor can be disabled by setting to False."""
        (tmp_path / "file.txt").write_text("content")

        resolver = DirectoryResolver(str(tmp_path), ext="txt", processors={"txt": False})
        result = resolver.load()

        # With processor disabled, should use default (None)
        node = result.get_node("file_txt")
        assert node.value is None


class TestDirectoryResolverCallback:
    """Callback functionality."""

    def test_callback_filters_entries(self, tmp_path):
        """Callback returning False excludes entry."""
        (tmp_path / "small.txt").write_text("x")
        (tmp_path / "large.txt").write_text("x" * 100)

        def only_large(nodeattr):
            return nodeattr["size"] > 50

        resolver = DirectoryResolver(str(tmp_path), ext="txt", callback=only_large)
        result = resolver.load()

        assert len(result) == 1
        assert "large_txt" in result

    def test_callback_receives_nodeattr(self, tmp_path):
        """Callback receives nodeattr dict with file info."""
        (tmp_path / "test.txt").write_text("content")
        received_attrs = []

        def capture_attrs(nodeattr):
            received_attrs.append(nodeattr)
            return True

        resolver = DirectoryResolver(str(tmp_path), ext="txt", callback=capture_attrs)
        resolver.load()

        assert len(received_attrs) == 1
        attr = received_attrs[0]
        assert "file_name" in attr
        assert "abs_path" in attr
        assert "size" in attr


class TestDirectoryResolverRelocate:
    """Relocate path functionality."""

    def test_relocate_affects_rel_path(self, tmp_path):
        """Relocate changes rel_path attribute."""
        (tmp_path / "file.txt").write_text("content")

        resolver = DirectoryResolver(str(tmp_path), relocate="/virtual/path", ext="txt")
        result = resolver.load()

        node = result.get_node("file_txt")
        assert node.get_attr("rel_path") == "/virtual/path/file.txt"


class TestDirectoryResolverCaching:
    """Resolver caching behavior."""

    def test_default_cache_time(self):
        """Default cache_time is 500 seconds."""
        resolver = DirectoryResolver("/tmp")
        assert resolver.cache_time == 500

    def test_custom_cache_time(self):
        """Cache time can be customized."""
        resolver = DirectoryResolver("/tmp", cache_time=60)
        assert resolver.cache_time == 60


class TestDirectoryResolverSymlinkSecurity:
    """Symlink security tests."""

    def test_symlink_inside_base_allowed(self, tmp_path):
        """Symlinks pointing inside base directory are allowed."""
        # Create a file and a symlink to it within the same directory
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(real_file)

        resolver = DirectoryResolver(str(tmp_path), ext="txt")
        result = resolver.load()

        # Both real file and symlink should be included
        assert "real_txt" in result
        assert "link_txt" in result

    def test_symlink_outside_base_blocked_by_default(self, tmp_path):
        """Symlinks pointing outside base directory are blocked by default."""
        # Create an external directory with a file
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        external_file = external_dir / "secret.txt"
        external_file.write_text("secret content")

        # Create base directory with a symlink to external file
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "normal.txt").write_text("normal")
        escape_link = base_dir / "escape.txt"
        escape_link.symlink_to(external_file)

        resolver = DirectoryResolver(str(base_dir), ext="txt")
        result = resolver.load()

        # Normal file should be included, escape symlink should be blocked
        assert "normal_txt" in result
        assert "escape_txt" not in result

    def test_symlink_outside_base_allowed_with_follow_symlinks(self, tmp_path):
        """Symlinks outside base are allowed when follow_symlinks=True."""
        # Create an external directory with a file
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        external_file = external_dir / "allowed.txt"
        external_file.write_text("allowed content")

        # Create base directory with a symlink to external file
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        escape_link = base_dir / "link.txt"
        escape_link.symlink_to(external_file)

        resolver = DirectoryResolver(str(base_dir), ext="txt", follow_symlinks=True)
        result = resolver.load()

        # With follow_symlinks=True, external symlink should be included
        assert "link_txt" in result

    def test_symlink_directory_outside_base_blocked(self, tmp_path):
        """Symlink directories pointing outside are blocked."""
        # Create an external directory
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        (external_dir / "secret.txt").write_text("secret")

        # Create base directory with a symlink to external directory
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        escape_dir_link = base_dir / "escape_dir"
        escape_dir_link.symlink_to(external_dir)

        resolver = DirectoryResolver(str(base_dir))
        result = resolver.load()

        # Symlink directory pointing outside should be blocked
        assert "escape_dir" not in result

    def test_default_follow_symlinks_is_false(self):
        """Default follow_symlinks is False for security."""
        resolver = DirectoryResolver("/tmp")
        assert resolver._kw["follow_symlinks"] is False
