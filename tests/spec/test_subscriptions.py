"""Spec test: Bag - subscriptions (osservabilita' degli eventi, sync).

Dipende da test_basic.py (set_item, get_item, pop, __delitem__) e da
test_population.py (fill_from).

Le subscriptions sono il contratto observer di Bag: registri un callback
con un id, la Bag notifica quando avvengono update/insert/delete. Nel
contesto sync testiamo:

- le notifiche granulari (update, insert, delete, any)
- la propagazione degli eventi lungo la catena parent (backref)
- il blocco della propagazione (callback che ritorna False)
- transaction() come meccanismo di coalescenza

Timer e reset(refresh=True) richiedono un event loop -> test_async_reactive.

## Scala

1.  subscribe(update=...)               notifica su cambio valore
2.  subscribe(insert=...)               notifica su nuovo nodo
3.  subscribe(delete=...)               notifica su rimozione
4.  subscribe(any=...)                  un callback per tutti
5.  subscribe attiva automaticamente backref
6.  subscribe senza callback            noop
7.  unsubscribe selettivo               update / insert / delete separati
8.  unsubscribe(any=True)               rimuove upd/ins/del ma NON transaction
9.  callback riceve argomenti documentati
10. propagazione lungo parent chain
11. callback ritorna False              stop propagazione
12. transaction()                       mutations coalesced
13. transaction()                       subscribers granulari silenziati
14. transaction() con exception         nessun evento transaction
15. transaction() annidate              liste isolate per scope
16. set_backref manuale                 fullpath diventa non-None
17. subscribe(timer=...) senza interval ValueError
"""

from __future__ import annotations

import pytest

from genro_bag import Bag, BagNode


# =============================================================================
# 1. subscribe(update=...)
# =============================================================================


