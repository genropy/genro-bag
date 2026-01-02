# Bag Specification

## Overview

La Bag è il container gerarchico principale. Contiene BagNodes accessibili per label o posizione, con supporto per path dotted (`a.b.c`).

## Struttura Interna

```python
class Bag:
    _nodes: NodeContainer      # Container ordinato di BagNodes
    _backref: bool             # Se True, abilita trigger e parent tracking
    _parent: Bag | None        # Bag padre (se nested)
    _parentNode: BagNode | None  # BagNode che contiene questa Bag
    _subscribers: dict         # Subscriber per eventi upd/ins/del
```

## __init__

```python
def __init__(self, source: dict[str, Any] | None = None):
```

- Crea un NodeContainer vuoto
- `_backref` default `False` (lightweight mode)
- Se `source` passato, chiama `_fill_from()`

## Dual Mode (backref)

- `backref=False` (default): Lightweight, no trigger, performance ottimale
- `backref=True`: Strict tree, eventi propagati UP, una sola parent

## Subscribers

Dizionario unificato con chiavi:
- `'upd'`: callback per update
- `'ins'`: callback per insert
- `'del'`: callback per delete

---

## Unimplemented Features

### _modified (dirty flag)

Flag per tracciare se la Bag è stata modificata:

```python
self._modified = None  # None = non tracciato, False = pulito, True = modificato
```

Quando settato a un valore non-None:
- Si sottoscrive automaticamente a tutti gli eventi
- Qualsiasi modifica lo mette a `True`

Quando settato a `None`:
- Si disiscrive dagli eventi

Utile per:
- "Vuoi salvare le modifiche?"
- Ottimizzare serializzazioni (non riscrivere se non modificato)

### _rootattributes

Attributi della root per serializzazione XML.

### _symbols

Simboli per valutazione espressioni nei path.
