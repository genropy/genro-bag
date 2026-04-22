"""Spec test: Bag - operazioni base (no resolver, no subscribe).

## Principio di costruzione: scala di dipendenze

I test sono ordinati dal piu' semplice al piu' complesso. Ogni livello
usa SOLO i metodi validati nei livelli precedenti. L'ordine del file
e' il contratto.

Scala:
    1.  Bag()                          costruzione vuota (solo: non solleva)
    2.  Bag(dict) + bag.get(label)     co-validati come duali
    3.  bag.get_item(path)             path puntato + default
    4.  bag[path]                      zucchero per get_item
    5.  bag.set_item + bag.__setitem__ validati con get_item/get_attr
    6.  bag.get_node / bag.node        validati con metodi pubblici del nodo
    7.  dunder protocols               __len__, __iter__, __contains__, __call__
    8.  set_item ordering              usa __iter__ per osservare l'ordine
    9.  pop / __delitem__ / pop_node   usano set + get + __contains__
    10. clear                          usa set + __len__
    11. equality __eq__ / __ne__       usa costruzione + set
    12. proprieta' default root        parent, root, fullpath, attributes, backref
    13. set_attr / get_attr / del_attr / setdefault / as_dict
    14. set_item + resolver guard      usa set_callback_item come primitiva

## Regola per i BagNode restituiti

Quando set_item o get_node restituiscono un BagNode:
- verificare PRIMA il tipo (isinstance(..., BagNode))
- poi leggere le proprieta' via API pubblica del nodo (label, value, attr,
  get_attr, has_attr, is_branch, position, ...).
- mai toccare attributi privati.
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagNode, BagNodeException


# =============================================================================
# 1. Costruzione vuota
# =============================================================================


class TestBagConstruct:
    def test_empty_bag_does_not_raise(self):
        """Bag() costruisce un'istanza senza sollevare."""
        Bag()

    def test_bag_from_none_does_not_raise(self):
        """Bag(None) equivale a Bag() e non solleva."""
        Bag(None)


# =============================================================================
# 2. Bag(dict) + get  (co-validati)
# =============================================================================