class TestUpdateSubscription:
    def test_update_callback_fires_on_value_change(self):
        """Modificare il valore di un nodo esistente triggera il callback update."""
        events = []
        bag = Bag()
        bag["a"] = 1
        bag.subscribe("s1", update=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 2
        assert events == ["upd_value"]

    def test_update_not_fired_on_insert(self):
        """Un insert non triggera il callback update."""
        events = []
        bag = Bag()
        bag.subscribe("s1", update=lambda **kw: events.append(kw["evt"]))
        bag["new"] = 1
        assert events == []


# =============================================================================
# 2. subscribe(insert=...)
# =============================================================================


class TestInsertSubscription:
    def test_insert_callback_fires_on_new_node(self):
        """Assegnare un path nuovo triggera il callback insert."""
        events = []
        bag = Bag()
        bag.subscribe("s1", insert=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 1
        assert events == ["ins"]

    def test_insert_not_fired_on_update(self):
        """Modificare un nodo esistente non triggera insert."""
        events = []
        bag = Bag()
        bag["a"] = 1
        bag.subscribe("s1", insert=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 2
        assert events == []


# =============================================================================
# 3. subscribe(delete=...)
# =============================================================================


class TestDeleteSubscription:
    def test_delete_callback_fires_on_pop(self):
        """pop/del triggerano il callback delete."""
        events = []
        bag = Bag()
        bag["a"] = 1
        bag.subscribe("s1", delete=lambda **kw: events.append(kw["evt"]))
        bag.pop("a")
        assert events == ["del"]

    def test_delete_callback_fires_on_del_item(self):
        """del bag[path] triggera il callback delete."""
        events = []
        bag = Bag()
        bag["a"] = 1
        bag.subscribe("s1", delete=lambda **kw: events.append(kw["evt"]))
        del bag["a"]
        assert events == ["del"]


# =============================================================================
# 4. subscribe(any=...)
# =============================================================================


class TestAnySubscription:
    def test_any_callback_fires_on_all_three(self):
        """any=... copre update + insert + delete (non timer/transaction)."""
        events = []
        bag = Bag()
        bag.subscribe("s1", any=lambda **kw: events.append(kw["evt"]))
        bag["a"] = 1         # ins
        bag["a"] = 2         # upd
        bag.pop("a")         # del
        assert events == ["ins", "upd_value", "del"]


# =============================================================================
# 5. subscribe abilita automaticamente backref
# =============================================================================


class TestSubscribeEnablesBackref:
    def test_subscribe_enables_backref(self):
        """subscribe attiva backref se non gia' attivo."""
        bag = Bag()
        assert bag.backref is False
        bag.subscribe("s1", update=lambda **kw: None)
        assert bag.backref is True


# =============================================================================
# 6. subscribe senza callback
# =============================================================================


class TestSubscribeNoCallback:
    def test_subscribe_without_callbacks_is_noop_but_enables_backref(self):
        """subscribe(id) senza callback non registra nulla ma abilita backref."""
        bag = Bag()
        bag.subscribe("s1")
        assert bag.backref is True
        # non ci sono callback: nessuna notifica da verificare, nessun errore
        bag["a"] = 1  # deve funzionare senza sollevare


# =============================================================================
# 7. unsubscribe selettivo
# =============================================================================


class TestUnsubscribeSelective:
    def test_unsubscribe_update_only(self):
        """unsubscribe(update=True) rimuove solo la callback update."""
        events: list[str] = []
        bag = Bag()
        bag.subscribe(
            "s1",
            update=lambda **kw: events.append("u"),
            insert=lambda **kw: events.append("i"),
        )
        bag.unsubscribe("s1", update=True)
        bag["a"] = 1  # insert -> 'i'
        bag["a"] = 2  # update -> non piu' registrato
        assert events == ["i"]

    def test_unsubscribe_insert_only_keeps_others(self):
        """unsubscribe(insert=True) preserva update e delete."""
        events: list[str] = []
        bag = Bag()
        bag.subscribe(
            "s1",
            insert=lambda **kw: events.append("i"),
            update=lambda **kw: events.append("u"),
            delete=lambda **kw: events.append("d"),
        )
        bag.unsubscribe("s1", insert=True)
        bag["a"] = 1     # insert -> non registrato
        bag["a"] = 2     # update
        bag.pop("a")     # delete
        assert events == ["u", "d"]


# =============================================================================
# 8. unsubscribe(any=True) NON tocca transaction
# =============================================================================


class TestUnsubscribeAny:
    def test_unsubscribe_any_removes_upd_ins_del_keeps_transaction(self):
        """any=True rimuove upd/ins/del/timer ma NON transaction."""
        events: list[str] = []
        bag = Bag()
        bag.subscribe(
            "s1",
            any=lambda **kw: events.append(kw["evt"]),
            transaction=lambda **kw: events.append("txn"),
        )
        bag.unsubscribe("s1", any=True)

        with bag.transaction():
            bag["a"] = 1
        # upd/ins/del sono stati rimossi; transaction ancora attivo
        assert events == ["txn"]

    def test_unsubscribe_transaction_only(self):
        """unsubscribe(transaction=True) rimuove solo transaction."""
        events: list[str] = []
        bag = Bag()
        bag.subscribe(
            "s1",
            any=lambda **kw: events.append(kw["evt"]),
            transaction=lambda **kw: events.append("txn"),
        )
        bag.unsubscribe("s1", transaction=True)
        with bag.transaction():
            bag["a"] = 1
        # transaction rimosso, ma granulari silenziati dentro with
        # -> nessun evento (il with consuma le mutations senza dispatcher)
        assert events == []


# =============================================================================
# 9. Callback riceve argomenti documentati
# =============================================================================


class TestCallbackArguments:
    def test_update_callback_receives_evt_node_pathlist_oldvalue(self):
        """Il callback update riceve evt, node, pathlist, oldvalue, reason."""
        captured: list[dict] = []
        bag = Bag()
        bag["a"] = "old"
        bag.subscribe("s1", update=lambda **kw: captured.append(kw))
        bag["a"] = "new"

        assert len(captured) == 1
        kw = captured[0]
        assert kw["evt"] == "upd_value"
        assert kw["node"].label == "a"
        assert kw["oldvalue"] == "old"
        assert "pathlist" in kw
        assert "reason" in kw

    def test_insert_callback_receives_evt_node_pathlist_ind(self):
        """Il callback insert riceve evt, node, pathlist, ind, reason."""
        captured: list[dict] = []
        bag = Bag()
        bag.subscribe("s1", insert=lambda **kw: captured.append(kw))
        bag["first"] = 1

        assert len(captured) == 1
        kw = captured[0]
        assert kw["evt"] == "ins"
        assert kw["node"].label == "first"
        assert kw["ind"] == 0
        assert "pathlist" in kw

    def test_delete_callback_receives_evt_node_pathlist_ind(self):
        """Il callback delete riceve evt, node, pathlist, ind, reason."""
        captured: list[dict] = []
        bag = Bag()
        bag["x"] = 1
        bag.subscribe("s1", delete=lambda **kw: captured.append(kw))
        bag.pop("x", _reason="cleanup")

        assert len(captured) == 1
        kw = captured[0]
        assert kw["evt"] == "del"
        assert kw["ind"] == 0
        assert kw["reason"] == "cleanup"


# =============================================================================
# 10. Propagazione eventi lungo la parent chain
# =============================================================================


class TestEventPropagation:
    def test_change_in_child_notifies_root(self):
        """Una modifica su un nodo di sub-Bag arriva al subscriber del root."""
        events: list = []
        root = Bag()
        root.subscribe("root_sub", update=lambda **kw: events.append(kw["pathlist"]))
        # creo sub-bag e la aggancio
        root["outer.inner"] = 1
        # modifica foglia profonda
        root["outer.inner"] = 2

        assert len(events) == 1
        # la pathlist contiene la sequenza dei label fino alla foglia modificata
        assert events[0] == ["outer", "inner"]

    def test_insert_in_child_notifies_root(self):
        """Un insert in sub-Bag propaga al root."""
        events: list = []
        root = Bag()
        root["outer.x"] = 1  # crea sub-bag 'outer'
        root.subscribe("root_sub", insert=lambda **kw: events.append(kw["node"].label))
        root["outer.y"] = 2

        assert "y" in events


# =============================================================================
# 11. Callback ritorna False -> stop propagazione
# =============================================================================


class TestPropagationStop:
    def test_false_stops_bubbling_to_parent(self):
        """Un callback che ritorna False blocca la propagazione al parent."""
        root_events: list = []
        child_events: list = []

        root = Bag()
        root["outer.x"] = 0
        child = root.get_item("outer")
        assert isinstance(child, Bag)

        # subscriber sul child che blocca; subscriber sul root che NON deve vedere
        child.subscribe(
            "child_sub",
            update=lambda **kw: (child_events.append(kw["evt"]), False)[1],
        )
        root.subscribe("root_sub", update=lambda **kw: root_events.append(kw["evt"]))

        root["outer.x"] = 1

        assert child_events == ["upd_value"]
        assert root_events == []  # bloccato


# =============================================================================
# 12-15. transaction()
# =============================================================================


class TestTransaction:
    def test_mutations_coalesced_into_single_event(self):
        """Mutazioni dentro un with transaction() arrivano in un unico evento."""
        received: list[list] = []
        bag = Bag()
        bag.subscribe("s1", transaction=lambda **kw: received.append(kw["mutations"]))

        with bag.transaction():
            bag["a"] = 1
            bag["b"] = 2
            bag["c"] = 3

        assert len(received) == 1
        mutations = received[0]
        assert len(mutations) == 3
        # ciascun item e' una tupla con il tipo di evento come primo elemento
        event_kinds = [m[0] for m in mutations]
        assert event_kinds == ["ins", "ins", "ins"]

    def test_granular_subscribers_silenced_inside_transaction(self):
        """Dentro un with, i callback granulari update/insert/delete non sono chiamati."""
        granular: list[str] = []
        txn_received: list = []
        bag = Bag()
        bag.subscribe(
            "s1",
            any=lambda **kw: granular.append(kw["evt"]),
            transaction=lambda **kw: txn_received.append(len(kw["mutations"])),
        )
        with bag.transaction():
            bag["a"] = 1
            bag["b"] = 2

        assert granular == []
        assert txn_received == [2]

    def test_exception_inside_with_suppresses_transaction_event(self):
        """Se il body del with solleva, nessun evento transaction viene emesso."""
        txn_received: list = []
        bag = Bag()
        bag.subscribe("s1", transaction=lambda **kw: txn_received.append(kw))

        with pytest.raises(RuntimeError):
            with bag.transaction():
                bag["a"] = 1
                raise RuntimeError("boom")

        assert txn_received == []
        # la mutazione gia' applicata resta (no rollback documentato)
        assert bag.get_item("a") == 1

    def test_nested_transactions_emit_separate_events(self):
        """Ogni with innestato emette il proprio evento transaction."""
        received: list[list] = []
        bag = Bag()
        bag.subscribe("s1", transaction=lambda **kw: received.append(kw["mutations"]))

        with bag.transaction():
            bag["outer1"] = 1
            with bag.transaction():
                bag["inner1"] = 2
                bag["inner2"] = 3
            bag["outer2"] = 4

        # due eventi: prima l'inner (chiude prima), poi l'outer
        assert len(received) == 2
        assert len(received[0]) == 2  # inner: 2 mutations
        assert len(received[1]) == 2  # outer: 2 mutations (outer1, outer2)


# =============================================================================
# 16. set_backref manuale
# =============================================================================


class TestSetBackref:
    def test_set_backref_enables_backref_flag(self):
        """set_backref() attiva il flag backref."""
        bag = Bag()
        assert bag.backref is False
        bag.set_backref()
        assert bag.backref is True

    def test_fullpath_none_without_backref(self):
        """fullpath su sub-Bag senza backref e' None."""
        root = Bag()
        root["outer.inner"] = 1
        outer = root.get_item("outer")
        assert isinstance(outer, Bag)
        assert outer.fullpath is None

    def test_fullpath_reports_path_after_subscribe_enables_backref(self):
        """Dopo che subscribe attiva backref, fullpath riflette la gerarchia."""
        root = Bag()
        root["outer.inner"] = 1
        root.subscribe("s1", update=lambda **kw: None)
        outer = root.get_item("outer")
        assert isinstance(outer, Bag)
        assert outer.fullpath == "outer"


# =============================================================================
# 17. subscribe(timer=...) senza interval solleva
# =============================================================================


class TestTimerValidation:
    def test_timer_without_interval_raises(self):
        """subscribe(timer=cb) senza interval solleva ValueError."""
        bag = Bag()
        with pytest.raises(ValueError):
            bag.subscribe("s1", timer=lambda **kw: None)


# =============================================================================
# 18. clear su sub-Bag con backref -> notifica upd_value sul parent
# =============================================================================


class TestClearWithBackref:
    def test_clear_of_nested_bag_notifies_parent_with_oldvalue(self):
        """Una clear() su sub-Bag annidata con backref emette upd_value sul parent.

        oldvalue e' un Bag orfano con il contenuto precedente (snapshot).
        Scenario: reset atomico di una sezione con watcher esterno.
        """
        events: list[dict] = []
        root = Bag()
        root["section.a"] = 1
        root["section.b"] = 2
        root.subscribe("w", update=lambda **kw: events.append(kw))

        section = root.get_item("section")
        assert isinstance(section, Bag)
        section.clear()

        # evento ricevuto dal parent
        assert len(events) >= 1
        last = events[-1]
        assert last["evt"] == "upd_value"
        # oldvalue e' un Bag con il contenuto di prima
        old = last["oldvalue"]
        assert isinstance(old, Bag)
        assert old.get_item("a") == 1
        assert old.get_item("b") == 2

    def test_clear_of_nested_bag_leaves_it_empty(self):
        """Dopo clear() su sub-Bag annidata, la sub-Bag e' vuota."""
        root = Bag()
        root["section.a"] = 1
        root.subscribe("w", update=lambda **kw: None)
        section = root.get_item("section")
        assert isinstance(section, Bag)
        section.clear()
        assert len(section) == 0


# =============================================================================
# 19. fullpath / root su gerarchie profonde (>= 3 livelli)
# =============================================================================


class TestDeepHierarchy:
    def test_fullpath_three_levels(self):
        """fullpath di una foglia a 3 livelli: outer.middle.inner."""
        root = Bag()
        root["a.b.c"] = 42
        root.subscribe("w", update=lambda **kw: None)
        middle = root.get_item("a.b")
        assert isinstance(middle, Bag)
        assert middle.fullpath == "a.b"

    def test_root_traverses_full_chain(self):
        """bag.root dal nodo piu' profondo risale fino alla radice."""
        root = Bag()
        root["a.b.c.d"] = 42
        root.subscribe("w", update=lambda **kw: None)
        deepest = root.get_item("a.b.c")
        assert isinstance(deepest, Bag)
        assert deepest.root is root

    def test_attributes_of_nested_bag_reflect_parent_node(self):
        """sub.attributes legge gli attr del nodo che contiene la sub-Bag."""
        root = Bag()
        root["section.inner"] = "v"
        root.set_attr("section", kind="form")
        root.subscribe("w", update=lambda **kw: None)
        section = root.get_item("section")
        assert isinstance(section, Bag)
        assert section.attributes.get("kind") == "form"


# =============================================================================
# 20. get_inherited_attributes della Bag (sub-Bag eredita da parent)
# =============================================================================


class TestBagGetInheritedAttributes:
    def test_sub_bag_inherits_from_parent_node(self):
        """Bag.get_inherited_attributes raccoglie attributi dalla catena parent.

        Scenario: sezione di form che eredita 'permission' dall'ancestor.
        """
        root = Bag()
        root["outer.inner"] = "v"
        root.set_attr("outer", permission="read")
        root.subscribe("w", update=lambda **kw: None)
        inner_bag = root.get_item("outer.inner")
        # 'outer.inner' non e' un Bag ma un valore scalare; richiede che
        # testiamo il meccanismo a livello di un container interno
        # Riparto: creo una sub-Bag vera come valore
        root2 = Bag()
        deep = Bag()
        deep["k"] = 1
        root2.set_item("section", deep, _attributes={"permission": "write"})
        root2.subscribe("w", update=lambda **kw: None)
        section = root2.get_item("section")
        assert isinstance(section, Bag)
        inherited = section.get_inherited_attributes()
        assert inherited.get("permission") == "write"


# =============================================================================
# 21. relative_path: dalla Bag al nodo discendente
# =============================================================================


class TestRelativePath:
    def test_relative_path_from_root_to_leaf(self):
        """bag.relative_path(leaf_node) ritorna il path dal bag al nodo."""
        root = Bag()
        root["a.b.c"] = 42
        root.subscribe("w", update=lambda **kw: None)
        leaf = root.get_node("a.b.c")
        assert isinstance(leaf, BagNode)
        assert root.relative_path(leaf) == "a.b.c"

    def test_relative_path_from_intermediate_to_leaf(self):
        """Path relativo dall'intermedio al figlio diretto."""
        root = Bag()
        root["outer.inner.leaf"] = 1
        root.subscribe("w", update=lambda **kw: None)
        outer = root.get_item("outer")
        assert isinstance(outer, Bag)
        leaf = root.get_node("outer.inner.leaf")
        assert isinstance(leaf, BagNode)
        # il path da 'outer' alla foglia e' 'inner.leaf'
        assert outer.relative_path(leaf) == "inner.leaf"


# =============================================================================
# 22. clear_backref: detach ricorsivo del sub-tree
# =============================================================================


class TestClearBackref:
    def test_clear_backref_disables_backref(self):
        """clear_backref() disabilita il backref sulla Bag."""
        bag = Bag()
        bag["x"] = 1
        bag.set_backref()
        assert bag.backref is True
        bag.clear_backref()
        assert bag.backref is False

    def test_clear_backref_recursive_on_nested_bags(self):
        """clear_backref() disabilita il backref anche sulle sub-Bag."""
        root = Bag()
        root["section.inner"] = 1
        root.subscribe("w", update=lambda **kw: None)
        section = root.get_item("section")
        assert isinstance(section, Bag)
        assert section.backref is True  # ereditato da root
        root.clear_backref()
        assert root.backref is False
        assert section.backref is False


# =============================================================================
# 23. get_node con autocreate su Bag con subscribers -> ins event
# =============================================================================


class TestAutocreateWithSubscribers:
    def test_autocreate_fires_insert_event(self):
        """get_node(path, autocreate=True) su Bag con backref emette ins event."""
        events: list = []
        bag = Bag()
        bag.subscribe("w", insert=lambda **kw: events.append(kw["node"].label))
        bag.get_node("newnode", autocreate=True)
        assert "newnode" in events


# =============================================================================
# 24. Stop propagation su insert e delete
# =============================================================================


class TestStopPropagationInsertDelete:
    def test_false_on_child_insert_blocks_parent(self):
        """Callback insert sul child che ritorna False blocca la propagazione."""
        root = Bag()
        # creo la sub-Bag 'section' con un nodo preesistente
        root["section.x"] = 0
        section = root.get_item("section")
        assert isinstance(section, Bag)

        root_events: list = []
        child_events: list = []
        section.subscribe(
            "child_sub",
            insert=lambda **kw: (child_events.append(kw["node"].label), False)[1],
        )
        root.subscribe("root_sub", insert=lambda **kw: root_events.append(kw["node"].label))

        # nuovo insert dentro section
        root["section.new"] = 1

        assert child_events == ["new"]
        assert root_events == []

    def test_false_on_child_delete_blocks_parent(self):
        """Callback delete sul child che ritorna False blocca la propagazione."""
        root = Bag()
        root["section.x"] = 0
        section = root.get_item("section")
        assert isinstance(section, Bag)

        root_events: list = []
        child_events: list = []
        section.subscribe(
            "child_sub",
            delete=lambda **kw: (child_events.append(kw["node"].label), False)[1],
        )
        root.subscribe("root_sub", delete=lambda **kw: root_events.append(kw["node"].label))

        # delete dentro section
        root.pop("section.x")

        assert child_events == ["x"]
        assert root_events == []


# =============================================================================
# 25. Update dentro transaction (record come mutation 'upd')
# =============================================================================


class TestTransactionUpdates:
    def test_update_inside_transaction_captured_as_upd_mutation(self):
        """Modifiche di valore dentro transaction finiscono nel batch come 'upd'."""
        received: list[list] = []
        bag = Bag()
        bag["x"] = 1  # pre-esistente
        bag.subscribe("s1", transaction=lambda **kw: received.append(kw["mutations"]))

        with bag.transaction():
            bag["x"] = 99        # update del valore
            bag["new"] = "ins"   # insert
            bag.pop("x")         # delete

        assert len(received) == 1
        kinds = [m[0] for m in received[0]]
        assert kinds == ["upd", "ins", "del"]


# =============================================================================
# 26. Delete propagazione verso root (pathlist)
# =============================================================================


class TestDeletePropagation:
    def test_delete_in_child_bubbles_with_pathlist(self):
        """pop su una foglia in sub-Bag notifica il root con pathlist."""
        captured: list[list] = []
        root = Bag()
        root["section.x"] = 1
        root.subscribe("w", delete=lambda **kw: captured.append(kw["pathlist"]))
        root.pop("section.x")

        assert len(captured) == 1
        # pathlist contiene la sequenza di label dal parent fino al nodo cancellato
        assert captured[0] == ["section"]


# =============================================================================
# 27. bag.move con backref: emette eventi del/ins per il riordino
# =============================================================================


class TestMoveWithBackref:
    def test_single_move_fires_del_and_ins_events(self):
        """move(0, 2) con backref emette prima un del sul nodo spostato e poi un ins."""
        events: list[str] = []
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag.subscribe(
            "w",
            delete=lambda **kw: events.append(f"del:{kw['node'].label}"),
            insert=lambda **kw: events.append(f"ins:{kw['node'].label}"),
        )
        bag.move(0, 2)
        # 'a' viene prima rimosso e poi reinserito in posizione 2
        assert "del:a" in events
        assert "ins:a" in events
        # ordine finale coerente con la semantica di move
        assert bag.keys() == ["b", "c", "a"]

    def test_single_move_trigger_false_suppresses_events(self):
        """move(..., trigger=False) non emette ins/del events."""
        events: list[str] = []
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag.subscribe(
            "w",
            any=lambda **kw: events.append(kw["evt"]),
        )
        bag.move(0, 1, trigger=False)
        assert events == []

    def test_multi_move_fires_events_for_each_node(self):
        """move([0, 2], 1) con backref emette eventi per ciascun nodo spostato."""
        events: list[str] = []
        bag = Bag()
        bag["a"] = 1
        bag["b"] = 2
        bag["c"] = 3
        bag["d"] = 4
        bag.subscribe(
            "w",
            delete=lambda **kw: events.append(f"del:{kw['node'].label}"),
            insert=lambda **kw: events.append(f"ins:{kw['node'].label}"),
        )
        bag.move([0, 2], 1)
        # entrambi i nodi spostati ricevono del + ins
        assert any(e.startswith("del:a") for e in events)
        assert any(e.startswith("ins:a") for e in events)
        assert any(e.startswith("del:c") for e in events)
        assert any(e.startswith("ins:c") for e in events)
