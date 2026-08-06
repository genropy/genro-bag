# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Spec tests for the DataChange layer."""

import json
from datetime import UTC, datetime

import pytest
from genro_toolbox import SignatureError
from genro_tytx.registry import SUFFIX_TO_TYPE, TYPE_REGISTRY

from genro_bag import Bag, BagSerializationError
from genro_bag.datachange import DataChangeCollector
from genro_bag.resolvers import UuidResolver

# =============================================================================
# 1. Capture on the plain rail
# =============================================================================


class TestPlainRailCapture:
    def test_write_is_captured(self):
        """A write on the observed Bag deposits one change."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        assert collector.pending == 1
        change = collector.changes[0]
        assert change["key"]["path"] == "a"
        assert change["value"] == 1
        assert change["delete"] is False

    def test_nested_write_path_is_dotted(self):
        """A write below the root reports the full dotted path."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a.b.c"] = 7
        paths = [c["key"]["path"] for c in collector.changes]
        assert "a.b.c" in paths

    def test_update_of_existing_node_is_captured(self):
        """Changing the value of an existing node deposits a change."""
        bag = Bag()
        bag["a"] = 1
        collector = DataChangeCollector(bag)
        bag["a"] = 2
        assert [c["value"] for c in collector.changes] == [2]

    def test_reason_travels_in_the_key(self):
        """The write reason ends up in the change key."""
        bag = Bag()
        bag["a"] = 1
        collector = DataChangeCollector(bag)
        bag.set_item("a", 2, _reason="sync")
        assert collector.changes[0]["key"]["reason"] == "sync"

    def test_attributes_are_captured(self):
        """Node attributes travel with the change."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag.set_item("a", 1, _attributes={"x": "1"})
        assert collector.changes[0]["attributes"] == {"x": "1"}

    def test_fired_defaults_to_false(self):
        """Locally captured changes are never marked fired."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        assert collector.changes[0]["key"]["fired"] is False


# =============================================================================
# 2. Prefix filtering
# =============================================================================


class TestPrefixFiltering:
    def test_write_under_subscribed_prefix_is_captured(self):
        """A write under an observed prefix is captured."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        bag["a.b"] = 1
        assert [c["key"]["path"] for c in collector.changes] == ["a", "a.b"]

    def test_write_outside_subscribed_paths_is_not_captured(self):
        """A write outside every observed prefix is ignored."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        bag["z.k"] = 1
        assert collector.pending == 0

    def test_prefix_matches_on_segment_boundary(self):
        """The prefix 'a' does not capture the sibling path 'ab'."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        bag["ab"] = 1
        assert collector.pending == 0

    def test_subscribe_path_widens_the_set(self):
        """subscribe_path starts capturing a new prefix at runtime."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        bag["z"] = 1
        collector.subscribe_path("z")
        bag["z"] = 2
        assert [c["key"]["path"] for c in collector.changes] == ["z"]

    def test_unsubscribe_path_narrows_the_set(self):
        """unsubscribe_path stops capturing a prefix at runtime."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        collector.unsubscribe_path("a")
        bag["a"] = 1
        assert collector.pending == 0

    def test_removing_the_last_prefix_captures_nothing(self):
        """An empty prefix set captures nothing; it is not paths=None."""
        bag = Bag()
        collector = DataChangeCollector(bag, paths={"a"})
        collector.unsubscribe_path("a")
        assert collector.paths == set()
        bag["a"] = 1
        bag["b"] = 2
        assert collector.pending == 0

    def test_subscribe_path_restricts_a_capture_everything_collector(self):
        """On paths=None, subscribe_path starts restricting to the prefix.

        Writing 'a.x' auto-creates the branch node 'a', so both fall under
        the prefix; the write to 'b' must not be captured.
        """
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.subscribe_path("a")
        bag["a.x"] = 1
        bag["b"] = 2
        assert [c["key"]["path"] for c in collector.changes] == ["a", "a.x"]

    def test_unsubscribe_path_on_capture_everything_is_a_no_op(self):
        """On paths=None there is no prefix set to narrow."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.unsubscribe_path("a")
        assert collector.paths is None
        bag["a"] = 1
        assert collector.pending == 1


# =============================================================================
# 3. Delete
# =============================================================================


