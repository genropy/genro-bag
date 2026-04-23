"""Spec test: Bag - populate, deepcopy, update, pickle, from_url.

Dipende da test_basic.py (set_item, get_item, get_attr, __len__,
__iter__, __contains__) e da test_query.py (query, keys, values, items).

## Scala

1.  fill_from(None)                 no-op, returns self
2.  fill_from(dict)                 ricostruzione da dict, nested dict -> Bag
3.  fill_from(list)                 item numerati 0,1,2... dict item -> Bag
4.  fill_from(Bag)                  clone profondo dei nodi
5.  fill_from(bytes)                delega dopo decode utf-8
6.  fill_from(str) inline XML/JSON  detect dal primo carattere
7.  fill_from(file path .bag.json)  transport JSON (TYTX)
8.  fill_from(file path .bag.mp)    transport MessagePack
9.  fill_from(file path .xml)       transport XML
10. fill_from(Path)                 pathlib.Path equivalente a str
11. fill_from transport esplicito   override dell'estensione
12. fill_from raise su tipo invalido
13. fill_from atomic semantics      errore -> self invariato
14. fill_from chainable             ritorna self
15. deepcopy isolamento             modifiche alla copia non toccano l'original
16. update(dict) / update(Bag)      merge / ignore_none / nested
17. pickle roundtrip                __getstate__ / __setstate__
18. from_url                        marker network, test di smoke
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from genro_bag import Bag


# =============================================================================
# 1. fill_from(None)
# =============================================================================


class TestFillFromNone:
    def test_none_source_is_noop(self):
        """fill_from(None) non cambia nulla e ritorna self."""
        bag = Bag({"a": 1})
        result = bag.fill_from(None)
        assert result is bag
        assert bag.get_item("a") == 1

    def test_no_args_equivalent_to_none(self):
        """fill_from() senza argomenti (source default None) e' no-op."""
        bag = Bag({"a": 1})
        bag.fill_from()
        assert bag.get_item("a") == 1


# =============================================================================
# 2. fill_from(dict)
# =============================================================================


class TestFillFromDict:
    def test_flat_dict_populates_labels(self):
        """fill_from(dict) crea un nodo per chiave."""
        bag = Bag()
        bag.fill_from({"a": 1, "b": 2})
        assert bag.get_item("a") == 1
        assert bag.get_item("b") == 2

    def test_dict_replaces_existing_content(self):
        """fill_from(dict) rimpiazza il contenuto precedente."""
        bag = Bag({"old": 99})
        bag.fill_from({"new": 42})
        assert bag.get_item("old") is None
        assert bag.get_item("new") == 42

    def test_nested_dict_becomes_nested_bag(self):
        """Un dict annidato come valore diventa un Bag annidato."""
        bag = Bag()
        bag.fill_from({"outer": {"inner": 7}})
        # il valore di 'outer' e' una Bag navigabile via path puntato
        assert bag.get_item("outer.inner") == 7


# =============================================================================
# 3. fill_from(list)
# =============================================================================


class TestFillFromList:
    def test_list_creates_numbered_nodes(self):
        """fill_from(list) crea label '0', '1', '2'..."""
        bag = Bag()
        bag.fill_from(["a", "b", "c"])
        assert bag.get_item("0") == "a"
        assert bag.get_item("1") == "b"
        assert bag.get_item("2") == "c"

    def test_list_of_dicts_converts_each_to_bag(self):
        """Item dict in una lista diventa un Bag annidato."""
        bag = Bag()
        bag.fill_from([{"name": "alice"}, {"name": "bob"}])
        assert bag.get_item("0.name") == "alice"
        assert bag.get_item("1.name") == "bob"

    def test_empty_list_empties_bag(self):
        """fill_from([]) svuota la bag."""
        bag = Bag({"a": 1})
        bag.fill_from([])
        assert bag.keys() == []


# =============================================================================
# 4. fill_from(Bag)
# =============================================================================


