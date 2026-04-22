"""Spec test: Bag - query / iterazione / aggregazione.

Dipende da test_basic.py: qui si assume che set_item, get_item, get_attr,
get_node, __len__, __iter__, __contains__ siano validi.

## Scala di dipendenze in questo file

1.  keys()                          primitive piu' semplice
2.  values()
3.  items()
4.  keys/values/items con iter=True (generator)
5.  is_empty()
6.  get_nodes()
7.  get_node_by_attr()
8.  get_node_by_value()
9.  walk() generator mode            usa BagNode.label / .value / path puntati
10. walk() callback mode
11. query()                          varianti what/deep/leaf/branch/condition/limit
12. digest()                         alias di query + as_columns
13. columns()                        wrapper su digest
14. sum()
15. sort()                           osservato tramite keys()/values() gia' validati
"""

from __future__ import annotations

from genro_bag import Bag, BagNode


# =============================================================================
# 1. keys()
# =============================================================================


class TestKeys:
    def test_empty_bag_returns_empty_list(self):
        """keys() su Bag vuoto ritorna lista vuota."""
        assert Bag().keys() == []

    def test_returns_labels_in_insertion_order(self):
        """keys() ritorna le label nell'ordine di inserimento."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.keys() == ["a", "b", "c"]

    def test_first_level_only(self):
        """keys() vede solo il primo livello (anche con path puntati)."""
        bag = Bag()
        bag["a.b.c"] = 1
        bag["x"] = 2
        assert bag.keys() == ["a", "x"]


# =============================================================================
# 2. values()
# =============================================================================


class TestValues:
    def test_empty_bag_returns_empty_list(self):
        """values() su Bag vuoto ritorna lista vuota."""
        assert Bag().values() == []

    def test_returns_values_in_order(self):
        """values() ritorna i valori nell'ordine di inserimento."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.values() == [1, 2, 3]

    def test_nested_bag_value_is_bag_instance(self):
        """Se un nodo ha come valore una Bag, values() lo espone come tale."""
        bag = Bag()
        bag["a.b"] = 1
        vals = bag.values()
        assert len(vals) == 1
        assert isinstance(vals[0], Bag)


# =============================================================================
# 3. items()
# =============================================================================


class TestItems:
    def test_empty_bag_returns_empty_list(self):
        """items() su Bag vuoto ritorna lista vuota."""
        assert Bag().items() == []

    def test_returns_label_value_tuples(self):
        """items() ritorna (label, value) in ordine."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.items() == [("a", 1), ("b", 2)]


# =============================================================================
# 4. keys/values/items con iter=True (generator)
# =============================================================================


class TestIterVariants:
    def test_keys_iter_returns_iterator(self):
        """keys(iter=True) ritorna un iteratore, non una lista."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.keys(iter=True)
        assert not isinstance(result, list)
        assert list(result) == ["a", "b"]

    def test_values_iter_returns_iterator(self):
        """values(iter=True) ritorna un iteratore."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.values(iter=True)
        assert not isinstance(result, list)
        assert list(result) == [1, 2]

    def test_items_iter_returns_iterator(self):
        """items(iter=True) ritorna un iteratore."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.items(iter=True)
        assert not isinstance(result, list)
        assert list(result) == [("a", 1), ("b", 2)]


# =============================================================================
# 5. is_empty()
# =============================================================================


class TestIsEmpty:
    def test_empty_bag_is_empty(self):
        """Un Bag appena creato e' vuoto."""
        assert Bag().is_empty() is True

    def test_bag_with_non_none_value_is_not_empty(self):
        """Un nodo con valore 1 rende la Bag non vuota."""
        bag = Bag()
        bag["a"] = 1
        assert bag.is_empty() is False

    def test_bag_with_only_none_values_is_empty(self):
        """Nodi con valore None contano come vuoti."""
        bag = Bag()
        bag["a"] = None
        bag["b"] = None
        assert bag.is_empty() is True

    def test_zero_is_none_treats_zero_as_empty(self):
        """Con zero_is_none=True anche 0 conta come vuoto."""
        bag = Bag()
        bag["a"] = 0
        assert bag.is_empty(zero_is_none=True) is True
        assert bag.is_empty() is False

    def test_blank_is_none_treats_empty_string_as_empty(self):
        """Con blank_is_none=True anche '' conta come vuoto."""
        bag = Bag()
        bag["a"] = ""
        assert bag.is_empty(blank_is_none=True) is True
        assert bag.is_empty() is False


# =============================================================================
# 6. get_nodes()
# =============================================================================


