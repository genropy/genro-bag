# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for FileResolver."""

from __future__ import annotations

import json

import pytest

from genro_bag import Bag
from genro_bag.resolvers import FileResolver

# =========================================================================
# Text formats
# =========================================================================


class TestFileResolverText:
    """Text file loading (.txt, .css, .html, .md)."""

    def test_load_txt(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("hello world")
        assert FileResolver(str(f))() == "hello world"

    def test_load_css(self, tmp_path):
        f = tmp_path / "style.css"
        f.write_text("body { color: red; }")
        assert FileResolver(str(f))() == "body { color: red; }"

    def test_load_html(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<h1>Title</h1>")
        assert FileResolver(str(f))() == "<h1>Title</h1>"

    def test_load_md(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Heading")
        assert FileResolver(str(f))() == "# Heading"

    def test_utf8_encoding(self, tmp_path):
        f = tmp_path / "unicode.txt"
        f.write_text("caf\u00e9 \u2603 \u00e8", encoding="utf-8")
        assert FileResolver(str(f))() == "caf\u00e9 \u2603 \u00e8"

    def test_latin1_encoding(self, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes("caf\u00e9".encode("latin-1"))
        assert FileResolver(str(f), encoding="latin-1")() == "caf\u00e9"

    def test_unknown_extension_falls_back_to_text(self, tmp_path):
        f = tmp_path / "data.log"
        f.write_text("log entry")
        assert FileResolver(str(f))() == "log entry"


# =========================================================================
# JSON format
# =========================================================================


class TestFileResolverJson:
    """JSON file loading."""

    def test_load_json_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"name": "Alice", "age": 30}))
        result = FileResolver(str(f))()
        assert isinstance(result, dict)
        assert result == {"name": "Alice", "age": 30}

    def test_load_json_dict_as_bag(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"name": "Alice", "age": 30}))
        bag = Bag()
        bag.set_item("data", FileResolver(str(f), as_bag=True))
        result = bag["data"]
        assert isinstance(result, Bag)
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_load_json_list(self, tmp_path):
        f = tmp_path / "items.json"
        f.write_text(json.dumps([1, 2, 3]))
        result = FileResolver(str(f))()
        assert result == [1, 2, 3]

    def test_load_json_list_as_bag(self, tmp_path):
        f = tmp_path / "items.json"
        f.write_text(json.dumps([10, 20, 30]))
        bag = Bag()
        bag.set_item("data", FileResolver(str(f), as_bag=True))
        result = bag["data"]
        assert isinstance(result, Bag)
        assert len(result) == 3

    def test_load_json_scalar_string(self, tmp_path):
        f = tmp_path / "val.json"
        f.write_text(json.dumps("just a string"))
        assert FileResolver(str(f))() == "just a string"

    def test_load_json_scalar_number(self, tmp_path):
        f = tmp_path / "num.json"
        f.write_text(json.dumps(42))
        assert FileResolver(str(f))() == 42

    def test_load_json_nested(self, tmp_path):
        f = tmp_path / "nested.json"
        data = {"users": [{"name": "A"}, {"name": "B"}]}
        f.write_text(json.dumps(data))
        result = FileResolver(str(f))()
        assert result["users"][0]["name"] == "A"

    def test_load_json_bag_node_format(self, tmp_path):
        """JSON with label/value/attr is handled by Bag.from_json when as_bag=True."""
        f = tmp_path / "contacts.json"
        data = [
            {"label": "c0", "value": None, "attr": {"name": "Alice", "role": "Engineer"}},
            {"label": "c1", "value": None, "attr": {"name": "Bob", "role": "Designer"}},
        ]
        f.write_text(json.dumps(data))
        result = FileResolver(str(f), as_bag=True)()
        assert isinstance(result, Bag)
        assert len(result) == 2
        node0 = result.get_node("c0")
        assert node0.attr["name"] == "Alice"
        assert node0.attr["role"] == "Engineer"
        node1 = result.get_node("c1")
        assert node1.attr["name"] == "Bob"

    def test_load_json_as_bag_standalone(self, tmp_path):
        """as_bag=True works without Bag attachment (standalone resolver)."""
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"x": 1, "y": 2}))
        result = FileResolver(str(f), as_bag=True)()
        assert isinstance(result, Bag)
        assert result["x"] == 1


# =========================================================================
# CSV format
# =========================================================================