class TestBagFromDictAndGet:
    def test_get_reads_value_initialized_from_dict(self):
        """Bag({'a': 1}).get('a') == 1: costruzione da dict e lettura duale."""
        bag = Bag({"a": 1})
        assert bag.get("a") == 1

    def test_get_missing_returns_none_by_default(self):
        """get('missing') ritorna None se il label non esiste."""
        bag = Bag({"a": 1})
        assert bag.get("missing") is None

    def test_get_missing_returns_default(self):
        """get(label, default) ritorna default se il label non esiste."""
        bag = Bag({"a": 1})
        assert bag.get("missing", "fallback") == "fallback"

    def test_get_empty_label_returns_self(self):
        """get('') ritorna la Bag stessa (convenzione documentata)."""
        bag = Bag({"a": 1})
        assert bag.get("") is bag

    def test_get_sharp_parent_returns_none_for_root(self):
        """get('#parent') su root ritorna None."""
        bag = Bag({"a": 1})
        assert bag.get("#parent") is None

    def test_from_empty_dict_does_not_raise(self):
        """Bag({}) e' equivalente a Bag() e get su qualunque label torna None."""
        bag = Bag({})
        assert bag.get("anything") is None

    def test_multiple_keys_from_dict_all_readable(self):
        """Bag({'a':1,'b':2}).get(...) legge ogni chiave iniziale."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.get("a") == 1
        assert bag.get("b") == 2
        assert bag.get("c") == 3


# =============================================================================
# 3. get_item (path puntato)
# =============================================================================


class TestGetItem:
    def test_single_level_path_matches_get(self):
        """get_item('a') su Bag({'a': 1}) == bag.get('a')."""
        bag = Bag({"a": 1})
        assert bag.get_item("a") == 1

    def test_missing_path_returns_none(self):
        """get_item su path inesistente ritorna None."""
        bag = Bag({"a": 1})
        assert bag.get_item("missing") is None

    def test_missing_path_returns_default(self):
        """get_item(path, default=X) ritorna X se path non esiste."""
        bag = Bag({"a": 1})
        assert bag.get_item("missing", default="fallback") == "fallback"

    def test_empty_path_returns_self(self):
        """get_item('') ritorna la Bag stessa."""
        bag = Bag({"a": 1})
        assert bag.get_item("") is bag


# =============================================================================
# 4. __getitem__ (bracket syntax)
# =============================================================================


class TestBracketGet:
    def test_bracket_equivalent_to_get_item(self):
        """bag['a'] delega a get_item('a')."""
        bag = Bag({"a": 1})
        assert bag["a"] == bag.get_item("a")


# =============================================================================
# 5. set_item (+ __setitem__) - validato con get_item / get_attr
# =============================================================================


class TestSetItem:
    def test_simple_label(self):
        """bag['a'] = 1; get_item('a') == 1."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_item("a") == 1

    def test_set_item_method_equivalent_to_bracket(self):
        """set_item('a', 1) equivale a bag['a'] = 1."""
        bag = Bag()
        bag.set_item("a", 1)
        assert bag.get_item("a") == 1

    def test_dotted_path(self):
        """set_item('a.b.c', 42); get_item duale sullo stesso path."""
        bag = Bag()
        bag.set_item("a.b.c", 42)
        assert bag.get_item("a.b.c") == 42

    def test_overwrite_value(self):
        """Assegnare due volte aggiorna il valore."""
        bag = Bag()
        bag["x"] = 1
        bag["x"] = 2
        assert bag.get_item("x") == 2

    def test_attributes_via_underscore_param(self):
        """_attributes={...} impostati sul nodo, leggibili via get_attr."""
        bag = Bag()
        bag.set_item("a.b", "hello", _attributes={"type": "greeting", "lang": "it"})
        assert bag.get_attr("a.b", "type") == "greeting"
        assert bag.get_attr("a.b", "lang") == "it"

    def test_kwargs_merged_into_attributes(self):
        """kwargs extra diventano attributi del nodo."""
        bag = Bag()
        bag.set_item("x", 1, type="int", size=4)
        assert bag.get_attr("x", "type") == "int"
        assert bag.get_attr("x", "size") == 4

    def test_kwargs_override_explicit_attributes(self):
        """kwargs vincono su _attributes."""
        bag = Bag()
        bag.set_item("x", 1, _attributes={"type": "old"}, type="new")
        assert bag.get_attr("x", "type") == "new"

    def test_query_syntax_sets_single_attribute(self):
        """set_item('x?attr', v) scrive solo l'attributo, il valore rimane."""
        bag = Bag()
        bag["x"] = 10
        bag.set_item("x?myattr", "attr_value")
        assert bag.get_attr("x", "myattr") == "attr_value"
        assert bag.get_item("x") == 10

    def test_query_syntax_sets_multiple_attributes(self):
        """set_item('x?a&b&c', (1,2,3)) imposta piu' attributi."""
        bag = Bag()
        bag["x"] = 0
        bag.set_item("x?a&b&c", (1, 2, 3))
        assert bag.get_attr("x", "a") == 1
        assert bag.get_attr("x", "b") == 2
        assert bag.get_attr("x", "c") == 3

    def test_fired_resets_value_to_none(self):
        """set_item(v, _fired=True): dopo la set, get_item e' None."""
        bag = Bag()
        bag.set_item("event", "click", _fired=True)
        assert bag.get_item("event") is None

    def test_returns_bagnode_instance(self):
        """set_item ritorna un BagNode (solo tipo verificato qui)."""
        bag = Bag()
        result = bag.set_item("a", 42)
        assert isinstance(result, BagNode)

    def test_returned_node_exposes_label_via_public_api(self):
        """Il BagNode restituito ha label pari al path finale."""
        bag = Bag()
        node = bag.set_item("a.b.c", 42)
        assert isinstance(node, BagNode)
        assert node.label == "c"

    def test_returned_node_exposes_value_via_public_api(self):
        """Il BagNode restituito ha value pari al valore assegnato."""
        bag = Bag()
        node = bag.set_item("a", 42)
        assert isinstance(node, BagNode)
        assert node.value == 42

    def test_returned_node_exposes_attr_via_public_api(self):
        """Il BagNode restituito ha attr pari al dict passato."""
        bag = Bag()
        node = bag.set_item("a", 1, _attributes={"k": "v"})
        assert isinstance(node, BagNode)
        assert node.attr == {"k": "v"}

    def test_returned_node_exposes_node_tag_via_public_api(self):
        """node_tag finisce come proprieta' pubblica del nodo."""
        bag = Bag()
        node = bag.set_item("doc", "hello", node_tag="paragraph")
        assert isinstance(node, BagNode)
        assert node.node_tag == "paragraph"