class TestGetNodes:
    def test_empty_bag_returns_empty_list(self):
        """get_nodes() su Bag vuoto ritorna lista vuota."""
        assert Bag().get_nodes() == []

    def test_returns_all_first_level_nodes(self):
        """get_nodes() senza filtro ritorna tutti i nodi di primo livello."""
        bag = Bag({"a": 1, "b": 2})
        nodes = bag.get_nodes()
        assert len(nodes) == 2
        assert all(isinstance(n, BagNode) for n in nodes)
        assert [n.label for n in nodes] == ["a", "b"]

    def test_filter_by_condition(self):
        """get_nodes(condition=...) applica un filtro callable sui nodi."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        nodes = bag.get_nodes(condition=lambda n: n.value > 1)
        assert [n.label for n in nodes] == ["b", "c"]


# =============================================================================
# 7. get_node_by_attr() - depth-first con priorita' di livello
# =============================================================================


class TestGetNodeByAttr:
    def test_finds_first_level_by_attribute(self):
        """Trova un nodo di primo livello per attr=value."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"id": "target"})
        bag.set_item("b", 2, _attributes={"id": "other"})
        node = bag.get_node_by_attr("id", "target")
        assert isinstance(node, BagNode)
        assert node.label == "a"

    def test_returns_none_if_not_found(self):
        """Ritorna None se nessun nodo matcha."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"id": "x"})
        assert bag.get_node_by_attr("id", "missing") is None

    def test_level_priority_over_depth(self):
        """Un match a livello corrente batte un match piu' profondo."""
        bag = Bag()
        bag.set_item("outer.inner", 1, _attributes={"id": "T"})
        # 'top' e' un nodo di primo livello con id=T -> deve vincere
        bag.set_item("top", 2, _attributes={"id": "T"})
        node = bag.get_node_by_attr("id", "T")
        assert isinstance(node, BagNode)
        assert node.label == "top"

    def test_descends_into_subbags(self):
        """Cerca anche dentro sub-Bag se non trova al livello corrente."""
        bag = Bag()
        bag.set_item("nest.target", 42, _attributes={"id": "X"})
        node = bag.get_node_by_attr("id", "X")
        assert isinstance(node, BagNode)
        assert node.label == "target"
        assert node.value == 42


# =============================================================================
# 8. get_node_by_value() - primo livello, non ricorsivo
# =============================================================================


class TestGetNodeByValue:
    def test_finds_node_whose_value_contains_key(self):
        """Trova un nodo la cui value (Bag/dict) ha key=value."""
        outer = Bag()
        outer["row1.name"] = "alice"
        outer["row2.name"] = "bob"
        node = outer.get_node_by_value("name", "bob")
        assert isinstance(node, BagNode)
        assert node.label == "row2"

    def test_returns_none_if_no_match(self):
        """Ritorna None se nessuna sub-Bag contiene la coppia."""
        outer = Bag()
        outer["row1.name"] = "alice"
        assert outer.get_node_by_value("name", "charlie") is None


# =============================================================================
# 9. walk() - generator mode (path, node)
# =============================================================================


class TestWalkGenerator:
    def test_empty_bag_yields_nothing(self):
        """walk() su Bag vuoto non produce nulla."""
        assert list(Bag().walk()) == []

    def test_flat_bag_yields_each_node(self):
        """walk() su Bag flat yield una tupla per nodo."""
        bag = Bag({"a": 1, "b": 2})
        result = list(bag.walk())
        paths = [p for p, _n in result]
        assert paths == ["a", "b"]
        assert all(isinstance(n, BagNode) for _p, n in result)

    def test_deep_tree_yields_depth_first_paths(self):
        """walk() attraversa depth-first con path puntati."""
        bag = Bag()
        bag["a.x"] = 1
        bag["a.y"] = 2
        bag["b"] = 3
        paths = [p for p, _n in bag.walk()]
        # depth-first: 'a', 'a.x', 'a.y', 'b'
        assert paths == ["a", "a.x", "a.y", "b"]


# =============================================================================
# 10. walk() - legacy callback mode
# =============================================================================