class TestDeleteCapture:
    def test_del_deposits_a_delete_change(self):
        """Deleting a node deposits a change with delete=True."""
        bag = Bag()
        bag["a"] = 1
        collector = DataChangeCollector(bag)
        del bag["a"]
        assert collector.pending == 1
        change = collector.changes[0]
        assert change["key"]["path"] == "a"
        assert change["delete"] is True
        assert change["value"] is None


# =============================================================================
# 4. change_idx and pending
# =============================================================================


class TestChangeIndex:
    def test_change_idx_strictly_increases(self):
        """Every deposit gets a higher change_idx than the previous one."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        indexes = [c["change_idx"] for c in collector.changes]
        assert indexes == sorted(set(indexes))
        assert len(indexes) == 3

    def test_pending_counts_the_changes(self):
        """pending reports the number of changes waiting to be drained."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        assert collector.pending == 0
        bag["a"] = 1
        bag["b"] = 2
        assert collector.pending == 2


# =============================================================================
# 5. detach and coexistence
# =============================================================================


class TestDetach:
    def test_detach_stops_capture(self):
        """After detach no further write is captured."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        collector.detach()
        bag["b"] = 2
        assert [c["key"]["path"] for c in collector.changes] == ["a"]

    def test_detach_keeps_pending_changes(self):
        """detach does not discard what was already captured."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        collector.detach()
        assert collector.pending == 1


class TestCoexistence:
    def test_other_subscriber_still_receives_events(self):
        """The collector never returns False, so other subscribers still fire."""
        seen = []
        bag = Bag()
        DataChangeCollector(bag)
        bag.subscribe("spy", insert=lambda **kw: seen.append(kw["evt"]))
        bag["a"] = 1
        assert seen == ["ins"]


# =============================================================================
# 7. Capture on the transaction rail
# =============================================================================


class TestTransactionRailCapture:
    def test_writes_inside_transaction_are_captured_in_order(self):
        """Three writes batched by a transaction arrive as three changes."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        with bag.transaction():
            bag["a"] = 1
            bag["b"] = 2
            bag["c"] = 3
        assert [c["key"]["path"] for c in collector.changes] == ["a", "b", "c"]
        assert [c["value"] for c in collector.changes] == [1, 2, 3]

    def test_nested_write_inside_transaction_reports_the_full_path(self):
        """A transaction mutation carries a local pathlist; capture rebuilds it."""
        bag = Bag()
        bag["user.name"] = "Bob"
        collector = DataChangeCollector(bag)
        with bag.transaction():
            bag["user.name"] = "Ada"
        assert [c["key"]["path"] for c in collector.changes] == ["user.name"]

    def test_delete_inside_transaction_yields_delete_true(self):
        """A del batched by a transaction is still a delete change."""
        bag = Bag()
        bag["a"] = 1
        collector = DataChangeCollector(bag)
        with bag.transaction():
            del bag["a"]
        assert [c["delete"] for c in collector.changes] == [True]
        assert collector.changes[0]["key"]["path"] == "a"

    def test_reason_travels_from_a_transaction_mutation(self):
        """The write reason reaches the key on both mutation shapes."""
        bag = Bag()
        bag["a"] = 1
        collector = DataChangeCollector(bag)
        with bag.transaction():
            bag.set_item("a", 2, _reason="sync")
            bag.set_item("b", 3, _reason="fresh")
        assert [c["key"]["reason"] for c in collector.changes] == ["sync", "fresh"]

    def test_prefix_filtering_applies_to_transaction_changes(self):
        """Prefixes restrict transaction-born capture exactly as on the plain rail."""
        bag = Bag()
        bag["keep.x"] = 0
        bag["skip.y"] = 0
        collector = DataChangeCollector(bag, paths={"keep"})
        with bag.transaction():
            bag["keep.x"] = 1
            bag["skip.y"] = 1
        assert [c["key"]["path"] for c in collector.changes] == ["keep.x"]

    def test_empty_transaction_deposits_nothing(self):
        """No mutations means no transaction event, hence no changes."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        with bag.transaction():
            pass
        assert collector.pending == 0

    def test_change_idx_continues_across_the_two_rails(self):
        """Transaction-born changes share the collector's monotonic counter."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        with bag.transaction():
            bag["b"] = 2
            bag["c"] = 3
        assert [c["change_idx"] for c in collector.changes] == [1, 2, 3]

    def test_detach_stops_transaction_capture(self):
        """detach removes the transaction subscription too."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.detach()
        with bag.transaction():
            bag["a"] = 1
        assert collector.pending == 0


# =============================================================================
# 3. Consumption: drain / drop / reset / append
# =============================================================================


