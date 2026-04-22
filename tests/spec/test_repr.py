"""Spec test: Bag - rappresentazioni string (__str__, to_string).

Dipende da test_basic.py (set_item, get_item, attributes).

I test verificano PROPRIETA' osservabili dell'output di stringa (contiene
la label, contiene il valore, gerarchia indentata) piuttosto che testare
il formato carattere-per-carattere. Il formato esatto puo' evolvere senza
rompere i test.

## Scala

1. __str__ su Bag vuoto            stringa vuota
2. __str__ mostra idx, label, valore, tipo
3. __str__ mostra attributi
4. __str__ gestisce Bag annidate   nested indentato
5. __str__ gestisce None e bytes
6. to_string su Bag vuoto          stringa vuota
7. to_string mostra label e valore in formato tree
8. to_string usa caratteri di tree (├──, └──)
9. to_string formatta attributi    [key=value]
10. to_string gestisce nesting     indentazione figli
"""

from __future__ import annotations

from genro_bag import Bag


# =============================================================================
# __str__
# =============================================================================


class TestStr:
    def test_empty_bag_str_is_empty(self):
        """str(Bag()) e' stringa vuota."""
        assert str(Bag()) == ""

    def test_str_contains_label_and_value(self):
        """str mostra label e valore di ogni nodo."""
        bag = Bag()
        bag["name"] = "alice"
        bag["count"] = 42
        out = str(bag)
        assert "name" in out
        assert "alice" in out
        assert "count" in out
        assert "42" in out

    def test_str_shows_index_of_each_node(self):
        """str prefissa ogni riga con l'indice del nodo."""
        bag = Bag({"a": 1, "b": 2})
        out = str(bag)
        # i due nodi hanno indici 0 e 1
        assert "0" in out
        assert "1" in out

    def test_str_shows_type_name(self):
        """str include il nome del tipo del valore (int, str, ...)."""
        bag = Bag()
        bag["x"] = 42
        bag["y"] = "hello"
        out = str(bag)
        assert "int" in out
        assert "str" in out

    def test_str_shows_attributes(self):
        """str include gli attributi del nodo quando presenti."""
        bag = Bag()
        bag.set_item("x", 1, _attributes={"type": "int"})
        out = str(bag)
        assert "type" in out

    def test_str_no_attr_marker_when_empty(self):
        """Quando il nodo non ha attributi, str non mostra '<>'."""
        bag = Bag({"a": 1})
        out = str(bag)
        assert "<>" not in out

    def test_str_nested_bag_indented(self):
        """str mostra le sub-Bag con label figli indentati."""
        bag = Bag()
        bag["outer.inner"] = 42
        out = str(bag)
        # sia 'outer' che 'inner' compaiono
        assert "outer" in out
        assert "inner" in out

    def test_str_handles_none_value(self):
        """str mostra 'None' per valori None."""
        bag = Bag()
        bag["empty"] = None
        out = str(bag)
        assert "None" in out
        assert "empty" in out

    def test_str_handles_bytes_value(self):
        """str decodifica bytes in UTF-8 per la visualizzazione."""
        bag = Bag()
        bag["b"] = b"hello"
        out = str(bag)
        assert "hello" in out


# =============================================================================
# to_string - ASCII tree
# =============================================================================


class TestToString:
    def test_empty_bag_returns_empty_string(self):
        """to_string() su Bag vuoto ritorna stringa vuota."""
        assert Bag().to_string() == ""

    def test_shows_label_and_value(self):
        """to_string mostra label: value per ogni nodo."""
        bag = Bag({"name": "alice", "age": 30})
        out = bag.to_string()
        assert "name" in out
        assert "alice" in out
        assert "age" in out
        assert "30" in out

    def test_uses_tree_characters(self):
        """to_string usa caratteri ├── e └── per i rami dell'albero."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        out = bag.to_string()
        # ultimo ha └──, gli altri ├──
        assert "├──" in out
        assert "└──" in out

    def test_formats_attributes_in_brackets(self):
        """to_string formatta gli attributi tra [ ] dopo la label."""
        bag = Bag()
        bag.set_item("user", "alice", _attributes={"id": 1})
        out = bag.to_string()
        assert "user" in out
        assert "id" in out
        # attributi racchiusi in parentesi quadre
        assert "[" in out
        assert "]" in out

    def test_nested_bag_children_are_indented(self):
        """to_string indenta i figli delle sub-Bag."""
        bag = Bag()
        bag["outer.inner"] = 42
        out = bag.to_string()
        lines = out.split("\n")
        # la riga con 'inner' e' piu' indentata di quella con 'outer'
        outer_line = next(l for l in lines if "outer" in l)
        inner_line = next(l for l in lines if "inner" in l)
        # conto spazi leading
        outer_indent = len(outer_line) - len(outer_line.lstrip(" │"))
        inner_indent = len(inner_line) - len(inner_line.lstrip(" │"))
        assert inner_indent > outer_indent

    def test_long_string_value_truncated(self):
        """Stringhe lunghe (>50) vengono troncate con '...'."""
        bag = Bag()
        long_value = "x" * 100
        bag["big"] = long_value
        out = bag.to_string()
        assert "..." in out

    def test_none_value_shown_as_none(self):
        """Valore None appare come 'None'."""
        bag = Bag()
        bag["empty"] = None
        out = bag.to_string()
        assert "None" in out

    def test_bytes_value_decoded(self):
        """bytes decodificati per la visualizzazione."""
        bag = Bag()
        bag["b"] = b"hello"
        out = bag.to_string()
        assert "hello" in out