# =============================================================================
# 6. get_node / node - validati con API pubblica del BagNode
# =============================================================================


class TestGetNode:
    def test_get_node_returns_bagnode_instance(self):
        """get_node('a') ritorna un BagNode se il path esiste."""
        bag = Bag()
        bag["a"] = 42
        result = bag.get_node("a")
        assert isinstance(result, BagNode)

    def test_get_node_missing_returns_none(self):
        """get_node su path inesistente ritorna None."""
        bag = Bag()
        assert bag.get_node("missing") is None

    def test_get_node_exposes_value_attr_label(self):
        """Le proprieta' pubbliche del nodo restituito sono coerenti."""
        bag = Bag()
        bag.set_item("a", 42, _attributes={"type": "int"})
        node = bag.get_node("a")
        assert isinstance(node, BagNode)
        assert node.label == "a"
        assert node.value == 42
        assert node.attr == {"type": "int"}

    def test_get_node_autocreate_creates_missing(self):
        """autocreate=True crea il nodo se mancante."""
        bag = Bag()
        node = bag.get_node("new", autocreate=True)
        assert isinstance(node, BagNode)
        assert node.label == "new"
        # leggibile via get_item
        assert bag.get_item("new") is None

    def test_get_node_none_path_returns_parent_node(self):
        """get_node(None) su root ritorna None (no parent)."""
        bag = Bag()
        assert bag.get_node(None) is None

    def test_get_node_as_tuple_returns_container_and_node(self):
        """as_tuple=True ritorna (Bag, BagNode)."""
        bag = Bag()
        bag["a.b"] = 1
        result = bag.get_node("a.b", as_tuple=True)
        assert isinstance(result, tuple)
        container, node = result
        assert isinstance(container, Bag)
        assert isinstance(node, BagNode)
        assert node.label == "b"
        assert node.value == 1

    def test_node_first_level_by_label(self):
        """bag.node('a') accesso rapido al figlio diretto."""
        bag = Bag({"a": 1, "b": 2})
        n = bag.node("a")
        assert isinstance(n, BagNode)
        assert n.label == "a"
        assert n.value == 1

    def test_node_first_level_by_index(self):
        """bag.node(0) accesso per indice."""
        bag = Bag({"a": 1, "b": 2})
        n = bag.node(0)
        assert isinstance(n, BagNode)
        assert n.label == "a"

    def test_set_item_return_matches_get_node(self):
        """set_item('a', v) e get_node('a') restituiscono lo stesso nodo."""
        bag = Bag()
        set_ret = bag.set_item("a", 42)
        got = bag.get_node("a")
        assert set_ret is got


# =============================================================================
# 7. Dunder: __len__, __iter__, __contains__, __call__
# =============================================================================


