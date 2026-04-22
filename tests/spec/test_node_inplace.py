"""Spec test: BagNode - API pubblica dei nodi in place.

Dipende da test_basic.py (set_item, get_item, get_node, ecc.).

## Principio

Un BagNode NON si istanzia da solo nei test (da solo non ha senso:
serve una Bag che lo contenga). Lo si OTTIENE sempre tramite la Bag:

    node = bag.set_item(path, value, ...)       # ritorno
    node = bag.get_node(path)                   # lookup
    node = bag.pop_node(path)                   # rimozione
    node = bag.node(label)                      # accesso diretto

Una volta in place, i metodi pubblici (no underscore) del BagNode
sono API pubblica e vanno esercitati.

## Scala

1.  Identita' del nodo                          label / __str__ / __repr__ / __eq__
2.  value / value setter / get_value
3.  static_value                                valore cached senza trigger
4.  attr property / set_attr / get_attr / del_attr / has_attr
5.  is_branch                                   valore Bag vs scalare
6.  is_valid                                    default True (senza invalid_reasons)
7.  position                                    indice nel container parent
8.  parent_bag / parent_node                    navigazione
9.  fullpath (con backref)                      path puntato al nodo
10. get_inherited_attributes                    merge lungo catena parent
11. attribute_owner_node                        ricerca ascendente per attributo
12. diff                                        confronto label/attr/value
13. as_tuple                                    (label, value, attr, resolver)
14. to_json                                     dict serializzabile
15. subscribe / unsubscribe                     notifiche node-level
16. reset_resolver                              rimuove il resolver
17. compiled                                    dict esterno compilato (inizializzato lazy)
18. orphaned                                    detach recursive dal parent
19. property _ (underscore)                     ritorna parent_bag o solleva
20. xml_tag                                     preservato da parsing XML
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagNode


# =============================================================================
# 1. Identita' del nodo
# =============================================================================


class TestNodeIdentity:
    def test_label_attribute(self):
        """node.label espone il label usato per l'inserimento."""
        bag = Bag()
        node = bag.set_item("foo", 1)
        assert node.label == "foo"

    def test_str_contains_label(self):
        """str(node) include il label."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert "x" in str(node)

    def test_repr_contains_label_and_id(self):
        """repr(node) include label e id dell'oggetto."""
        bag = Bag()
        node = bag.set_item("x", 1)
        r = repr(node)
        assert "x" in r
        assert str(id(node)) in r

    def test_equal_nodes_have_same_label_attr_value(self):
        """Due nodi con stessi label, attr, value sono uguali (via __eq__)."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v"})
        n2 = b.set_item("x", 1, _attributes={"k": "v"})
        assert n1 == n2

    def test_different_value_not_equal(self):
        """Nodi con valori diversi non sono uguali."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("x", 2)
        assert n1 != n2

    def test_different_label_not_equal(self):
        """Nodi con label diversi non sono uguali."""
        bag = Bag()
        n1 = bag.set_item("x", 1)
        n2 = bag.set_item("y", 1)
        assert n1 != n2

    def test_ne_with_non_bagnode(self):
        """__eq__ con oggetto non-BagNode ritorna False."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node != "not a node"
        assert node != 42


# =============================================================================
# 2. value / value setter / get_value
# =============================================================================


class TestNodeValue:
    def test_value_property_reads_value(self):
        """node.value legge il valore del nodo."""
        bag = Bag()
        node = bag.set_item("x", 42)
        assert node.value == 42

    def test_value_setter_updates_value(self):
        """node.value = X aggiorna il valore, visibile anche da bag[x]."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.value = 99
        assert bag.get_item("x") == 99

    def test_get_value_static_true_reads_static(self):
        """get_value(static=True) ritorna il valore cached senza trigger."""
        bag = Bag()
        node = bag.set_item("x", 7)
        assert node.get_value(static=True) == 7


# =============================================================================
# 3. static_value
# =============================================================================


class TestStaticValue:
    def test_static_value_property(self):
        """static_value espone il valore cached senza triggerare il resolver."""
        bag = Bag()
        node = bag.set_item("x", 10)
        assert node.static_value == 10

    def test_static_value_on_node_with_resolver_before_load(self):
        """static_value su nodo con resolver prima di una lettura e' None."""
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        # mai letto -> static_value None
        assert node.static_value is None


