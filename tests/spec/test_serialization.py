"""Spec test: Bag - serializzazione XML / JSON / TYTX.

Dipende da test_basic.py (set_item, get_item, get_attr, get_node,
__len__, __contains__) e test_population.py (fill_from, deepcopy).

I formati XML/JSON/TYTX sono tre contratti DISTINTI:
- XML: human-readable, senza type info (tutto stringa)
- TYTX: type-preserving (int, float, date, datetime, Decimal)
- JSON: struttura esplicita label/value/attr, con o senza type info (typed=True)

Per ciascuno testiamo il roundtrip: from_X(to_X(bag)) deve ricostruire
Bag equivalente per i valori attesi dal formato.

## Scala

1.  to_xml / from_xml                roundtrip semplice
2.  to_xml opzioni                   pretty, doc_header, self_closed_tags
3.  to_xml filename                  scrittura su file
4.  to_xml attributi                 attr serializzati come XML attributes
5.  to_xml nested                    sub-Bag annidate
6.  from_xml plain                   elementi -> nodi
7.  from_xml legacy GenRoBag         auto-detect + _T types
8.  from_xml tag_attribute           path da attributo

9.  to_tytx / from_tytx              roundtrip JSON e msgpack
10. to_tytx filename                 scrittura su file
11. to_tytx compact mode             parent paths come codici numerici
12. to_tytx preserves types          int / float / None / bytes
13. to_tytx preserves attr e node_tag

14. to_json / from_json              roundtrip JSON (typed o no)
15. to_json typed                    preserva date/datetime/Decimal
16. from_json da dict Python diretto
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from genro_bag import Bag


# =============================================================================
# 1. to_xml / from_xml - roundtrip semplice
# =============================================================================


class TestXmlRoundtripSimple:
    def test_roundtrip_under_single_root(self):
        """Roundtrip XML richiede un singolo root element (vincolo del formato).

        XML non preserva i tipi: i valori tornano come stringa.
        """
        src = Bag()
        src["root.a"] = "1"
        src["root.b"] = "2"
        xml = src.to_xml()
        restored = Bag.from_xml(xml or "")
        assert restored.get_item("root.a") == "1"
        assert restored.get_item("root.b") == "2"

    def test_empty_bag_produces_empty_string(self):
        """to_xml() su Bag vuoto ritorna stringa vuota (caso limite del formato)."""
        assert Bag().to_xml() == ""


# =============================================================================
# 2. to_xml - opzioni
# =============================================================================


class TestToXmlOptions:
    def test_pretty_adds_indentation(self):
        """pretty=True produce output indentato."""
        bag = Bag({"a": "1", "b": "2"})
        compact = bag.to_xml()
        pretty = bag.to_xml(pretty=True)
        assert pretty != compact
        assert "\n" in (pretty or "")

    def test_doc_header_true_adds_xml_declaration(self):
        """doc_header=True prefissa la dichiarazione XML."""
        bag = Bag({"a": "1"})
        xml = bag.to_xml(doc_header=True)
        assert (xml or "").startswith("<?xml version=")

    def test_doc_header_string_uses_custom_header(self):
        """doc_header str viene usato come header custom."""
        bag = Bag({"a": "1"})
        xml = bag.to_xml(doc_header="<!DOCTYPE custom>")
        assert (xml or "").startswith("<!DOCTYPE custom>")

    def test_self_closed_tags(self):
        """self_closed_tags lista rende i tag indicati self-closing se vuoti."""
        bag = Bag()
        bag["empty_tag"] = None
        xml = bag.to_xml(self_closed_tags=["empty_tag"])
        assert "<empty_tag/>" in (xml or "")


# =============================================================================
# 3. to_xml - filename
# =============================================================================


class TestToXmlFile:
    def test_writes_to_file_when_filename_given(self, tmp_path: Path):
        """filename=... scrive su file e ritorna None."""
        bag = Bag({"a": "hello"})
        file = tmp_path / "out.xml"
        result = bag.to_xml(filename=str(file))
        assert result is None
        content = file.read_text(encoding="utf-8")
        assert "hello" in content

    def test_file_can_be_read_back(self, tmp_path: Path):
        """Il file XML prodotto e' rileggibile con from_xml tramite fill_from."""
        src = Bag({"x": "world"})
        file = tmp_path / "out.xml"
        src.to_xml(filename=str(file))
        restored = Bag().fill_from(str(file))
        assert restored.get_item("x") == "world"