class TestDunderProtocols:
    def test_len_empty_bag(self):
        """len(Bag()) == 0."""
        assert len(Bag()) == 0

    def test_len_counts_first_level_children(self):
        """len conta solo i figli diretti; path puntati contano il primo livello."""
        bag = Bag()
        bag["a"] = 1
        bag["b.c"] = 2
        assert len(bag) == 2

    def test_len_from_dict(self):
        """Bag({...}) ha len pari al numero di chiavi del dict."""
        assert len(Bag({"a": 1, "b": 2, "c": 3})) == 3

    def test_overwrite_does_not_increase_len(self):
        """Sovrascrivere un path esistente non cambia len."""
        bag = Bag()
        bag["x"] = 1
        bag["x"] = 2
        assert len(bag) == 1

    def test_contains_existing_path(self):
        """'a.b' in bag e' True dopo set_item('a.b')."""
        bag = Bag()
        bag["a.b"] = 1
        assert "a.b" in bag

    def test_contains_missing_path(self):
        """path mai settato -> not in bag."""
        bag = Bag()
        bag["a.b"] = 1
        assert "a.c" not in bag

    def test_contains_non_string_is_false(self):
        """in con tipi non supportati ritorna False."""
        bag = Bag({"a": 1})
        assert (123 in bag) is False  # type: ignore[operator]

    def test_iter_yields_bagnode_instances(self):
        """iter(bag) produce BagNode, non valori."""
        bag = Bag({"a": 1, "b": 2})
        items = list(bag)
        assert all(isinstance(n, BagNode) for n in items)

    def test_iter_preserves_insertion_order_from_dict(self):
        """Iterazione rispetta l'ordine di inserimento del dict iniziale."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert [n.label for n in bag] == ["a", "b", "c"]

    def test_call_no_args_returns_keys_list(self):
        """bag() senza argomenti ritorna lista delle chiavi di primo livello."""
        bag = Bag({"a": 1, "b": 2})
        assert bag() == ["a", "b"]

    def test_call_with_path_returns_value(self):
        """bag(path) equivale a bag[path]."""
        bag = Bag()
        bag["a.b"] = 42
        assert bag("a.b") == 42


# =============================================================================
# 8. set_item ordering (usa __iter__ validato sopra)
# =============================================================================


class TestSetItemOrdering:
    def test_sequential_set_appends(self):
        """set_item successivi aggiungono in coda (default)."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        assert [n.label for n in bag] == ["a", "b", "c"]

    def test_node_position_lt_prepends(self):
        """node_position='<' mette in testa."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("c", 3, node_position="<")
        assert [n.label for n in bag] == ["c", "a", "b"]

    def test_node_position_before_label(self):
        """node_position='<b' inserisce prima del label 'b'."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("x", 99, node_position="<b")
        assert [n.label for n in bag] == ["a", "x", "b"]

    def test_node_position_after_label(self):
        """node_position='>a' inserisce dopo il label 'a'."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.set_item("x", 99, node_position=">a")
        assert [n.label for n in bag] == ["a", "x", "b"]


# =============================================================================
# 9. pop / __delitem__ / pop_node
# =============================================================================


class TestPop:
    def test_pop_removes_and_returns_value(self):
        """pop('a.b') rimuove il nodo e ne restituisce il valore."""
        bag = Bag()
        bag["a.b"] = 42
        assert bag.pop("a.b") == 42
        assert "a.b" not in bag

    def test_pop_missing_returns_default(self):
        """pop su path inesistente restituisce default."""
        bag = Bag()
        assert bag.pop("missing", "gone") == "gone"

    def test_del_item_is_alias_for_pop(self):
        """del bag[path] rimuove il nodo."""
        bag = Bag()
        bag["a"] = 1
        del bag["a"]
        assert "a" not in bag

    def test_pop_node_returns_bagnode_instance(self):
        """pop_node restituisce un BagNode."""
        bag = Bag()
        bag.set_item("a", 42, _attributes={"type": "int"})
        node = bag.pop_node("a")
        assert isinstance(node, BagNode)
        assert node.label == "a"
        assert node.value == 42
        assert node.attr == {"type": "int"}

    def test_pop_node_missing_returns_none(self):
        """pop_node su path inesistente restituisce None."""
        bag = Bag()
        assert bag.pop_node("missing") is None


# =============================================================================
# 10. clear (usa set + __len__)
# =============================================================================


class TestClear:
    def test_clear_empties_bag(self):
        """clear() porta len a 0."""
        bag = Bag({"a": 1, "b": 2})
        bag.clear()
        assert len(bag) == 0

    def test_clear_on_empty_is_noop(self):
        """clear() su Bag vuoto non solleva."""
        bag = Bag()
        bag.clear()
        assert len(bag) == 0


# =============================================================================
# 11. __eq__ / __ne__
# =============================================================================


class TestEquality:
    def test_same_content_equal(self):
        """Due Bag costruite dallo stesso dict sono uguali."""
        assert Bag({"x": 1, "y": 2}) == Bag({"x": 1, "y": 2})

    def test_different_values_not_equal(self):
        """Bag con valori diversi sono diverse."""
        assert Bag({"x": 1}) != Bag({"x": 2})

    def test_different_order_not_equal(self):
        """L'ordine dei nodi conta per l'uguaglianza."""
        a = Bag()
        a["x"] = 1
        a["y"] = 2
        b = Bag()
        b["y"] = 2
        b["x"] = 1
        assert a != b

    def test_not_equal_to_non_bag(self):
        """Confronto con non-Bag e' sempre falso."""
        assert Bag({"a": 1}) != {"a": 1}
        assert Bag({"a": 1}) != "not a bag"
        assert Bag({"a": 1}) != 42