# =============================================================================
# 4. attr / set_attr / get_attr / del_attr / has_attr
# =============================================================================


class TestNodeAttr:
    def test_attr_property_returns_dict(self):
        """node.attr ritorna il dict degli attributi."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.attr == {"k": "v"}

    def test_set_attr_via_kwargs(self):
        """node.set_attr(k=v) aggiunge l'attributo."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.set_attr(k="v")
        assert node.get_attr("k") == "v"

    def test_set_attr_via_dict(self):
        """node.set_attr(attr={...}) accetta un dict."""
        bag = Bag()
        node = bag.set_item("x", 1)
        node.set_attr(attr={"a": 1, "b": 2})
        assert node.get_attr("a") == 1
        assert node.get_attr("b") == 2

    def test_get_attr_single(self):
        """get_attr(label) ritorna un attributo specifico."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.get_attr("k") == "v"

    def test_get_attr_missing_returns_default(self):
        """get_attr(missing, default=X) ritorna X."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.get_attr("nope", default="fallback") == "fallback"

    def test_get_attr_no_label_returns_all(self):
        """get_attr() senza label ritorna tutti gli attributi."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        result = node.get_attr()
        assert result == {"a": 1, "b": 2}

    def test_del_attr_removes_key(self):
        """del_attr(key) rimuove un attributo."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        node.del_attr("a")
        assert not node.has_attr("a")
        assert node.has_attr("b")

    def test_del_attr_comma_separated(self):
        """del_attr('a,b') rimuove piu' attributi da stringa comma-separated."""
        bag = Bag()
        node = bag.set_item(
            "x", 1, _attributes={"a": 1, "b": 2, "c": 3}
        )
        node.del_attr("a,b")
        assert not node.has_attr("a")
        assert not node.has_attr("b")
        assert node.has_attr("c")

    def test_has_attr_without_value(self):
        """has_attr(key) ritorna True se l'attributo esiste."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"k": "v"})
        assert node.has_attr("k") is True
        assert node.has_attr("missing") is False

    def test_has_attr_with_value_match(self):
        """has_attr(key, value) ritorna True solo se match."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"kind": "int"})
        assert node.has_attr("kind", "int") is True
        assert node.has_attr("kind", "str") is False


# =============================================================================
# 5. is_branch
# =============================================================================


class TestIsBranch:
    def test_is_branch_true_for_bag_value(self):
        """Nodo con valore Bag ha is_branch=True."""
        bag = Bag()
        bag["outer.inner"] = 1  # crea sub-bag 'outer'
        outer = bag.get_node("outer")
        assert isinstance(outer, BagNode)
        assert outer.is_branch is True

    def test_is_branch_false_for_scalar(self):
        """Nodo con valore scalare ha is_branch=False."""
        bag = Bag()
        node = bag.set_item("x", 42)
        assert node.is_branch is False


# =============================================================================
# 6. is_valid
# =============================================================================


class TestIsValid:
    def test_fresh_node_is_valid(self):
        """Un nodo appena creato ha is_valid=True (nessun errore)."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.is_valid is True


# =============================================================================
# 7. position
# =============================================================================


class TestPosition:
    def test_position_returns_index(self):
        """position ritorna l'indice 0-based nel parent."""
        bag = Bag()
        n0 = bag.set_item("a", 1)
        n1 = bag.set_item("b", 2)
        n2 = bag.set_item("c", 3)
        assert n0.position == 0
        assert n1.position == 1
        assert n2.position == 2

    def test_position_reflects_reordering(self):
        """Dopo un riordino, position riflette la nuova posizione."""
        bag = Bag()
        bag.set_item("a", 1)
        bag.set_item("b", 2)
        n = bag.set_item("c", 3, node_position="<")
        assert n.position == 0

    def test_position_negative_on_popped_node(self):
        """Un nodo estratto con pop_node non e' piu' nel container: position -1.

        pop_node non chiama orphaned(), quindi parent_bag resta referenziato
        ma il nodo non e' piu' indicizzabile nel container (label assente).
        """
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        assert node.position == -1


# =============================================================================
# 8. parent_bag / parent_node
# =============================================================================


