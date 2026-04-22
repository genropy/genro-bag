# tests/spec — Spec-driven test suite

**Status**: DA REVISIONARE — suite in costruzione, non ancora approvata come sostituto della suite storica.

## Principi

I test in questa directory seguono 4 principi, da cui il nome "spec":

1. **Dai docstring, non dal codice.** Ogni test nasce dalla documentazione pubblica di un metodo di `Bag` (docstring, README, manual). Non si scrivono test per "coprire un ramo if" — si scrivono test per "documentare una variante d'uso".

2. **End-to-end, non primitive interne.** Il test crea una `Bag`, esercita un'operazione pubblica, verifica il comportamento osservabile. Nessun accesso a `_nodes`, `_htraverse`, `_node_to_xml` o qualunque altro attributo con underscore.

3. **Un modulo = un dominio omogeneo.** `test_basic.py` tocca solo operazioni base senza resolver né subscription. `test_query.py` solo query/walk/aggregazioni. Non si mescolano domini nello stesso file.

4. **Non si testa ciò che non esiste da solo.** `BagNode`, `BagNodeContainer`, `BagResolver` sono strutture interne. L'utente li incontra solo come conseguenza di operazioni su `Bag`. Vengono esercitati attraverso la `Bag`, mai in isolamento.

## API pubblica

Definizione operativa: **tutto ciò che non inizia con `_`**.

- `set_item` è pubblica.
- `_htraverse` non lo è.

I dunder (`__init__`, `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`, `__len__`, `__iter__`, `__eq__`, `__ne__`, `__str__`, `__repr__`, `__call__`) fanno parte dell'API.

## Processo

1. Si parte dai metodi più fondativi (`set_item`, `get_item`, accesso `[...]`).
2. Si scrive un test per variante d'uso documentata.
3. Si misura la coverage con:

   ```bash
   pytest tests/spec/ --cov=genro_bag --cov-report=term-missing --cov-report=html:htmlcov-spec
   ```

4. Si apre `htmlcov-spec/index.html`, si guarda quali rami restano scoperti, si decide il prossimo test.
5. Il coverage report è la TODO-list: non si scrive test "in più" senza verificare che aggiunga copertura reale.

## Moduli previsti

Ordine di costruzione:

1. `test_basic.py` — istanziazione, `set_item`/`get_item`, `[...]`, `len`, `in`, iter, `get_node`, proprietà base.
2. `test_query.py` — `query`, `walk`, `keys`/`values`/`items`, `get_nodes`, `sort`, `sum`, `is_empty`, `columns`.
3. `test_population.py` — `fill_from`, `update`, `deepcopy`, `from_url`.
4. `test_serialization.py` — `to_xml`/`from_xml`, `to_json`/`from_json`, `to_tytx`/`from_tytx`.
5. `test_events.py` — `subscribe`/`unsubscribe`, `transaction`, backref.
6. `test_resolvers.py` — `Bag` con resolver come valori (comportamento osservabile).

Ogni modulo si chiude quando la coverage marginale che aggiunge è sotto soglia e ogni metodo pubblico del dominio è stato chiamato in tutte le varianti documentate.

## Cosa questa suite NON contiene

- Test su `BagNode`, `BagNodeContainer`, `BagResolver` istanziati direttamente.
- Test che esercitano attributi o metodi con underscore.
- Test "tappabuchi" il cui solo scopo è alzare una metrica.
- Duplicazioni di dominio (una feature sta in un solo file).