class TestWalkCallback:
    def test_callback_invoked_per_node(self):
        """walk(callback) chiama callback per ogni nodo visitato."""
        bag = Bag({"a": 1, "b": 2})
        visited = []
        bag.walk(lambda n: visited.append(n.label))
        assert visited == ["a", "b"]

    def test_callback_truthy_return_exits_early(self):
        """Se il callback ritorna truthy, walk termina restituendo quel valore."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        result = bag.walk(lambda n: n.value if n.value == 2 else None)
        assert result == 2

    def test_callback_with_pathlist_tracks_path(self):
        """Con _pathlist=[] il callback riceve il path corrente come lista."""
        bag = Bag()
        bag["outer.inner"] = 42
        captured = []

        def cb(node, _pathlist=None, **kw):
            captured.append(list(_pathlist))

        bag.walk(cb, _pathlist=[])
        # primo nodo 'outer' ha path ['outer'], secondo 'inner' ha ['outer', 'inner']
        assert captured == [["outer"], ["outer", "inner"]]


# =============================================================================
# 11. query()
# =============================================================================


class TestQuery:
    def test_default_what_returns_tuples_k_v_a(self):
        """query() default = '#k,#v,#a': (label, value, attr)."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"x": 10})
        bag.set_item("b", 2, _attributes={"x": 20})
        result = bag.query()
        assert result == [("a", 1, {"x": 10}), ("b", 2, {"x": 20})]

    def test_query_labels_only(self):
        """query('#k') ritorna solo le label."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.query("#k") == ["a", "b"]

    def test_query_values_only(self):
        """query('#v') ritorna solo i valori."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.query("#v") == [1, 2]

    def test_query_attribute_only(self):
        """query('#a.type') ritorna il valore dell'attributo 'type' per ogni nodo."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"type": "int"})
        bag.set_item("b", 2, _attributes={"type": "str"})
        assert bag.query("#a.type") == ["int", "str"]

    def test_query_deep_paths(self):
        """query('#p', deep=True) ritorna tutti i path in modalita' ricorsiva."""
        bag = Bag()
        bag["a.b"] = 1
        bag["a.c"] = 2
        bag["d"] = 3
        result = bag.query("#p", deep=True)
        assert result == ["a", "a.b", "a.c", "d"]

    def test_query_leaves_only(self):
        """query(deep=True, branch=False) esclude i nodi branch."""
        bag = Bag()
        bag["a.b"] = 1
        bag["a.c"] = 2
        bag["d"] = 3
        result = bag.query("#p", deep=True, branch=False)
        # 'a' e' branch ed e' escluso
        assert result == ["a.b", "a.c", "d"]

    def test_query_branches_only(self):
        """query(deep=True, leaf=False) esclude i nodi leaf."""
        bag = Bag()
        bag["a.b"] = 1
        bag["c"] = 2
        result = bag.query("#p", deep=True, leaf=False)
        assert result == ["a"]

    def test_query_with_condition(self):
        """query(condition=...) filtra i nodi."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        result = bag.query("#k", condition=lambda n: n.value > 1)
        assert result == ["b", "c"]

    def test_query_limit(self):
        """query(limit=N) tronca il risultato a N elementi."""
        bag = Bag({"a": 1, "b": 2, "c": 3, "d": 4})
        assert bag.query("#k", limit=2) == ["a", "b"]

    def test_query_iter_returns_generator(self):
        """query(iter=True) ritorna un generatore, non una lista."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.query("#k", iter=True)
        assert not isinstance(result, list)
        assert list(result) == ["a", "b"]

    def test_query_callable_what(self):
        """query(what=[callable]) applica il callable a ogni nodo."""
        bag = Bag({"a": 1, "b": 2})
        result = bag.query([lambda n: n.label.upper()])
        assert result == ["A", "B"]

    def test_query_node_node(self):
        """query('#n') ritorna i BagNode stessi."""
        bag = Bag({"a": 1})
        result = bag.query("#n")
        assert len(result) == 1
        assert isinstance(result[0], BagNode)
        assert result[0].label == "a"

    def test_query_static_value(self):
        """query('#__v') ritorna lo static_value (mai triggera resolver)."""
        bag = Bag({"a": 1})
        assert bag.query("#__v") == [1]


# =============================================================================
# 12. digest() - alias retrocompat + as_columns
# =============================================================================


class TestDigest:
    def test_digest_default_matches_query_default(self):
        """digest() senza args equivale a query() non-deep non-iter."""
        bag = Bag({"a": 1, "b": 2})
        assert bag.digest() == bag.query()

    def test_digest_as_columns_transposes(self):
        """digest(as_columns=True) trasforma in colonne (list of lists)."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"x": 10})
        bag.set_item("b", 2, _attributes={"x": 20})
        result = bag.digest("#k,#v", as_columns=True)
        assert result == [["a", "b"], [1, 2]]

    def test_digest_as_columns_on_empty_bag(self):
        """digest(as_columns=True) su Bag vuoto ritorna liste vuote per ogni col."""
        result = Bag().digest("#k,#v", as_columns=True)
        assert result == [[], []]


# =============================================================================
# 13. columns() - wrapper su digest
# =============================================================================


class TestColumns:
    def test_columns_from_string(self):
        """columns('a,b') ritorna le colonne per i campi 'a' e 'b'."""
        bag = Bag()
        bag["row1.name"] = "alice"
        bag["row1.age"] = 30
        bag["row2.name"] = "bob"
        bag["row2.age"] = 25
        result = bag.columns("name,age")
        assert result == [["alice", "bob"], [30, 25]]

    def test_columns_attr_mode(self):
        """columns(cols, attr_mode=True) legge dagli attributi."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"price": 10, "qty": 2})
        bag.set_item("b", 2, _attributes={"price": 20, "qty": 3})
        result = bag.columns("price,qty", attr_mode=True)
        assert result == [[10, 20], [2, 3]]