# =============================================================================
# 12. Proprieta' di root Bag
# =============================================================================


class TestRootProperties:
    def test_root_bag_has_no_parent(self):
        """Un Bag non annidato ha parent None."""
        assert Bag().parent is None

    def test_root_bag_has_no_parent_node(self):
        """Un Bag non annidato ha parent_node None."""
        assert Bag().parent_node is None

    def test_root_is_self_for_root_bag(self):
        """Il root di un Bag non annidato e' se stesso."""
        bag = Bag()
        assert bag.root is bag

    def test_fullpath_none_without_backref(self):
        """fullpath e' None senza backref abilitato."""
        bag = Bag()
        bag["a.b"] = 1
        inner = bag.get_item("a")
        assert isinstance(inner, Bag)
        assert inner.fullpath is None

    def test_attributes_empty_for_standalone_bag(self):
        """attributes e' dict vuoto per Bag senza parent_node."""
        assert Bag().attributes == {}

    def test_root_attributes_default_none(self):
        """root_attributes default e' None."""
        assert Bag().root_attributes is None

    def test_root_attributes_setter_stores_copy(self):
        """root_attributes setter salva il dict."""
        bag = Bag()
        bag.root_attributes = {"owner": "test"}
        assert bag.root_attributes == {"owner": "test"}

    def test_backref_default_false(self):
        """backref default e' False."""
        assert Bag().backref is False


# =============================================================================
# 13. set_attr / get_attr / del_attr / setdefault / as_dict
# =============================================================================


class TestAttrAccessors:
    def test_set_attr_on_existing_node(self):
        """set_attr aggiunge attributi a un nodo esistente."""
        bag = Bag()
        bag["a"] = 1
        bag.set_attr("a", type="int")
        assert bag.get_attr("a", "type") == "int"

    def test_get_attr_default_for_missing(self):
        """get_attr con default per attributo mancante."""
        bag = Bag()
        bag["a"] = 1
        assert bag.get_attr("a", "missing", default="x") == "x"

    def test_del_attr_removes(self):
        """del_attr rimuove l'attributo specifico."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"type": "int", "size": 4})
        bag.del_attr("a", "type")
        assert bag.get_attr("a", "type") is None
        assert bag.get_attr("a", "size") == 4

    def test_setdefault_returns_existing(self):
        """setdefault su path esistente non sovrascrive."""
        bag = Bag()
        bag["a"] = 1
        assert bag.setdefault("a", 99) == 1
        assert bag.get_item("a") == 1

    def test_setdefault_creates_if_missing(self):
        """setdefault crea il nodo se assente."""
        bag = Bag()
        assert bag.setdefault("new", 42) == 42
        assert bag.get_item("new") == 42

    def test_as_dict_first_level(self):
        """as_dict restituisce dict del primo livello."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.as_dict() == {"a": 1, "b": 2}


# =============================================================================
# 14. set_item + resolver guard
# =============================================================================


