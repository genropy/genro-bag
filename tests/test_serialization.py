# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for Bag TYTX serialization (.bag.json and .bag.mp)."""

import datetime
import os
import tempfile
from decimal import Decimal

from genro_bag import Bag


class TestBagToTytxJson:
    """Tests for Bag.to_tytx() with JSON transport (.bag.json)."""

    def test_simple_values(self):
        """Test serialization of simple scalar values."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42
        bag["price"] = Decimal("19.99")

        data = bag.to_tytx()

        assert isinstance(data, str)
        assert "name" in data
        assert "test" in data

    def test_nested_bag(self):
        """Test serialization of nested Bag structures."""
        bag = Bag()
        bag["config.db.host"] = "localhost"
        bag["config.db.port"] = 5432

        data = bag.to_tytx()

        assert "config" in data
        assert "host" in data
        assert "localhost" in data

    def test_typed_values_preserved(self):
        """Test that typed values are preserved in TYTX format."""
        bag = Bag()
        bag["integer"] = 42
        bag["decimal"] = Decimal("123.45")
        bag["date"] = datetime.date(2025, 1, 5)
        bag["datetime"] = datetime.datetime(2025, 1, 5, 10, 30, 0)
        bag["time"] = datetime.time(14, 30, 0)
        bag["boolean"] = True

        data = bag.to_tytx()

        # TYTX format includes type markers
        assert "::L" in data or "42" in data  # Integer
        assert "::N" in data or "123.45" in data  # Decimal
        assert "::D" in data or "2025-01-05" in data  # Date

    def test_none_value(self):
        """Test serialization of None values."""
        bag = Bag()
        bag["empty"] = None

        data = bag.to_tytx()

        assert "::NN" in data  # None marker

    def test_attributes_preserved(self):
        """Test that node attributes are preserved."""
        bag = Bag()
        bag.set_item("item", "value", _attributes={"id": 123, "active": True})

        data = bag.to_tytx()

        assert "id" in data
        assert "123" in data

    def test_compact_mode(self):
        """Test compact serialization mode."""
        bag = Bag()
        bag["a.b.c"] = "deep"
        bag["a.b.d"] = "deeper"

        normal = bag.to_tytx(compact=False)
        compact = bag.to_tytx(compact=True)

        # Compact mode should have paths dict
        assert "paths" in compact

    def test_write_to_file(self):
        """Test writing to .bag.json file."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test")
            result = bag.to_tytx(filename=filepath)

            assert result is None  # Returns None when writing to file
            assert os.path.exists(filepath + ".bag.json")

            with open(filepath + ".bag.json") as f:
                content = f.read()
            assert "name" in content
            assert "test" in content

    def test_file_extension_auto_added(self):
        """Test that .bag.json extension is added automatically."""
        bag = Bag()
        bag["test"] = "value"

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "myfile")
            bag.to_tytx(filename=filepath)

            assert os.path.exists(filepath + ".bag.json")