class TestDrain:
    def test_drain_returns_changes_in_change_idx_order(self):
        """Drain order follows the monotonic counter, not insertion accidents."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        drained = collector.drain()
        assert [c["change_idx"] for c in drained] == [1, 2, 3]
        assert [c["key"]["path"] for c in drained] == ["a", "b", "c"]

    def test_drain_empties_the_pending_list(self):
        """The default drain consumes what it returns."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        assert len(collector.drain()) == 1
        assert collector.pending == 0

    def test_drain_without_reset_leaves_pending_intact(self):
        """drain(reset=False) peeks: the same changes are still there."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        first = collector.drain(reset=False)
        assert collector.pending == 1
        assert collector.drain(reset=False) == first


class TestDropAndReset:
    def test_drop_removes_only_the_matching_prefix(self):
        """drop discards the changes under one prefix and keeps the rest."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["keep.x"] = 1
        bag["gone.y"] = 2
        bag["gone.z"] = 3
        collector.drop("gone")
        assert [c["key"]["path"] for c in collector.drain()] == ["keep", "keep.x"]

    def test_drop_matches_on_segment_boundaries(self):
        """The prefix 'a' does not drop the sibling path 'ab'."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        bag["ab"] = 2
        collector.drop("a")
        assert [c["key"]["path"] for c in collector.drain()] == ["ab"]

    def test_reset_empties_without_reading(self):
        """reset drops everything pending."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        bag["a"] = 1
        collector.reset()
        assert collector.pending == 0


class TestAppend:
    def _forwarded(self, path, value, delete=False, fired=False):
        """Build a change as a consumer forwarding one from elsewhere would."""
        return {
            "key": {"path": path, "reason": None, "fired": fired},
            "value": value,
            "attributes": None,
            "delete": delete,
            "change_ts": datetime.now(UTC),
            "change_idx": 0,
        }

    def test_append_deposits_a_forwarded_change(self):
        """A change not born from a local write joins the pending list."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.append(self._forwarded("remote.x", 42))
        assert collector.pending == 1
        change = collector.drain()[0]
        assert change["key"]["path"] == "remote.x"
        assert change["change_idx"] == 1

    def test_append_with_replace_coalesces_repeated_writes(self):
        """Ten writes to one path survive as one change, carrying the last value."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        for value in range(10):
            collector.append(self._forwarded("x", value), replace=True)
        drained = collector.drain()
        assert len(drained) == 1
        assert drained[0]["value"] == 9

    def test_coalesced_change_goes_to_the_tail_with_a_new_idx(self):
        """Drain order reflects when the last write happened."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.append(self._forwarded("x", 1))
        collector.append(self._forwarded("y", 2))
        collector.append(self._forwarded("x", 3), replace=True)
        drained = collector.drain()
        assert [c["key"]["path"] for c in drained] == ["y", "x"]
        assert drained[-1]["change_idx"] == 3

    def test_delete_coalesces_over_a_previous_set(self):
        """delete sits outside the key, so only the removal survives."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.append(self._forwarded("x", 1))
        collector.append(self._forwarded("x", None, delete=True), replace=True)
        drained = collector.drain()
        assert len(drained) == 1
        assert drained[0]["delete"] is True

    def test_append_without_replace_keeps_both(self):
        """Without replace the two changes on one path both stay pending."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        collector.append(self._forwarded("x", 1))
        collector.append(self._forwarded("x", 2))
        assert collector.pending == 2

    def test_replace_discriminates_on_the_whole_key(self):
        """A different reason is a different key, so nothing coalesces."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        first = self._forwarded("x", 1)
        first["key"]["reason"] = "sync"
        collector.append(first)
        collector.append(self._forwarded("x", 2), replace=True)
        assert collector.pending == 2

    def test_append_does_not_mutate_the_forwarded_dict(self):
        """The collector stores a copy: the caller's dict keeps its change_idx."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        forwarded = self._forwarded("x", 1)
        collector.append(forwarded)
        assert forwarded["change_idx"] == 0
        stored = collector.drain()[0]
        assert stored is not forwarded
        assert stored["change_idx"] == 1

    def test_forwarding_one_change_to_two_collectors(self):
        """Fan-out: each collector assigns its own change_idx to its own copy."""
        bag_a, bag_b = Bag(), Bag()
        collector_a = DataChangeCollector(bag_a)
        collector_b = DataChangeCollector(bag_b)
        collector_b.append(self._forwarded("warmup", 0))
        forwarded = self._forwarded("x", 1)
        collector_a.append(forwarded)
        collector_b.append(forwarded)
        drained_a = collector_a.drain()[0]
        drained_b = collector_b.drain()[-1]
        assert drained_a is not drained_b
        assert drained_a["change_idx"] == 1
        assert drained_b["change_idx"] == 2


# =============================================================================
# 5. Two independent collectors on one Bag
# =============================================================================


class TestTwoCollectorsOnOneBag:
    def test_both_collectors_capture_the_same_write(self):
        """Two collectors attached to the same Bag both see one write."""
        bag = Bag()
        first = DataChangeCollector(bag)
        second = DataChangeCollector(bag)
        bag["a"] = 1
        assert first.pending == 1
        assert second.pending == 1

    def test_draining_one_leaves_the_other_intact(self):
        """Each collector keeps its own pending list."""
        bag = Bag()
        first = DataChangeCollector(bag)
        second = DataChangeCollector(bag)
        bag["a"] = 1
        first.drain()
        assert first.pending == 0
        assert second.pending == 1

    def test_detaching_one_leaves_the_other_capturing(self):
        """Detaching one collector does not affect the other's capture."""
        bag = Bag()
        first = DataChangeCollector(bag)
        second = DataChangeCollector(bag)
        first.detach()
        bag["a"] = 1
        assert first.pending == 0
        assert second.pending == 1