class TestSetItemResolverGuard:
    def test_raises_when_overwriting_resolver_without_param(self):
        """Sovrascrivere un nodo con resolver senza resolver= solleva BagNodeException."""
        bag = Bag()
        bag.set_callback_item("data", lambda: "computed")
        with pytest.raises(BagNodeException):
            bag.set_item("data", "new")

    def test_resolver_false_removes_resolver(self):
        """resolver=False rimuove il resolver e scrive il nuovo valore."""
        bag = Bag()
        bag.set_callback_item("data", lambda: "computed")
        bag.set_item("data", "new", resolver=False)
        # il nodo non ha piu' resolver e il valore nuovo e' letto
        assert bag.get_item("data") == "new"


# =============================================================================
# 15. move - riordino di nodi (drag & drop)
# =============================================================================


class TestMove:
    def test_move_single_node_forward(self):
        """move(0, 2) sposta il primo nodo alla posizione 2."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(0, 2)
        assert bag.keys() == ["b", "c", "a"]

    def test_move_single_node_backward(self):
        """move(2, 0) sposta l'ultimo nodo in testa."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(2, 0)
        assert bag.keys() == ["c", "a", "b"]

    def test_move_list_of_indices(self):
        """move([0, 2], 1) sposta piu' nodi mantenendo l'ordine relativo."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4
        bag.move([0, 2], 1)
        # i nodi spostati ('a' e 'c') vengono inseriti attorno alla destinazione
        # la chiave importante: i nodi non spostati conservano ordine relativo
        result = bag.keys()
        assert set(result) == {"a", "b", "c", "d"}
        # 'b' e 'd' (non spostati) mantengono ordine relativo
        assert result.index("b") < result.index("d")

    def test_move_to_same_position_is_noop(self):
        """move(1, 1) non cambia l'ordine."""
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.move(1, 1)
        assert bag.keys() == ["a", "b", "c"]


# =============================================================================
# 16. as_dict - flag ascii / lower
# =============================================================================


class TestAsDictFlags:
    def test_as_dict_lower(self):
        """as_dict(lower=True) restituisce chiavi in minuscolo."""
        bag = Bag()
        bag["Name"] = "alice"
        bag["AGE"] = 30
        result = bag.as_dict(lower=True)
        assert result == {"name": "alice", "age": 30}

    def test_as_dict_ascii(self):
        """as_dict(ascii=True) forza le chiavi a str (passaggio attraverso str())."""
        bag = Bag()
        bag["a"] = 1
        result = bag.as_dict(ascii=True)
        assert result == {"a": 1}


# =============================================================================
# 17. nodes property
# =============================================================================


class TestNodesProperty:
    def test_nodes_returns_list_of_bagnodes(self):
        """bag.nodes e' l'alias della lista di BagNode di primo livello."""
        bag = Bag({"a": 1, "b": 2})
        nodes = bag.nodes
        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert all(isinstance(n, BagNode) for n in nodes)
        assert [n.label for n in nodes] == ["a", "b"]


# =============================================================================
# 18. __contains__ con un BagNode
# =============================================================================