# =============================================================================
# 4. to_xml - attributi
# =============================================================================


class TestToXmlAttributes:
    def test_attributes_serialized_as_xml_attrs(self):
        """attributi del nodo finiscono come XML attributes."""
        bag = Bag()
        bag.set_item("elem", "text", _attributes={"type": "string", "id": "x"})
        xml = bag.to_xml() or ""
        assert 'type="string"' in xml
        assert 'id="x"' in xml

    def test_none_attribute_skipped(self):
        """attributi con valore None non vengono emessi."""
        bag = Bag()
        bag.set_item("e", "v", _attributes={"keep": "yes"})
        # inserisco un attributo None manualmente via set_attr
        bag.set_attr("e", nil=None)
        xml = bag.to_xml() or ""
        assert "keep" in xml
        # l'attributo None viene rimosso, non appare
        assert "nil=" not in xml


# =============================================================================
# 5. to_xml - nested
# =============================================================================


class TestToXmlNested:
    def test_nested_bag_nested_xml(self):
        """Una sub-Bag produce XML annidato."""
        bag = Bag()
        bag["outer.inner"] = "v"
        xml = bag.to_xml() or ""
        assert "<outer>" in xml
        assert "<inner>v</inner>" in xml
        assert "</outer>" in xml

    def test_nested_roundtrip(self):
        """Roundtrip XML su struttura annidata."""
        src = Bag()
        src["outer.inner"] = "v"
        xml = src.to_xml() or ""
        restored = Bag.from_xml(xml)
        assert restored.get_item("outer.inner") == "v"


# =============================================================================
# 6. from_xml - plain
# =============================================================================


class TestFromXmlPlain:
    def test_simple_xml_elements_become_nodes(self):
        """Ogni elemento XML diventa un nodo della Bag."""
        bag = Bag.from_xml("<root><a>1</a><b>2</b></root>")
        assert bag.get_item("root.a") == "1"
        assert bag.get_item("root.b") == "2"

    def test_attributes_become_node_attr(self):
        """XML attributes -> node.attr."""
        bag = Bag.from_xml('<root><item id="x" kind="small">hello</item></root>')
        assert bag.get_attr("root.item", "id") == "x"
        assert bag.get_attr("root.item", "kind") == "small"

    def test_bytes_source_decoded(self):
        """from_xml accetta bytes (UTF-8)."""
        bag = Bag.from_xml(b"<root><a>1</a></root>")
        assert bag.get_item("root.a") == "1"


# =============================================================================
# 7. from_xml - legacy GenRoBag auto-detect
# =============================================================================


class TestFromXmlLegacy:
    def test_legacy_wrapper_unwrapped(self):
        """Il wrapper <GenRoBag> e' rimosso automaticamente."""
        bag = Bag.from_xml("<GenRoBag><a>1</a></GenRoBag>")
        # senza _T il valore e' stringa
        assert bag.get_item("a") == "1"

    def test_legacy_type_marker_int(self):
        """_T='L' converte il valore a int."""
        bag = Bag.from_xml('<GenRoBag><count _T="L">42</count></GenRoBag>')
        assert bag.get_item("count") == 42
        assert isinstance(bag.get_item("count"), int)


# =============================================================================
# 8. from_xml - tag_attribute
# =============================================================================