class TestParentLinks:
    def test_parent_bag_returns_containing_bag(self):
        """node.parent_bag e' la Bag che contiene il nodo."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.parent_bag is bag

    def test_parent_bag_none_after_orphaned_call(self):
        """orphaned() azzera parent_bag; pop_node da solo no."""
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        # pop_node non chiama orphaned: parent_bag resta
        assert node.parent_bag is bag
        # orphaned() azzera il riferimento
        node.orphaned()
        assert node.parent_bag is None

    def test_parent_node_with_backref(self):
        """Con backref, il nodo dentro una sub-Bag vede il parent_node."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)  # abilita backref
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.parent_node is not None
        assert inner.parent_node.label == "outer"

    def test_parent_node_none_for_top_level(self):
        """Un nodo top-level non ha parent_node."""
        root = Bag()
        root.set_backref()
        node = root.set_item("x", 1)
        assert node.parent_node is None


# =============================================================================
# 9. fullpath (con backref)
# =============================================================================


class TestNodeFullpath:
    def test_fullpath_none_without_backref(self):
        """Senza backref, fullpath del nodo e' None (top-level non annidato)."""
        bag = Bag()
        node = bag.set_item("x", 1)
        # il parent_bag e' root, fullpath del bag e' None -> nodo none
        assert node.fullpath is None

    def test_fullpath_reports_path_with_backref(self):
        """Con backref, il nodo annidato ha fullpath dot-separated dalla root."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)  # abilita backref
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.fullpath == "outer.inner"


# =============================================================================
# 10. get_inherited_attributes
# =============================================================================


class TestInheritedAttributes:
    def test_inherited_merges_ancestors_attributes(self):
        """inherited ritorna attributi mergiati dalla catena parent (con backref)."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        # attributo sul nodo outer (container)
        root.set_attr("outer", env="prod")
        # attributo sul nodo inner (foglia)
        root.set_attr("outer.inner", role="worker")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        inherited = inner.get_inherited_attributes()
        assert inherited.get("env") == "prod"
        assert inherited.get("role") == "worker"

    def test_inherited_own_overrides_ancestor(self):
        """Se il nodo ha un attributo gia' presente nell'antenato, vince il nodo."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", k="from_outer")
        root.set_attr("outer.inner", k="from_inner")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.get_inherited_attributes()["k"] == "from_inner"


# =============================================================================
# 11. attribute_owner_node
# =============================================================================


class TestAttributeOwnerNode:
    def test_finds_ancestor_with_attribute(self):
        """attribute_owner_node trova l'ascendente che possiede l'attributo."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", kind="section")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        owner = inner.attribute_owner_node("kind")
        assert isinstance(owner, BagNode)
        assert owner.label == "outer"

    def test_finds_ancestor_with_attr_value_match(self):
        """attribute_owner_node con value fa match su (key, value)."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        root.set_attr("outer", role="admin")
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        owner = inner.attribute_owner_node("role", "admin")
        assert isinstance(owner, BagNode)
        assert owner.label == "outer"

    def test_returns_none_when_not_found(self):
        """attribute_owner_node ritorna None se l'attributo non esiste."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        inner = root.get_node("outer.inner")
        assert isinstance(inner, BagNode)
        assert inner.attribute_owner_node("nonexistent") is None


# =============================================================================
# 12. diff
# =============================================================================