# =============================================================================
# 6. Bag as a TYTX custom type (suffix "X")
# =============================================================================


class TestBagAsTytxCustomType:
    """Bag is registered with genro-tytx under its historical suffix "X".

    Two meanings share the token and are told apart by the payload: an EMPTY
    payload ("::X") is the branch-node marker genro-bag's own flattener emits
    at row level, while "<payload>::X" is a whole serialized Bag travelling
    inside a plain dict or list value.
    """

    def test_bag_declares_the_x_suffix(self):
        """The suffix genro-tytx reads off the class is "X"."""
        assert Bag.__tytx_suffix__ == "X"

    def test_bag_is_in_the_tytx_registry(self):
        """Importing genro_bag registers Bag as a TYTX type."""
        assert TYPE_REGISTRY[Bag][0] == "X"
        assert SUFFIX_TO_TYPE["X"][0] is Bag

    def test_from_tytx_of_an_empty_payload_is_an_empty_bag(self):
        """The branch-node marker decodes to a Bag with no children."""
        bag = Bag.from_tytx("")
        assert isinstance(bag, Bag)
        assert len(bag) == 0

    def test_from_tytx_of_empty_bytes_is_an_empty_bag(self):
        """The bytes twin of the empty payload decodes the same way."""
        bag = Bag.from_tytx(b"", transport="msgpack")
        assert isinstance(bag, Bag)
        assert len(bag) == 0

    def test_from_tytx_of_none_raises(self):
        """Only the empty payload means a branch node; None is a caller error."""
        with pytest.raises(TypeError):
            Bag.from_tytx(None)  # type: ignore[arg-type]

    def test_branch_marker_still_travels_as_double_colon_x(self):
        """Registration must not change the wire shape of a branch node.

        The row slot must hold exactly "::X" (empty payload): a substring
        check would also match a whole-Bag "<payload>::X" encoding.
        """
        bag = Bag()
        bag["a.b"] = 1
        rows = json.loads(bag.to_tytx())["rows"]
        assert rows[0][3] == "::X"

    def test_branch_nodes_still_round_trip(self):
        """A nested Bag built as a branch survives the round-trip."""
        bag = Bag()
        bag["a.b"] = 1
        back = Bag.from_tytx(bag.to_tytx())
        assert isinstance(back["a"], Bag)
        assert back["a.b"] == 1

    def test_branch_nodes_still_round_trip_msgpack(self):
        """A nested Bag built as a branch survives the msgpack round-trip.

        Unlike json, msgpack strings are not re-scanned for suffixes on
        decode, so the row-level "::X" marker reaches the parser as a
        literal string — the parser must recognise both forms.
        """
        bag = Bag()
        bag["a.b"] = 1
        back = Bag.from_tytx(bag.to_tytx(transport="msgpack"), transport="msgpack")
        assert isinstance(back["a"], Bag)
        assert back["a.b"] == 1

    def test_bag_nested_in_a_dict_value_round_trips_json(self):
        """A Bag carried inside a plain dict value comes back as a Bag."""
        inner = Bag()
        inner["x"] = 1
        inner["y"] = "two"
        bag = Bag()
        bag["payload"] = {"nested": inner, "n": 7}
        back = Bag.from_tytx(bag.to_tytx())
        payload = back["payload"]
        assert payload["n"] == 7
        assert isinstance(payload["nested"], Bag)
        assert payload["nested"]["x"] == 1
        assert payload["nested"]["y"] == "two"

    def test_bag_nested_in_a_dict_value_round_trips_msgpack(self):
        """Same as the json case, over the msgpack transport.

        Environment canary: under a narrowed coverage scope (e.g.
        ``--cov=genro_bag.datachange``) the msgpack C packer stops
        recognising ``ExtType`` and degrades it to a plain list, so this
        test fails with ``[4, b'X:...']`` instead of a Bag. That is a
        coverage/C-extension interaction outside genro-bag — do not chase
        it here; run with the project's configured coverage scope.
        """
        inner = Bag()
        inner["x"] = 1
        bag = Bag()
        bag["payload"] = {"nested": inner}
        back = Bag.from_tytx(bag.to_tytx(transport="msgpack"), transport="msgpack")
        assert isinstance(back["payload"]["nested"], Bag)
        assert back["payload"]["nested"]["x"] == 1