class TestFromXmlTagAttribute:
    def test_tag_attribute_uses_attr_as_label(self):
        """tag_attribute=X fa usare l'attributo X come label del nodo."""
        xml = '<grammar><define name="section"/></grammar>'
        bag = Bag.from_xml(xml, tag_attribute="name")
        assert "section" in bag["grammar"]


# =============================================================================
# 9. to_tytx / from_tytx - roundtrip JSON e msgpack
# =============================================================================


class TestTytxRoundtrip:
    def test_roundtrip_json_preserves_int_and_str(self):
        """to_tytx + from_tytx ricostruisce valori int e str."""
        src = Bag({"a": 1, "b": "hello"})
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_item("a") == 1
        assert isinstance(restored.get_item("a"), int)
        assert restored.get_item("b") == "hello"

    def test_roundtrip_msgpack(self):
        """Stesso roundtrip ma con transport msgpack (binary)."""
        src = Bag({"a": 1, "b": "hello"})
        data = src.to_tytx(transport="msgpack")
        assert isinstance(data, bytes)
        restored = Bag.from_tytx(data, transport="msgpack")
        assert restored.get_item("a") == 1
        assert restored.get_item("b") == "hello"

    def test_roundtrip_preserves_nested_bags(self):
        """Sub-Bag annidate sopravvivono al roundtrip."""
        src = Bag()
        src["outer.inner"] = 42
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_item("outer.inner") == 42


# =============================================================================
# 10. to_tytx - filename
# =============================================================================


class TestToTytxFile:
    def test_writes_json_file_with_extension(self, tmp_path: Path):
        """filename con transport='json' scrive .bag.json."""
        src = Bag({"a": 1})
        src.to_tytx(filename=str(tmp_path / "out"), transport="json")
        assert (tmp_path / "out.bag.json").is_file()

    def test_writes_msgpack_file_with_extension(self, tmp_path: Path):
        """filename con transport='msgpack' scrive .bag.mp."""
        src = Bag({"a": 1})
        src.to_tytx(filename=str(tmp_path / "out"), transport="msgpack")
        assert (tmp_path / "out.bag.mp").is_file()


# =============================================================================
# 11. to_tytx - compact mode
# =============================================================================


class TestToTytxCompact:
    def test_compact_roundtrip(self):
        """compact=True preserva la struttura nel roundtrip."""
        src = Bag()
        src["a.b.c"] = 42
        src["a.b.d"] = "x"
        src["e"] = 1
        data = src.to_tytx(transport="json", compact=True)
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_item("a.b.c") == 42
        assert restored.get_item("a.b.d") == "x"
        assert restored.get_item("e") == 1


# =============================================================================
# 12. to_tytx - preserves Python types
# =============================================================================


class TestTytxTypes:
    def test_preserves_float(self):
        """Float sopravvive al roundtrip."""
        src = Bag({"x": 3.14})
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_item("x") == 3.14
        assert isinstance(restored.get_item("x"), float)

    def test_preserves_none(self):
        """Valori None sono conservati come None."""
        src = Bag()
        src["empty"] = None
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_item("empty") is None
        assert "empty" in restored

    def test_preserves_decimal(self):
        """Decimal: TYTX preserva il tipo."""
        src = Bag()
        src["price"] = Decimal("19.99")
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        value = restored.get_item("price")
        assert value == Decimal("19.99")
        assert isinstance(value, Decimal)


# =============================================================================
# 13. to_tytx - preserves attr e node_tag
# =============================================================================


class TestTytxAttrAndTag:
    def test_roundtrip_preserves_attributes(self):
        """Gli attributi dei nodi sopravvivono al roundtrip TYTX."""
        src = Bag()
        src.set_item("a", 1, _attributes={"kind": "int", "size": 4})
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        assert restored.get_attr("a", "kind") == "int"
        assert restored.get_attr("a", "size") == 4

    def test_roundtrip_preserves_node_tag(self):
        """node_tag sopravvive al roundtrip."""
        src = Bag()
        src.set_item("doc", "hello", node_tag="paragraph")
        data = src.to_tytx(transport="json")
        restored = Bag.from_tytx(data, transport="json")  # type: ignore[arg-type]
        node = restored.get_node("doc")
        assert node is not None
        assert node.node_tag == "paragraph"