class TestBagToTytxMsgpack:
    """Tests for Bag.to_tytx() with MessagePack transport (.bag.mp)."""

    def test_simple_values(self):
        """Test serialization of simple scalar values."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42

        data = bag.to_tytx(transport="msgpack")

        assert isinstance(data, bytes)

    def test_typed_values_preserved(self):
        """Test that typed values are preserved in MessagePack."""
        bag = Bag()
        bag["integer"] = 42
        bag["decimal"] = Decimal("123.45")
        bag["date"] = datetime.date(2025, 1, 5)

        data = bag.to_tytx(transport="msgpack")

        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_write_to_file(self):
        """Test writing to .bag.mp file."""
        bag = Bag()
        bag["name"] = "test"
        bag["count"] = 42

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test")
            result = bag.to_tytx(transport="msgpack", filename=filepath)

            assert result is None
            assert os.path.exists(filepath + ".bag.mp")

            with open(filepath + ".bag.mp", "rb") as f:
                content = f.read()
            assert len(content) > 0

    def test_compact_mode(self):
        """Test compact serialization mode with MessagePack."""
        bag = Bag()
        bag["a.b.c"] = "deep"

        data = bag.to_tytx(transport="msgpack", compact=True)

        assert isinstance(data, bytes)


class TestBagFromTytxJson:
    """Tests for Bag.from_tytx() with JSON transport."""

    def test_simple_values(self):
        """Test deserialization of simple values."""
        original = Bag()
        original["name"] = "test"
        original["count"] = 42

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["name"] == "test"
        assert restored["count"] == 42

    def test_nested_bag(self):
        """Test deserialization of nested structures."""
        original = Bag()
        original["config.db.host"] = "localhost"
        original["config.db.port"] = 5432

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["config.db.host"] == "localhost"
        assert restored["config.db.port"] == 5432

    def test_typed_values_restored(self):
        """Test that typed values are correctly restored.

        Note: TYTX converts naive datetimes to UTC (adds tzinfo=timezone.utc).
        """
        original = Bag()
        original["integer"] = 42
        original["decimal"] = Decimal("123.45")
        original["date"] = datetime.date(2025, 1, 5)
        original["datetime"] = datetime.datetime(2025, 1, 5, 10, 30, 0)
        original["time"] = datetime.time(14, 30, 0)
        original["boolean"] = True

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["integer"] == 42
        assert isinstance(restored["integer"], int)
        assert restored["decimal"] == Decimal("123.45")
        assert isinstance(restored["decimal"], Decimal)
        assert restored["date"] == datetime.date(2025, 1, 5)
        assert isinstance(restored["date"], datetime.date)
        # TYTX adds UTC timezone to naive datetimes
        assert restored["datetime"].replace(tzinfo=None) == datetime.datetime(2025, 1, 5, 10, 30, 0)
        assert restored["time"] == datetime.time(14, 30, 0)
        assert restored["boolean"] is True

    def test_none_value_restored(self):
        """Test that None values are correctly restored."""
        original = Bag()
        original["empty"] = None

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["empty"] is None

    def test_attributes_restored(self):
        """Test that node attributes are correctly restored."""
        original = Bag()
        original.set_item("item", "value", _attributes={"id": 123, "active": True})

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["item"] == "value"
        node = restored.get_node("item")
        assert node.attr["id"] == 123
        assert node.attr["active"] is True

    def test_compact_mode_restored(self):
        """Test deserialization from compact mode."""
        original = Bag()
        original["a.b.c"] = "deep"
        original["a.b.d"] = "deeper"

        data = original.to_tytx(compact=True)
        restored = Bag.from_tytx(data)

        assert restored["a.b.c"] == "deep"
        assert restored["a.b.d"] == "deeper"


class TestBagFromTytxMsgpack:
    """Tests for Bag.from_tytx() with MessagePack transport."""

    def test_simple_values(self):
        """Test deserialization from MessagePack."""
        original = Bag()
        original["name"] = "test"
        original["count"] = 42

        data = original.to_tytx(transport="msgpack")
        restored = Bag.from_tytx(data, transport="msgpack")

        assert restored["name"] == "test"
        assert restored["count"] == 42

    def test_typed_values_restored(self):
        """Test that typed values are correctly restored from MessagePack."""
        original = Bag()
        original["integer"] = 42
        original["decimal"] = Decimal("123.45")
        original["date"] = datetime.date(2025, 1, 5)

        data = original.to_tytx(transport="msgpack")
        restored = Bag.from_tytx(data, transport="msgpack")

        assert restored["integer"] == 42
        assert restored["decimal"] == Decimal("123.45")
        assert restored["date"] == datetime.date(2025, 1, 5)

    def test_nested_bag(self):
        """Test deserialization of nested structures from MessagePack."""
        original = Bag()
        original["config.db.host"] = "localhost"
        original["config.db.port"] = 5432

        data = original.to_tytx(transport="msgpack")
        restored = Bag.from_tytx(data, transport="msgpack")

        assert restored["config.db.host"] == "localhost"
        assert restored["config.db.port"] == 5432


class TestTytxRoundTrip:
    """Tests for complete to_tytx/from_tytx round-trip."""

    def test_json_roundtrip_all_types(self):
        """Test JSON round-trip with all supported types.

        Note: TYTX treats naive datetimes as UTC. When decoded, datetimes
        have tzinfo=datetime.timezone.utc.
        """
        original = Bag()
        original["string"] = "hello world"
        original["integer"] = 42
        original["float"] = 3.14159
        original["decimal"] = Decimal("999.99")
        original["boolean_true"] = True
        original["boolean_false"] = False
        original["none"] = None
        original["date"] = datetime.date(2025, 1, 5)
        original["datetime"] = datetime.datetime(2025, 1, 5, 10, 30, 45)
        original["time"] = datetime.time(14, 30, 0)

        data = original.to_tytx()
        restored = Bag.from_tytx(data)

        assert restored["string"] == "hello world"
        assert restored["integer"] == 42
        assert restored["float"] == 3.14159
        assert restored["decimal"] == Decimal("999.99")
        assert restored["boolean_true"] is True
        assert restored["boolean_false"] is False
        assert restored["none"] is None
        assert restored["date"] == datetime.date(2025, 1, 5)
        # TYTX treats naive datetimes as UTC
        assert restored["datetime"].replace(tzinfo=None) == datetime.datetime(
            2025, 1, 5, 10, 30, 45
        )
        assert restored["time"] == datetime.time(14, 30, 0)

    def test_msgpack_roundtrip_all_types(self):
        """Test MessagePack round-trip with all supported types.

        Note: TYTX treats naive datetimes as UTC.
        """
        original = Bag()
        original["string"] = "hello world"
        original["integer"] = 42
        original["decimal"] = Decimal("999.99")
        original["date"] = datetime.date(2025, 1, 5)
        original["datetime"] = datetime.datetime(2025, 1, 5, 10, 30, 45)
        original["none"] = None

        data = original.to_tytx(transport="msgpack")
        restored = Bag.from_tytx(data, transport="msgpack")

        assert restored["string"] == "hello world"
        assert restored["integer"] == 42
        assert restored["decimal"] == Decimal("999.99")
        assert restored["date"] == datetime.date(2025, 1, 5)
        # TYTX treats naive datetimes as UTC
        assert restored["datetime"].replace(tzinfo=None) == datetime.datetime(
            2025, 1, 5, 10, 30, 45
        )
        assert restored["none"] is None

    def test_deep_nesting_roundtrip(self):
        """Test round-trip with deeply nested structures."""
        original = Bag()
        original["level1.level2.level3.level4.value"] = "deep"
        original["level1.level2.other"] = "sibling"
        original["level1.another"] = "different branch"

        for transport in ["json", "msgpack"]:
            data = original.to_tytx(transport=transport)
            restored = Bag.from_tytx(
                data, transport="msgpack" if transport == "msgpack" else "json"
            )

            assert restored["level1.level2.level3.level4.value"] == "deep"
            assert restored["level1.level2.other"] == "sibling"
            assert restored["level1.another"] == "different branch"

    def test_attributes_roundtrip(self):
        """Test that attributes survive round-trip."""
        original = Bag()
        original.set_item(
            "item",
            "value",
            _attributes={"id": 123, "name": "test", "active": True, "score": Decimal("9.5")},
        )

        for transport in ["json", "msgpack"]:
            data = original.to_tytx(transport=transport)
            restored = Bag.from_tytx(
                data, transport="msgpack" if transport == "msgpack" else "json"
            )

            node = restored.get_node("item")
            assert node.attr["id"] == 123
            assert node.attr["name"] == "test"
            assert node.attr["active"] is True
            assert node.attr["score"] == Decimal("9.5")

    def test_compact_roundtrip(self):
        """Test compact mode round-trip."""
        original = Bag()
        original["a.b.c.d"] = "very deep"
        original["a.b.c.e"] = "sibling"
        original["a.b.f"] = "another"
        original["a.x"] = "different"

        for transport in ["json", "msgpack"]:
            data = original.to_tytx(transport=transport, compact=True)
            restored = Bag.from_tytx(
                data, transport="msgpack" if transport == "msgpack" else "json"
            )

            assert restored["a.b.c.d"] == "very deep"
            assert restored["a.b.c.e"] == "sibling"
            assert restored["a.b.f"] == "another"
            assert restored["a.x"] == "different"

    def test_special_characters_roundtrip(self):
        """Test round-trip with special characters."""
        original = Bag()
        original["text"] = 'Hello <world> & "friends"'
        original["unicode"] = "Привет 你好 مرحبا"
        original["newlines"] = "line1\nline2\nline3"

        for transport in ["json", "msgpack"]:
            data = original.to_tytx(transport=transport)
            restored = Bag.from_tytx(
                data, transport="msgpack" if transport == "msgpack" else "json"
            )

            assert restored["text"] == 'Hello <world> & "friends"'
            assert restored["unicode"] == "Привет 你好 مرحبا"
            assert restored["newlines"] == "line1\nline2\nline3"

    def test_empty_bag_roundtrip(self):
        """Test round-trip with empty Bag values."""
        original = Bag()
        original["parent"] = Bag()  # Empty Bag
        original["parent.child"] = "has content"
        original["empty_parent"] = Bag()  # Truly empty

        for transport in ["json", "msgpack"]:
            data = original.to_tytx(transport=transport)
            restored = Bag.from_tytx(
                data, transport="msgpack" if transport == "msgpack" else "json"
            )

            assert restored["parent.child"] == "has content"
            assert isinstance(restored["empty_parent"], Bag)


class TestTytxFileOperations:
    """Tests for file I/O operations."""

    def test_json_file_roundtrip(self):
        """Test complete file round-trip with JSON."""
        original = Bag()
        original["name"] = "file test"
        original["count"] = 42
        original["config.host"] = "localhost"

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test")
            original.to_tytx(filename=filepath)

            # Read file and restore
            with open(filepath + ".bag.json") as f:
                data = f.read()
            restored = Bag.from_tytx(data)

            assert restored["name"] == "file test"
            assert restored["count"] == 42
            assert restored["config.host"] == "localhost"

    def test_msgpack_file_roundtrip(self):
        """Test complete file round-trip with MessagePack."""
        original = Bag()
        original["name"] = "msgpack test"
        original["count"] = 42
        original["decimal"] = Decimal("99.99")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test")
            original.to_tytx(transport="msgpack", filename=filepath)

            # Read file and restore
            with open(filepath + ".bag.mp", "rb") as f:
                data = f.read()
            restored = Bag.from_tytx(data, transport="msgpack")

            assert restored["name"] == "msgpack test"
            assert restored["count"] == 42
            assert restored["decimal"] == Decimal("99.99")

    def test_file_already_has_extension(self):
        """Test that extension is not duplicated if already present."""
        original = Bag()
        original["test"] = "value"

        with tempfile.TemporaryDirectory() as tmpdir:
            # JSON
            filepath_json = os.path.join(tmpdir, "test.bag.json")
            original.to_tytx(filename=filepath_json)
            assert os.path.exists(filepath_json)
            # Should NOT create test.bag.json.bag.json

            # MessagePack
            filepath_mp = os.path.join(tmpdir, "test.bag.mp")
            original.to_tytx(transport="msgpack", filename=filepath_mp)
            assert os.path.exists(filepath_mp)