class TestFillFromBag:
    def test_copies_nodes_from_source_bag(self):
        """fill_from(Bag) copia label, value e attributi."""
        src = Bag()
        src.set_item("a", 1, _attributes={"type": "int"})
        src.set_item("b", "hi")
        dst = Bag()
        dst.fill_from(src)
        assert dst.get_item("a") == 1
        assert dst.get_attr("a", "type") == "int"
        assert dst.get_item("b") == "hi"

    def test_nested_bag_is_deep_copied(self):
        """Sub-Bag nei nodi della sorgente vengono copiate in profondita'."""
        src = Bag()
        src["nest.inner"] = 42
        dst = Bag()
        dst.fill_from(src)
        # modifico la destinazione, l'originale non cambia
        dst["nest.inner"] = 99
        assert src.get_item("nest.inner") == 42


# =============================================================================
# 5. fill_from(bytes)
# =============================================================================


class TestFillFromBytes:
    def test_bytes_json_inline_is_decoded(self):
        """bytes contenente JSON inline viene decodificato come JSON."""
        bag = Bag()
        bag.fill_from(b'{"a": 1, "b": 2}')
        assert bag.get_item("a") == 1
        assert bag.get_item("b") == 2


# =============================================================================
# 6. fill_from(str) inline XML / JSON (auto-detect)
# =============================================================================


class TestFillFromInlineStr:
    def test_json_inline_detected_by_leading_brace(self):
        """Stringa che inizia con '{' e' parsata come JSON."""
        bag = Bag()
        bag.fill_from('{"a": 1, "b": 2}')
        assert bag.get_item("a") == 1
        assert bag.get_item("b") == 2

    def test_json_list_inline_detected_by_leading_bracket(self):
        """Stringa che inizia con '[' e' parsata come JSON (list).

        Una list JSON top-level produce nodi con prefix 'r_' e indice.
        """
        bag = Bag()
        bag.fill_from("[10, 20, 30]")
        assert bag.get_item("r_0") == 10
        assert bag.get_item("r_1") == 20
        assert bag.get_item("r_2") == 30

    def test_xml_inline_detected_by_leading_angle(self):
        """Stringa che inizia con '<' e' parsata come XML."""
        bag = Bag()
        bag.fill_from("<root><a>1</a></root>")
        # l'elemento root e' un contenitore che avvolge il nodo 'a'
        assert bag.get_item("root.a") == "1"


# =============================================================================
# 7-9. fill_from(file path) per estensione (JSON / msgpack / XML)
# =============================================================================


class TestFillFromFile:
    def test_bag_json_file(self, tmp_path: Path):
        """File con estensione .bag.json usa transport JSON (TYTX)."""
        # to_tytx aggiunge .bag.json automaticamente all'argomento filename
        src = Bag({"a": 1, "b": "hello"})
        src.to_tytx(filename=str(tmp_path / "sample"), transport="json")
        target = Bag()
        target.fill_from(str(tmp_path / "sample.bag.json"))
        assert target.get_item("a") == 1
        assert target.get_item("b") == "hello"

    def test_bag_mp_file(self, tmp_path: Path):
        """File con estensione .bag.mp usa transport MessagePack."""
        src = Bag({"a": 1, "b": "hello"})
        src.to_tytx(filename=str(tmp_path / "sample"), transport="msgpack")
        target = Bag()
        target.fill_from(str(tmp_path / "sample.bag.mp"))
        assert target.get_item("a") == 1
        assert target.get_item("b") == "hello"

    def test_xml_file(self, tmp_path: Path):
        """File con estensione .xml viene parsato come XML."""
        file = tmp_path / "sample.xml"
        file.write_text("<root><a>1</a></root>", encoding="utf-8")
        bag = Bag()
        bag.fill_from(str(file))
        assert bag.get_item("root.a") == "1"

    def test_file_not_found_raises(self):
        """File inesistente solleva FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Bag().fill_from("/nonexistent/path/file.xml")

    def test_unrecognized_extension_raises(self, tmp_path: Path):
        """Estensione non riconosciuta e senza transport esplicito solleva ValueError."""
        file = tmp_path / "sample.unknown"
        file.write_text("nothing", encoding="utf-8")
        with pytest.raises(ValueError):
            Bag().fill_from(str(file))


# =============================================================================
# 10. fill_from(Path) - pathlib
# =============================================================================


class TestFillFromPath:
    def test_pathlib_path_works_like_str(self, tmp_path: Path):
        """Un pathlib.Path e' equivalente a una stringa di path."""
        file = tmp_path / "sample.xml"
        file.write_text("<root><a>1</a></root>", encoding="utf-8")
        bag = Bag()
        bag.fill_from(file)
        assert bag.get_item("root.a") == "1"