class TestDiff:
    def test_diff_none_when_equal(self):
        """diff ritorna None se i nodi sono equivalenti."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v"})
        n2 = b.set_item("x", 1, _attributes={"k": "v"})
        assert n1.diff(n2) is None

    def test_diff_reports_label_difference(self):
        """diff segnala label diverso."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("y", 1)
        result = n1.diff(n2)
        assert result is not None
        assert "label" in result.lower()

    def test_diff_reports_value_difference(self):
        """diff segnala value diverso."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1)
        n2 = b.set_item("x", 2)
        result = n1.diff(n2)
        assert result is not None
        assert "value" in result.lower()

    def test_diff_reports_attr_difference(self):
        """diff segnala attr diversi."""
        a = Bag()
        b = Bag()
        n1 = a.set_item("x", 1, _attributes={"k": "v1"})
        n2 = b.set_item("x", 1, _attributes={"k": "v2"})
        result = n1.diff(n2)
        assert result is not None
        assert "attr" in result.lower()


# =============================================================================
# 13. as_tuple
# =============================================================================


class TestAsTuple:
    def test_returns_label_value_attr_resolver(self):
        """as_tuple ritorna (label, value, attr, resolver)."""
        bag = Bag()
        node = bag.set_item("x", 42, _attributes={"k": "v"})
        label, value, attr, resolver = node.as_tuple()
        assert label == "x"
        assert value == 42
        assert attr == {"k": "v"}
        assert resolver is None

    def test_tuple_has_resolver_when_set(self):
        """Se il nodo ha un resolver, compare nella tupla."""
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        _, _, _, resolver = node.as_tuple()
        assert isinstance(resolver, UuidResolver)


# =============================================================================
# 14. to_json
# =============================================================================


class TestNodeToJson:
    def test_returns_dict_with_label_value_attr(self):
        """to_json ritorna dict con chiavi 'label', 'value', 'attr'."""
        bag = Bag()
        node = bag.set_item("x", 42, _attributes={"k": "v"})
        data = node.to_json()
        assert data["label"] == "x"
        assert data["value"] == 42
        assert data["attr"] == {"k": "v"}


# =============================================================================
# 15. subscribe / unsubscribe (node-level)
# =============================================================================


class TestNodeSubscription:
    def test_node_subscribe_receives_update_notifications(self):
        """node.subscribe registra un callback invocato su cambio valore."""
        events: list = []
        bag = Bag()
        node = bag.set_item("x", 1)
        node.subscribe("s1", lambda **kw: events.append(kw))
        bag["x"] = 2

        assert len(events) == 1
        assert events[0]["evt"] == "upd_value"

    def test_node_unsubscribe_stops_notifications(self):
        """Dopo unsubscribe non arrivano piu' eventi node-level."""
        events: list = []
        bag = Bag()
        node = bag.set_item("x", 1)
        node.subscribe("s1", lambda **kw: events.append(kw))
        node.unsubscribe("s1")
        bag["x"] = 2

        assert events == []


# =============================================================================
# 16. reset_resolver
# =============================================================================


class TestResetResolver:
    def test_reset_resolver_clears_value_and_invalidates_cache(self):
        """reset_resolver() invalida la cache e azzera il valore corrente.

        Non rimuove il resolver: il nome si riferisce a "reset del resolver",
        cioe' reset dello stato cached, non all'eliminazione dell'oggetto.
        """
        from genro_bag.resolvers import UuidResolver

        bag = Bag()
        bag["id"] = UuidResolver()
        first = bag["id"]  # triggera load -> UUID generato e cached
        node = bag.get_node("id")
        assert isinstance(node, BagNode)
        assert node.resolver is not None
        node.reset_resolver()
        # il resolver resta, ma la cache e' invalidata: ri-accedere genera
        # un NUOVO uuid (cache_time=False -> non si ricarica finche' non e' azzerata)
        second = bag["id"]
        assert node.resolver is not None
        assert first != second


# =============================================================================
# 17. compiled (lazy)
# =============================================================================


class TestCompiled:
    def test_compiled_returns_dict_lazy_init(self):
        """compiled espone un dict per dati esterni, inizializzato al primo accesso."""
        bag = Bag()
        node = bag.set_item("x", 1)
        c = node.compiled
        assert isinstance(c, dict)

    def test_compiled_same_instance_across_calls(self):
        """Due letture di compiled restituiscono lo stesso dict (stesso oggetto)."""
        bag = Bag()
        node = bag.set_item("x", 1)
        c1 = node.compiled
        c2 = node.compiled
        assert c1 is c2


# =============================================================================
# 18. orphaned
# =============================================================================


class TestOrphaned:
    def test_orphaned_clears_parent_bag(self):
        """orphaned() azzera parent_bag sul nodo e ritorna self per chaining."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.parent_bag is bag
        result = node.orphaned()
        assert result is node
        assert node.parent_bag is None


# =============================================================================
# 19. _ property (underscore) - parent_bag getter con raise
# =============================================================================


class TestUnderscoreProperty:
    def test_returns_parent_bag(self):
        """node._ ritorna la parent Bag quando il nodo e' attached."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node._ is bag

    def test_raises_when_no_parent(self):
        """node._ su nodo senza parent_bag solleva ValueError.

        Per avere un nodo veramente orfano serve pop_node seguito da
        orphaned() (pop_node da solo preserva parent_bag).
        """
        bag = Bag()
        bag.set_item("x", 1)
        node = bag.pop_node("x")
        assert isinstance(node, BagNode)
        node.orphaned()
        with pytest.raises(ValueError):
            _ = node._