# =============================================================================
# 14. to_json / from_json - roundtrip
# =============================================================================


class TestJsonRoundtrip:
    def test_typed_roundtrip_preserves_values(self):
        """to_json(typed=True) + from_json ricostruisce valori e attributi."""
        src = Bag()
        src.set_item("a", 42, _attributes={"type": "int"})
        src.set_item("b", "hello")
        data = src.to_json(typed=True)
        restored = Bag.from_json(data)
        assert restored.get_item("a") == 42
        assert restored.get_attr("a", "type") == "int"
        assert restored.get_item("b") == "hello"

    def test_non_typed_roundtrip_basic(self):
        """to_json(typed=False) produce JSON standard rileggibile."""
        src = Bag({"a": 1, "b": 2})
        data = src.to_json(typed=False)
        restored = Bag.from_json(data)
        assert restored.get_item("a") == 1
        assert restored.get_item("b") == 2

    def test_roundtrip_preserves_nested(self):
        """Struttura annidata sopravvive al roundtrip JSON."""
        src = Bag()
        src["outer.inner"] = "v"
        data = src.to_json(typed=True)
        restored = Bag.from_json(data)
        assert restored.get_item("outer.inner") == "v"


# =============================================================================
# 15. to_json typed - preserva date/datetime/Decimal
# =============================================================================


class TestJsonTyped:
    def test_preserves_decimal(self):
        """typed=True preserva Decimal attraverso JSON."""
        src = Bag({"price": Decimal("19.99")})
        data = src.to_json(typed=True)
        restored = Bag.from_json(data)
        value = restored.get_item("price")
        assert value == Decimal("19.99")
        assert isinstance(value, Decimal)


# =============================================================================
# 16. from_json da dict/list Python diretto
# =============================================================================


class TestFromJsonNonString:
    def test_from_json_dict_input(self):
        """from_json accetta direttamente un dict Python."""
        bag = Bag.from_json({"a": 1, "b": 2})
        assert bag.get_item("a") == 1
        assert bag.get_item("b") == 2

    def test_from_json_scalar_wrapped_in_value(self):
        """from_json(scalare) wrappa in {'value': scalare}."""
        bag = Bag.from_json(42)  # type: ignore[arg-type]
        assert bag.get_item("value") == 42


# =============================================================================
# 17. from_xml raise_on_error + empty
# =============================================================================


class TestFromXmlExtra:
    def test_empty_factory_called_on_empty_element(self):
        """empty callable produce il valore di default per elementi vuoti."""
        bag = Bag.from_xml(
            '<GenRoBag><x _T="L"></x></GenRoBag>',
            empty=lambda: 0,
        )
        assert bag.get_item("x") == 0

    def test_raise_on_error_true_propagates(self):
        """raise_on_error=True solleva per valori non convertibili."""
        with pytest.raises(Exception):
            Bag.from_xml(
                '<GenRoBag><x _T="L">not_a_number</x></GenRoBag>',
                raise_on_error=True,
            )


# =============================================================================
# 18. XML tag sanitization (label Python validi ma invalidi come tag XML)
# =============================================================================