# =============================================================================
# 11. fill_from con transport esplicito
# =============================================================================


class TestFillFromExplicitTransport:
    def test_transport_overrides_extension(self, tmp_path: Path):
        """transport='json' forza il formato indipendentemente dall'estensione."""
        src = Bag({"a": 1})
        # salvo con .bag.json ma rinomino a .dat
        src.to_tytx(filename=str(tmp_path / "sample"), transport="json")
        raw = (tmp_path / "sample.bag.json").read_text(encoding="utf-8")
        weird = tmp_path / "sample.dat"
        weird.write_text(raw, encoding="utf-8")

        target = Bag()
        target.fill_from(str(weird), transport="json")
        assert target.get_item("a") == 1


# =============================================================================
# 12. fill_from raise su tipo invalido
# =============================================================================


class TestFillFromInvalidType:
    def test_unsupported_type_raises_typeerror(self):
        """Un oggetto non gestibile solleva TypeError."""
        with pytest.raises(TypeError):
            Bag().fill_from(42)

    def test_tuple_also_unsupported(self):
        """Una tupla (non list) non e' supportata."""
        with pytest.raises(TypeError):
            Bag().fill_from((1, 2, 3))


# =============================================================================
# 13. fill_from - semantica atomica: errore -> self invariato
# =============================================================================


class TestFillFromAtomic:
    def test_typeerror_on_invalid_source_leaves_bag_unchanged(self):
        """Source con tipo non supportato: self resta intatta."""
        bag = Bag({"a": 1, "b": 2})
        with pytest.raises(TypeError):
            bag.fill_from(42)
        # contenuto invariato
        assert bag.get_item("a") == 1
        assert bag.get_item("b") == 2
        assert bag.keys() == ["a", "b"]

    def test_filenotfound_leaves_bag_unchanged(self):
        """File inesistente: self resta intatta dopo l'eccezione."""
        bag = Bag({"a": 1})
        with pytest.raises(FileNotFoundError):
            bag.fill_from("/nonexistent/file.xml")
        assert bag.get_item("a") == 1


# =============================================================================
# 14. fill_from chainable
# =============================================================================


class TestFillFromChainable:
    def test_returns_self_for_chaining(self):
        """fill_from ritorna self per concatenare chiamate."""
        bag = Bag()
        assert bag.fill_from({"a": 1}) is bag


# =============================================================================
# 15. deepcopy
# =============================================================================


class TestDeepcopy:
    def test_deepcopy_creates_independent_bag(self):
        """deepcopy crea una Bag nuova: modifiche non si propagano."""
        src = Bag({"a": 1, "b": 2})
        copy = src.deepcopy()
        copy["a"] = 99
        assert src.get_item("a") == 1
        assert copy.get_item("a") == 99

    def test_deepcopy_preserves_attributes(self):
        """deepcopy preserva attributi dei nodi come dict indipendente."""
        src = Bag()
        src.set_item("a", 1, _attributes={"type": "int"})
        copy = src.deepcopy()
        assert copy.get_attr("a", "type") == "int"

    def test_deepcopy_recurses_on_nested_bags(self):
        """Sub-Bag vengono copiate in profondita'."""
        src = Bag()
        src["outer.inner"] = 1
        copy = src.deepcopy()
        copy["outer.inner"] = 99
        assert src.get_item("outer.inner") == 1

    def test_deepcopy_same_class(self):
        """La copia e' un'istanza della stessa classe (per subclassing)."""
        src = Bag({"a": 1})
        copy = src.deepcopy()
        assert type(copy) is type(src)


# =============================================================================
# 16. update
# =============================================================================