# =============================================================================
# 20. xml_tag
# =============================================================================


class TestXmlTag:
    def test_xml_tag_preserved_from_parsing(self):
        """Dopo parse XML, node.xml_tag preserva il tag originale dell'elemento."""
        bag = Bag.from_xml("<root><item>v</item></root>")
        node = bag.get_node("root.item")
        assert isinstance(node, BagNode)
        assert node.xml_tag == "item"

    def test_xml_tag_none_when_not_from_parsing(self):
        """Un nodo creato via set_item non ha xml_tag."""
        bag = Bag()
        node = bag.set_item("x", 1)
        assert node.xml_tag is None


# =============================================================================
# 21. set_value con _attributes: evento 'upd_value_attr' sul parent
# =============================================================================


class TestSetValueWithAttributes:
    def test_set_value_with_attributes_fires_upd_value_attr_on_parent(self):
        """set_value(v, _attributes={...}) con backref emette 'upd_value_attr'."""
        events: list[str] = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_value(99, _attributes={"kind": "int"})

        assert "upd_value_attr" in events
        # il valore e l'attributo sono entrambi aggiornati
        assert bag.get_item("x") == 99
        assert bag.get_attr("x", "kind") == "int"

    def test_set_value_with_updattr_false_replaces_attributes(self):
        """set_value(v, _attributes={...}, _updattr=False) sostituisce gli attr."""
        bag = Bag()
        node = bag.set_item("x", 1, _attributes={"a": 1, "b": 2})
        # _updattr=False: sostituzione completa, non merge
        node.set_value(99, _attributes={"c": 3}, _updattr=False)

        # gli attributi vecchi sono spariti
        assert not node.has_attr("a")
        assert not node.has_attr("b")
        # solo il nuovo attributo resta
        assert node.get_attr("c") == 3

    def test_set_value_does_not_fire_when_unchanged(self):
        """set_value con lo stesso valore e stessi attr non emette evento."""
        events: list[str] = []
        bag = Bag()
        bag.set_item("x", 1, _attributes={"k": "v"})
        bag.subscribe("w", update=lambda **kw: events.append(kw["evt"]))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        # stesso valore, stessi attr -> nessun cambio
        node.set_value(1, _attributes={"k": "v"})
        assert events == []

    def test_set_value_trigger_false_suppresses_events(self):
        """set_value(v, trigger=False) non notifica i subscribers."""
        events: list = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_value(42, trigger=False)

        assert events == []
        # ma il valore e' cambiato
        assert bag.get_item("x") == 42


# =============================================================================
# 22. set_value con BagNode come value: estrae valore e merge attr
# =============================================================================


class TestSetValueWithBagNode:
    def test_set_value_with_bagnode_extracts_value_and_replaces_attrs(self):
        """set_value(other_node) estrae value e rimpiazza gli attr con quelli di other.

        Con _updattr non specificato (default None in set_value), set_attr
        va in modalita' replace: gli attr preesistenti vengono sostituiti
        da quelli dell'altro nodo.
        """
        src = Bag()
        other = src.set_item("src", 42, _attributes={"origin": "lab"})

        dst = Bag()
        node = dst.set_item("x", 0, _attributes={"target": "prod"})
        node.set_value(other)

        # il valore di 'x' diventa 42 (estratto da other)
        assert dst.get_item("x") == 42
        # attr di other presenti
        assert dst.get_attr("x", "origin") == "lab"
        # attr preesistente 'target' sostituito (replace mode)
        assert dst.get_attr("x", "target") is None


# =============================================================================
# 23. set_attr senza trigger
# =============================================================================


class TestSetAttrTriggerFalse:
    def test_set_attr_trigger_false_does_not_notify(self):
        """node.set_attr(trigger=False) aggiorna gli attr ma non notifica."""
        events: list = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("w", update=lambda **kw: events.append(kw))

        node = bag.get_node("x")
        assert isinstance(node, BagNode)
        node.set_attr(trigger=False, k="v")

        assert events == []
        assert node.get_attr("k") == "v"