# =============================================================================
# 9. Wire round-trip
# =============================================================================


class TestChangeWireRoundTrip:
    """Drained changes travel on the wire with no datachange-specific code.

    A change is a plain dict of scalars nesting one dict, so genro-tytx's
    TYPE_REGISTRY carries every field as-is, and a Bag in ``value`` travels
    through the generic registration of Phase 6. Two transport behaviours are
    generic, not datachange's: genro-tytx truncates a datetime to milliseconds
    and tags a naive one as UTC, and ``to_json`` maps every dict to a Bag.
    """

    def _carrier(self, changes):
        """Put drained changes into a Bag, one per numbered node."""
        carrier = Bag()
        for index, change in enumerate(changes):
            carrier[f"c_{index}"] = change
        return carrier

    def _drained(self):
        """A set of changes covering value, Bag value, attributes and delete."""
        bag = Bag()
        collector = DataChangeCollector(bag)
        inner = Bag()
        inner["x"] = 1
        inner["y"] = "two"
        bag["n"] = inner
        bag.set_item("a", 2, _attributes={"k": "v"}, _reason="sync")
        del bag["a"]
        return collector.drain()

    def test_changes_round_trip_through_tytx(self):
        """Every field but the timestamp comes back equal, with no encoder."""
        changes = self._drained()
        back = Bag.from_tytx(self._carrier(changes).to_tytx())
        for index, original in enumerate(changes):
            restored = back[f"c_{index}"]
            assert isinstance(restored, dict)
            assert {k: v for k, v in restored.items() if k != "change_ts"} == {
                k: v for k, v in original.items() if k != "change_ts"
            }

    def test_change_ts_survives_to_the_millisecond(self):
        """The timestamp is aware UTC and travels as the same instant."""
        changes = self._drained()
        back = Bag.from_tytx(self._carrier(changes).to_tytx())
        original = changes[0]["change_ts"]
        restored = back["c_0"]["change_ts"]
        assert original.tzinfo is UTC
        assert restored == original.replace(
            microsecond=original.microsecond // 1000 * 1000
        )

    def test_bag_value_round_trips_through_tytx(self):
        """A change whose value is a Bag comes back as an equal Bag."""
        changes = self._drained()
        back = Bag.from_tytx(self._carrier(changes).to_tytx())
        restored = back["c_0"]["value"]
        assert isinstance(restored, Bag)
        assert restored == changes[0]["value"]

    def test_delete_and_attributes_round_trip_through_tytx(self):
        """The delete flag and the attribute dict survive unchanged."""
        changes = self._drained()
        back = Bag.from_tytx(self._carrier(changes).to_tytx())
        assert back["c_1"]["attributes"] == {"k": "v"}
        assert back["c_1"]["key"]["reason"] == "sync"
        assert back["c_1"]["delete"] is False
        assert back["c_2"]["delete"] is True
        assert back["c_2"]["key"]["path"] == "a"

    def test_changes_round_trip_through_json(self):
        """to_json carries every field; its dicts come back as Bags."""
        changes = self._drained()
        back = Bag.from_json(self._carrier(changes).to_json())
        for index, original in enumerate(changes):
            assert back[f"c_{index}.key.path"] == original["key"]["path"]
            assert back[f"c_{index}.key.reason"] == original["key"]["reason"]
            assert back[f"c_{index}.key.fired"] == original["key"]["fired"]
            assert back[f"c_{index}.delete"] == original["delete"]
            assert back[f"c_{index}.change_idx"] == original["change_idx"]

    def test_bag_value_round_trips_through_json(self):
        """The Bag in value stays a Bag with its own content."""
        changes = self._drained()
        back = Bag.from_json(self._carrier(changes).to_json())
        assert isinstance(back["c_0.value"], Bag)
        assert back["c_0.value.x"] == 1
        assert back["c_0.value.y"] == "two"