class TestUpdate:
    def test_update_with_dict_adds_new_and_overwrites(self):
        """update(dict) aggiunge chiavi nuove e sovrascrive esistenti."""
        bag = Bag({"a": 1, "b": 2})
        bag.update({"a": 10, "c": 3})
        assert bag.get_item("a") == 10
        assert bag.get_item("b") == 2
        assert bag.get_item("c") == 3

    def test_update_with_bag_merges_attributes(self):
        """update(Bag) merge anche gli attributi dei nodi esistenti."""
        dst = Bag()
        dst.set_item("a", 1, _attributes={"x": 10})
        src = Bag()
        src.set_item("a", 2, _attributes={"y": 20})
        dst.update(src)
        assert dst.get_item("a") == 2
        assert dst.get_attr("a", "x") == 10
        assert dst.get_attr("a", "y") == 20

    def test_update_ignore_none_preserves_existing(self):
        """Con ignore_none=True, valori None non sovrascrivono."""
        bag = Bag({"a": 1})
        bag.update({"a": None}, ignore_none=True)
        assert bag.get_item("a") == 1

    def test_update_ignore_none_false_overwrites(self):
        """Con ignore_none=False (default), None sovrascrive."""
        bag = Bag({"a": 1})
        bag.update({"a": None})
        assert bag.get_item("a") is None

    def test_update_recurses_on_nested_bags(self):
        """Se entrambi hanno Bag nello stesso label, update ricorsivo."""
        dst = Bag()
        dst["outer.a"] = 1
        dst["outer.b"] = 2
        src = Bag()
        src["outer.a"] = 99
        src["outer.c"] = 3
        dst.update(src)
        assert dst.get_item("outer.a") == 99
        assert dst.get_item("outer.b") == 2
        assert dst.get_item("outer.c") == 3


# =============================================================================
# 17. pickle roundtrip
# =============================================================================


class TestPickle:
    def test_roundtrip_preserves_values(self):
        """Pickle-unpickle ricostruisce valori identici."""
        src = Bag({"a": 1, "b": "hi"})
        restored = pickle.loads(pickle.dumps(src))
        assert restored.get_item("a") == 1
        assert restored.get_item("b") == "hi"

    def test_roundtrip_preserves_attributes(self):
        """Pickle preserva gli attributi dei nodi."""
        src = Bag()
        src.set_item("a", 1, _attributes={"type": "int"})
        restored = pickle.loads(pickle.dumps(src))
        assert restored.get_attr("a", "type") == "int"

    def test_roundtrip_preserves_nested(self):
        """Pickle preserva strutture annidate."""
        src = Bag()
        src["outer.inner"] = 42
        restored = pickle.loads(pickle.dumps(src))
        assert restored.get_item("outer.inner") == 42

    def test_roundtrip_preserves_backref_state(self):
        """Pickle di una Bag con backref attivo restituisce una Bag con backref.

        Scenario: salviamo una Bag "vivente" (pronta a notificare) e dobbiamo
        ricostruirla nello stesso stato dopo l'unpickle.
        """
        src = Bag()
        src["outer.inner"] = 42
        src.set_backref()
        assert src.backref is True
        data = pickle.dumps(src)
        restored = pickle.loads(data)
        assert restored.backref is True
        # la sub-Bag annidata deve avere backref attivato anche lei
        inner = restored.get_item("outer")
        assert isinstance(inner, Bag)
        assert inner.backref is True

    def test_roundtrip_without_backref_stays_without_backref(self):
        """Pickle di una Bag senza backref resta senza backref dopo il restore."""
        src = Bag()
        src["outer.inner"] = 42
        assert src.backref is False
        restored = pickle.loads(pickle.dumps(src))
        assert restored.backref is False


# =============================================================================
# 18. from_url (marker network - smoke test)
# =============================================================================


class TestFromUrl:
    @pytest.mark.network
    def test_from_url_json_endpoint(self):
        """from_url fetcha un JSON endpoint pubblico e lo parsa."""
        # httpbin e' un endpoint di test comune; se down, il test skip per rete
        bag = Bag.from_url("https://httpbin.org/json")
        # httpbin.org/json ritorna un oggetto {"slideshow": {...}}
        assert "slideshow" in bag