# =============================================================================
# 14. sum()
# =============================================================================


class TestSum:
    def test_sum_values_default(self):
        """sum() senza args somma i valori di primo livello."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        assert bag.sum() == 6

    def test_sum_none_values_are_zero(self):
        """Valori None sono trattati come 0 dalla somma."""
        bag = Bag({"a": 1, "b": None, "c": 2})
        assert bag.sum() == 3

    def test_sum_attribute(self):
        """sum('#a.price') somma l'attributo 'price' di ogni nodo."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"price": 10})
        bag.set_item("b", 2, _attributes={"price": 20})
        assert bag.sum("#a.price") == 30

    def test_sum_multiple_returns_list(self):
        """sum('#v,#a.qty') ritorna [sum_values, sum_qty]."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"qty": 5})
        bag.set_item("b", 2, _attributes={"qty": 7})
        assert bag.sum("#v,#a.qty") == [3, 12]

    def test_sum_with_condition(self):
        """sum con condition filtra prima di sommare."""
        bag = Bag({"a": 1, "b": 2, "c": 3})
        total = bag.sum("#v", condition=lambda n: n.value > 1)
        assert total == 5

    def test_sum_deep(self):
        """sum('#a.qty', deep=True) somma ricorsivamente su sub-Bag."""
        bag = Bag()
        bag.set_item("outer.a", 0, _attributes={"qty": 10})
        bag.set_item("outer.b", 0, _attributes={"qty": 20})
        bag.set_item("c", 0, _attributes={"qty": 5})
        assert bag.sum("#a.qty", deep=True) == 35


# =============================================================================
# 15. sort() - validato tramite keys()/values()
# =============================================================================


class TestSort:
    def test_sort_by_label_ascending_default(self):
        """sort('#k') ordina per label ascendente (default)."""
        bag = Bag()
        bag["c"] = 1
        bag["a"] = 2
        bag["b"] = 3
        bag.sort("#k")
        assert bag.keys() == ["a", "b", "c"]

    def test_sort_by_label_descending(self):
        """sort('#k:d') ordina per label discendente."""
        bag = Bag()
        bag["a"] = 1
        bag["c"] = 2
        bag["b"] = 3
        bag.sort("#k:d")
        assert bag.keys() == ["c", "b", "a"]

    def test_sort_by_value_ascending(self):
        """sort('#v') ordina per valore."""
        bag = Bag()
        bag["a"] = 3
        bag["b"] = 1
        bag["c"] = 2
        bag.sort("#v")
        assert bag.values() == [1, 2, 3]

    def test_sort_by_value_descending(self):
        """sort('#v:d') ordina per valore discendente."""
        bag = Bag({"a": 1, "b": 3, "c": 2})
        bag.sort("#v:d")
        assert bag.values() == [3, 2, 1]

    def test_sort_by_attribute(self):
        """sort('#a.name') ordina per attributo 'name'."""
        bag = Bag()
        bag.set_item("a", 1, _attributes={"name": "charlie"})
        bag.set_item("b", 2, _attributes={"name": "alice"})
        bag.set_item("c", 3, _attributes={"name": "bob"})
        bag.sort("#a.name")
        assert bag.keys() == ["b", "c", "a"]

    def test_sort_by_callable(self):
        """sort(callable) usa il callable come key function."""
        bag = Bag({"a": 3, "b": 1, "c": 2})
        bag.sort(lambda n: n.value)
        assert bag.values() == [1, 2, 3]

    def test_sort_returns_self(self):
        """sort ritorna self per chaining."""
        bag = Bag({"a": 1})
        assert bag.sort("#k") is bag

    def test_multi_level_sort(self):
        """sort('#a.g:a,#v:d' applica sort multi-livello."""
        bag = Bag()
        # stesso gruppo 'g=A', valori diversi -> devono ordinarsi per valore desc
        bag.set_item("n1", 1, _attributes={"g": "A"})
        bag.set_item("n2", 3, _attributes={"g": "A"})
        bag.set_item("n3", 2, _attributes={"g": "B"})
        bag.sort("#a.g:a,#v:d")
        # dentro 'A' discendente per valore -> n2(3), n1(1); poi gruppo 'B' -> n3(2)
        assert bag.keys() == ["n2", "n1", "n3"]