# =============================================================================
# 8. Signing refusal for a Bag nested in a plain container value
# =============================================================================


class TestNestedBagSigningRefusal:
    """A Bag nested in a plain dict/list travels through the TYTX type
    registry, whose hooks take no sign_key: a resolver in there can be
    neither signed on encode nor verified on decode. Both sides refuse
    rather than letting the resolver bypass the signature.
    """

    def _bag_with_nested_resolver(self):
        inner = Bag()
        inner["id"] = UuidResolver("uuid4")
        bag = Bag()
        bag["d"] = {"inner": inner}
        return bag

    def test_signed_encode_refuses_a_nested_resolver(self):
        """to_tytx with sign_key refuses what it cannot sign."""
        bag = self._bag_with_nested_resolver()
        with pytest.raises(BagSerializationError):
            bag.to_tytx(sign_key="secret")

    def test_signed_decode_refuses_a_nested_resolver(self):
        """from_tytx with sign_key refuses what it cannot verify."""
        wire = self._bag_with_nested_resolver().to_tytx()
        with pytest.raises(SignatureError):
            Bag.from_tytx(wire, sign_key="secret")

    def test_unsigned_round_trip_still_carries_the_nested_resolver(self):
        """Without a key the nested resolver keeps travelling as before."""
        wire = self._bag_with_nested_resolver().to_tytx()
        back = Bag.from_tytx(wire)
        assert isinstance(back["d"]["inner"].get_resolver("id"), UuidResolver)

    def test_signed_encode_of_a_nested_bag_without_resolvers_passes(self):
        """The refusal is about resolvers, not about nesting itself."""
        inner = Bag()
        inner["x"] = 1
        bag = Bag()
        bag["d"] = {"inner": inner}
        back = Bag.from_tytx(bag.to_tytx(sign_key="secret"), sign_key="secret")
        assert back["d"]["inner"]["x"] == 1

    def _bag_with_nested_resolver_in_attribute(self):
        inner = Bag()
        inner["id"] = UuidResolver("uuid4")
        bag = Bag()
        bag.set_item("n", 1, _attributes={"meta": {"inner": inner}})
        return bag

    def test_signed_tytx_refuses_a_nested_resolver_in_an_attribute(self):
        """The attribute slot rides the same registry: encode refuses too."""
        bag = self._bag_with_nested_resolver_in_attribute()
        with pytest.raises(BagSerializationError):
            bag.to_tytx(sign_key="secret")

    def test_signed_tytx_decode_refuses_a_nested_resolver_in_an_attribute(self):
        """An unsigned attribute-borne nested resolver is refused on decode."""
        wire = self._bag_with_nested_resolver_in_attribute().to_tytx()
        with pytest.raises(SignatureError):
            Bag.from_tytx(wire, sign_key="secret")

    def test_signed_to_json_refuses_a_nested_resolver_in_a_value(self):
        """to_json rides the same registry for plain values: encode refuses."""
        bag = self._bag_with_nested_resolver()
        with pytest.raises(BagSerializationError):
            bag.to_json(sign_key="secret")

    def test_signed_to_json_refuses_a_nested_resolver_in_an_attribute(self):
        """to_json shares encode_attrs with the tytx rail: same refusal."""
        bag = self._bag_with_nested_resolver_in_attribute()
        with pytest.raises(BagSerializationError):
            bag.to_json(sign_key="secret")

    def test_signed_from_json_refuses_a_nested_resolver_in_a_value(self):
        """An unsigned nested resolver in a json payload is refused on decode."""
        wire = self._bag_with_nested_resolver().to_json()
        with pytest.raises(SignatureError):
            Bag.from_json(wire, sign_key="secret")