class TestFileResolverCsv:
    """CSV file loading."""

    def test_load_csv_with_headers(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\n")
        result = FileResolver(str(f))()
        assert isinstance(result, Bag)
        assert len(result) == 2
        node0 = result.get_node("r0")
        assert node0.attr["name"] == "Alice"
        assert node0.attr["age"] == "30"
        assert node0.attr["city"] == "NYC"
        node1 = result.get_node("r1")
        assert node1.attr["name"] == "Bob"

    def test_load_csv_without_headers(self, tmp_path):
        f = tmp_path / "nohead.csv"
        f.write_text("Alice,30,NYC\nBob,25,LA\n")
        result = FileResolver(str(f), csv_has_header=False)()
        assert isinstance(result, Bag)
        assert len(result) == 2
        node0 = result.get_node("r0")
        assert node0.attr["c0"] == "Alice"
        assert node0.attr["c1"] == "30"
        assert node0.attr["c2"] == "NYC"

    def test_load_csv_empty_file(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("")
        result = FileResolver(str(f))()
        assert isinstance(result, Bag)
        assert len(result) == 0

    def test_load_csv_header_only(self, tmp_path):
        f = tmp_path / "header.csv"
        f.write_text("name,age,city\n")
        result = FileResolver(str(f))()
        assert isinstance(result, Bag)
        assert len(result) == 0

    def test_load_csv_custom_delimiter(self, tmp_path):
        f = tmp_path / "semi.csv"
        f.write_text("name;age\nAlice;30\n")
        result = FileResolver(str(f), csv_delimiter=";")()
        assert len(result) == 1
        assert result.get_node("r0").attr["name"] == "Alice"
        assert result.get_node("r0").attr["age"] == "30"

    def test_csv_node_values_are_none(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("x,y\n1,2\n")
        result = FileResolver(str(f))()
        node = result.get_node("r0")
        assert node.value is None


# =========================================================================
# Bag serialized formats
# =========================================================================


class TestFileResolverBagFormats:
    """Native Bag format loading (.bag.json, .bag.mp, .xml)."""

    def test_load_xml(self, tmp_path):
        source = Bag()
        source["name"] = "test"
        source["count"] = 42
        source.to_tytx(filename=str(tmp_path / "data"))
        # to_tytx writes .bag.json which round-trips types correctly
        # Use TYTX format to write, then save as .xml via to_xml with wrapper
        wrapper = Bag()
        wrapper["root"] = source
        xml_str = wrapper.to_xml()
        f = tmp_path / "data.xml"
        f.write_text(xml_str)
        result = FileResolver(str(f))()
        assert isinstance(result, Bag)
        assert result["root.name"] == "test"
        # XML does not preserve int types unless TYTX-encoded
        assert str(result["root.count"]) == "42"

    def test_load_bag_json(self, tmp_path):
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42
        bag.to_tytx(filename=str(tmp_path / "data"))
        result = FileResolver(str(tmp_path / "data.bag.json"))()
        assert isinstance(result, Bag)
        assert result["name"] == "test"
        assert result["count"] == 42

    def test_load_bag_mp(self, tmp_path):
        pytest.importorskip("msgpack")
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42
        bag.to_tytx(transport="msgpack", filename=str(tmp_path / "data"))
        result = FileResolver(str(tmp_path / "data.bag.mp"))()
        assert isinstance(result, Bag)
        assert result["name"] == "test"
        assert result["count"] == 42


# =========================================================================
# Path resolution
# =========================================================================


class TestFileResolverPathResolution:
    """Path resolution and base_path."""

    def test_absolute_path(self, tmp_path):
        f = tmp_path / "abs.txt"
        f.write_text("content")
        assert FileResolver(str(f))() == "content"

    def test_relative_path_with_base_path(self, tmp_path):
        f = tmp_path / "rel.txt"
        f.write_text("relative content")
        result = FileResolver("rel.txt", base_path=str(tmp_path))()
        assert result == "relative content"

    def test_relative_path_default_cwd(self, tmp_path, monkeypatch):
        f = tmp_path / "cwd.txt"
        f.write_text("from cwd")
        monkeypatch.chdir(tmp_path)
        assert FileResolver("cwd.txt")() == "from cwd"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="file not found"):
            FileResolver(str(tmp_path / "nope.txt"))()


# =========================================================================
# Caching
# =========================================================================


class TestFileResolverCaching:
    """Cache behavior."""

    def test_default_cache_time_zero(self):
        resolver = FileResolver("/dev/null")
        assert resolver.cache_time == 0

    def test_no_cache_rereads_file(self, tmp_path):
        f = tmp_path / "mutable.txt"
        f.write_text("v1")
        resolver = FileResolver(str(f))
        assert resolver() == "v1"
        f.write_text("v2")
        assert resolver() == "v2"

    def test_cached_returns_same_value(self, tmp_path):
        f = tmp_path / "cached.txt"
        f.write_text("original")
        resolver = FileResolver(str(f), cache_time=300)
        assert resolver() == "original"
        f.write_text("changed")
        assert resolver() == "original"

    def test_infinite_cache(self, tmp_path):
        f = tmp_path / "inf.txt"
        f.write_text("first")
        resolver = FileResolver(str(f), cache_time=False)
        assert resolver() == "first"
        f.write_text("second")
        assert resolver() == "first"

    def test_cache_reset(self, tmp_path):
        f = tmp_path / "reset.txt"
        f.write_text("v1")
        resolver = FileResolver(str(f), cache_time=300)
        assert resolver() == "v1"
        f.write_text("v2")
        assert resolver() == "v1"
        resolver.reset()
        assert resolver() == "v2"


# =========================================================================
# Bag integration
# =========================================================================


class TestFileResolverWithBag:
    """Integration with Bag."""

    def test_bag_access_resolves_file(self, tmp_path):
        f = tmp_path / "content.txt"
        f.write_text("bag text")
        bag = Bag()
        bag["file"] = FileResolver(str(f))
        assert bag["file"] == "bag text"

    def test_node_attr_overrides_path(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("file A")
        f2 = tmp_path / "b.txt"
        f2.write_text("file B")
        bag = Bag()
        bag.set_item("doc", FileResolver(str(f1)))
        assert bag["doc"] == "file A"
        bag.set_attr("doc", _attributes={"path": str(f2)})
        assert bag["doc"] == "file B"

    def test_resolver_serialization(self, tmp_path):
        f = tmp_path / "ser.txt"
        f.write_text("serialize me")
        resolver = FileResolver(str(f), cache_time=60)
        data = resolver.serialize()
        restored = FileResolver.deserialize(data)
        assert restored() == "serialize me"