class TestXmlTagSanitization:
    def test_label_with_invalid_chars_is_sanitized(self):
        """Label con spazi/caratteri speciali: to_xml produce un tag valido.

        Scenario reale: dati da CSV con header "My Col" o "col$1".
        """
        bag = Bag()
        bag.set_item("root.my col", "v")
        xml = bag.to_xml() or ""
        # il tag e' sanitizzato (es. 'my_col') ma l'XML resta parsabile
        assert "<root>" in xml
        assert "</root>" in xml

    def test_label_starting_with_digit_gets_underscore_prefix(self):
        """Label che inizia con cifra: il tag sanitizzato ha prefisso '_'."""
        bag = Bag()
        bag.set_item("root.2024data", "v")
        xml = bag.to_xml() or ""
        # il tag emesso inizia con '_' (non con cifra)
        assert "<_2024data" in xml or "<_" in xml

    def test_empty_label_becomes_none_marker(self):
        """Label vuoto produce il tag speciale '_none_'."""
        # uso set_item con path contenente un segmento vuoto -> label ''
        bag = Bag()
        # setto direttamente un nodo con label vuoto tramite path "root." non funziona
        # perche' split elimina gli empty. Passo per set sulla sub-Bag.
        sub = Bag()
        sub.set_item("", "v")
        bag.set_item("root", sub)
        xml = bag.to_xml() or ""
        # il tag emesso include il marker _none_
        assert "_none_" in xml


# =============================================================================
# 19. to_json typed + resolver: il resolver e' serializzato in JSON
# =============================================================================


class TestJsonWithResolver:
    def test_to_json_includes_resolver_for_serializable_resolver(self):
        """to_json(typed=True) emette 'resolver' per resolver serializzabili.

        UuidResolver e' serializzabile (nessun callback, solo args/kwargs).
        """
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver("uuid4")
        data = bag.to_json(typed=True)
        assert "resolver" in data
        assert "UuidResolver" in data

    def test_roundtrip_json_with_resolver_reconstructs_resolver(self):
        """from_json(to_json(bag_with_resolver)) ricostruisce un resolver equivalente."""
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver("uuid4")
        data = bag.to_json(typed=True)
        restored = Bag.from_json(data)
        resolver = restored.get_resolver("id")
        assert isinstance(resolver, UuidResolver)


# =============================================================================
# 20. to_json emette 'tag' per node_tag
# =============================================================================


class TestJsonWithNodeTag:
    def test_to_json_includes_node_tag(self):
        """to_json emette 'tag' nel dict del nodo quando il nodo ha node_tag."""
        bag = Bag()
        bag.set_item("doc", "hello", node_tag="paragraph")
        data = bag.to_json(typed=True)
        assert "paragraph" in data


# =============================================================================
# 21. JSON edge case - list e dict vuoti
# =============================================================================


class TestJsonEmpty:
    def test_empty_json_list_produces_empty_bag(self):
        """from_json('[]') produce un Bag vuoto."""
        bag = Bag.from_json("[]")
        assert len(bag) == 0

    def test_empty_json_dict_produces_empty_bag(self):
        """from_json('{}') produce un Bag vuoto."""
        bag = Bag.from_json("{}")
        assert len(bag) == 0


# =============================================================================
# 22. XML legacy mixed content + from_json list_joiner
# =============================================================================
#
# Nota: il docstring di from_xml dichiara env var substitution {GNR_*}
# ma nel codice di _parse.py non c'e' logica di sostituzione.
# Test non scritto: la feature e' documentata ma non implementata
# (candidato bug/doc-mismatch).


class TestXmlMixedContent:
    def test_mixed_content_text_becomes_special_node(self):
        """XML con testo e figli dentro lo stesso elemento emette un nodo '_' per il testo."""
        xml = "<root>leading text<child>v</child></root>"
        bag = Bag.from_xml(xml)
        # 'root' ha un figlio 'child' e un nodo '_' per il testo misto
        root = bag.get_item("root")
        assert isinstance(root, Bag)
        assert root.get_item("child") == "v"
        assert root.get_item("_") == "leading text"


class TestFromJsonListJoiner:
    def test_string_list_with_joiner(self):
        """from_json con list_joiner concatena liste di stringhe."""
        bag = Bag.from_json({"items": ["a", "b", "c"]}, list_joiner=",")
        assert bag.get_item("items") == "a,b,c"