class TestContainsNode:
    def test_node_in_bag_after_insertion(self):
        """Un BagNode ottenuto via set_item e' contenuto nella Bag."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node in bag

    def test_node_not_in_bag_after_pop(self):
        """Un BagNode estratto con pop_node non e' piu' contenuto."""
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        assert node not in bag


# =============================================================================
# 19. Path navigation: #parent, ../, backslash escape
# =============================================================================


class TestPathNavigation:
    def test_parent_navigation_with_dotdot(self):
        """Un path che inizia con '../' accede al parent della Bag corrente.

        Richiede una Bag nested con backref (#parent resolve via parent chain).
        """
        root = Bag()
        root["outer.inner"] = "target"
        root["outer.sibling"] = "neighbor"
        root.subscribe("w", update=lambda **kw: None)  # abilita backref
        inner_bag = root.get_item("outer")
        assert isinstance(inner_bag, Bag)
        # dal contenitore 'outer' navigo a ../outer.inner
        assert inner_bag.get_item("../outer.inner") == "target"

    def test_parent_navigation_with_sharp_parent(self):
        """'#parent' equivale a '../' (risolve al parent)."""
        root = Bag()
        root["outer.inner"] = "target"
        root.subscribe("w", update=lambda **kw: None)
        inner_bag = root.get_item("outer")
        assert isinstance(inner_bag, Bag)
        # #parent ritorna il Bag parent
        assert inner_bag.get("#parent") is root

    def test_backslash_escape_for_literal_dot_in_label(self):
        """Un path con '\\.' tratta il punto come parte del label, non separatore.

        Scenario: label che contengono un punto (es. email, domini, versioni).
        """
        bag = Bag()
        # set_item con path 'user\.name' crea UN nodo con label 'user.name',
        # non due nodi annidati
        bag.set_item("user\\.name", "alice")
        # la lettura con lo stesso escape ritrova il valore
        assert bag.get_item("user\\.name") == "alice"
        # l'accesso "ingenuo" (senza escape) invece interpreta il punto
        # come separatore: 'user' seguito da 'name' non esiste
        assert bag.get_item("user.name") is None


# =============================================================================
# 20. bag.get con pattern '#' - accesso posizionale e per attributo/valore
# =============================================================================


class TestGetWithSharpPatterns:
    def test_get_by_numeric_index(self):
        """bag.get('#0') ritorna il valore del nodo all'indice 0."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.get("#0") == 1
        assert bag.get("#1") == 2
        assert bag.get("#2") == 3

    def test_get_by_numeric_index_out_of_range_returns_default(self):
        """bag.get('#99') oltre i nodi ritorna default."""
        bag = Bag({"a": 1})
        assert bag.get("#99", default="gone") == "gone"

    def test_get_by_attribute_match(self):
        """bag.get('#attr=value') ritorna il valore del nodo con quell'attributo.

        Scenario reale: ricerca di un record in una lista ordinata per 'id' logico.
        """
        bag = Bag()
        bag.set_item("row1", "alice", _attributes={"id": "x"})
        bag.set_item("row2", "bob", _attributes={"id": "y"})
        assert bag.get("#id=x") == "alice"
        assert bag.get("#id=y") == "bob"

    def test_get_by_attribute_match_no_result_returns_default(self):
        """bag.get('#id=missing') quando nessun match ritorna default."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"id": "x"})
        assert bag.get("#id=missing", default="none") == "none"

    def test_get_by_value_match(self):
        """bag.get('#=value') ritorna il valore del primo nodo con quel valore."""
        bag = Bag()
        bag.set_item("a", "foo")
        bag.set_item("b", "bar")
        assert bag.get("#=foo") == "foo"
        assert bag.get("#=bar") == "bar"


# =============================================================================
# 21. node_position avanzato: '#n', '<#n', '>#n', '<missing'
# =============================================================================


class TestNodePositionSharpSyntax:
    def test_position_sharp_n_insert_at_index(self):
        """node_position='#2' inserisce all'indice 2."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position="#1")
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_lt_sharp_n_insert_before_index(self):
        """node_position='<#n' inserisce prima dell'indice n."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position="<#1")
        assert bag.keys() == ["a", "new", "b", "c"]

    def test_position_gt_sharp_n_insert_after_index(self):
        """node_position='>#n' inserisce dopo l'indice n."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        bag.set_item("new", 99, node_position=">#1")
        assert bag.keys() == ["a", "b", "new", "c"]

    def test_position_lt_missing_label_appends(self):
        """node_position='<missing' con label inesistente: appende in coda (fallback)."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position="<nonexistent")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_gt_missing_label_appends(self):
        """node_position='>missing' con label inesistente: appende in coda."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position=">nonexistent")
        assert bag.keys() == ["a", "b", "new"]

    def test_position_integer_clamped_to_valid_range(self):
        """node_position=int oltre len viene limitato a len (append)."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position=999)
        # aggiunto in coda
        assert bag.keys()[-1] == "new"

    def test_position_negative_integer_clamped_to_zero(self):
        """node_position=int negativo viene limitato a 0 (prepend)."""
        bag = Bag({"a": 1, "b": 2})
        bag.set_item("new", 99, node_position=-5)
        assert bag.keys()[0] == "new"
