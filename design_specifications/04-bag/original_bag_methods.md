# Original Bag Methods

Elenco completo dei metodi della classe `Bag` originale (gnrbag.py).

**Legenda priorità**:
- `P1` = Priority 1 (core, subito)
- `P2` = Priority 2 (dopo il core)
- `P3` = Priority 3 (nice to have)
- `NO` = Non implementare (deprecated/legacy)
- `?` = Da decidere

---

## Initialization & Properties

| Method | Priority | Notes |
|--------|----------|-------|
| `__init__(source, **kwargs)` | ? | Costruttore |
| `parent` (property) | ? | Riferimento al parent Bag |
| `fullpath` (property) | ? | Path completo dalla root |
| `node` (property) | ? | DEPRECATED - usa parentNode |
| `parentNode` (property) | ? | Nodo parent |
| `attributes` (property) | ? | Attributi del parentNode |
| `rootattributes` (property) | ? | Attributi root |
| `modified` (property) | ? | Flag modificato |
| `backref` (property) | ? | Modalità backref |
| `nodes` (property) | ? | Lista nodi |

---

## Core Access (dict-like)

| Method | Priority | Notes |
|--------|----------|-------|
| `__getitem__(path)` | ? | `bag['a.b.c']` |
| `__setitem__(path, value)` | ? | `bag['a.b.c'] = v` |
| `__delitem__(path)` | ? | `del bag['a.b.c']` |
| `__contains__(what)` | ? | `'a.b' in bag` |
| `__iter__()` | ? | `for node in bag` |
| `__len__()` | ? | `len(bag)` |
| `__call__(what)` | ? | `bag()` returns keys |
| `getItem(path, default, mode)` | ? | Get con default |
| `setItem(path, value, **kw)` | ? | Set con attributi |
| `get(label, default, mode)` | ? | Get singolo livello |
| `setdefault(path, default)` | ? | Come dict.setdefault |
| `pop(path, dflt)` | ? | Rimuove e ritorna |
| `popNode(path)` | ? | Rimuove e ritorna nodo |
| `clear()` | ? | Svuota la bag |
| `keys()` | ? | Lista labels |
| `values()` | ? | Lista valori |
| `items()` | ? | Lista (label, value) |
| `iteritems()` | ? | Generatore items |
| `iterkeys()` | ? | Generatore keys |
| `itervalues()` | ? | Generatore values |
| `has_key(path)` | ? | Esiste path? |

---

## Node Access

| Method | Priority | Notes |
|--------|----------|-------|
| `getNode(path, asTuple, autocreate, default)` | ? | Ritorna BagNode |
| `getNodes(condition)` | ? | Lista nodi filtrati |
| `getNodeByAttr(attr, value, path)` | ? | Cerca nodo per attributo |
| `getNodeByValue(label, value)` | ? | Cerca nodo per valore |
| `getDeepestNode(path)` | ? | Nodo più profondo esistente |
| `appendNode(label, value, **kw)` | ? | Aggiunge nodo in coda |
| `addItem(path, value, **kw)` | ? | Aggiunge (duplicati ok) |

---

## Attributes

| Method | Priority | Notes |
|--------|----------|-------|
| `setAttr(path, _attributes, **kw)` | ? | Setta attributi |
| `getAttr(path, attr, default)` | ? | Legge attributo |
| `delAttr(path, attr)` | ? | Elimina attributo |
| `getInheritedAttributes()` | ? | Attributi ereditati |

---

## Path Traversal (Internal)

**NOTA: Metodi privati - non considerare nel confronto (gestiti internamente).**

| Method | Priority | Notes |
|--------|----------|-------|
| `_htraverse(...)` | -- | Interno, non considerare |
| `_index(label)` | -- | Interno, non considerare |
| `_pathSplit(path)` | -- | Interno, non considerare |
| `_set(label, value, **kw)` | -- | Interno, non considerare |
| `_pop(label)` | -- | Interno, non considerare |
| `_getNode(label, autocreate, default)` | -- | Interno, non considerare |
| `_insertNode(node, position)` | -- | Interno, non considerare |

---

## Backref & Triggers

| Method | Priority | Notes |
|--------|----------|-------|
| `setBackRef(node, parent)` | ? | Attiva modalità backref |
| `clearBackRef()` | ? | Disattiva backref |
| `delParentRef()` | ? | Rimuove riferimento parent |
| `subscribe(id, update, insert, delete, any)` | ? | Sottoscrivi eventi |
| `unsubscribe(id, **kw)` | ? | Rimuovi sottoscrizione |
| `_onNodeChanged(...)` | -- | Interno, non considerare |
| `_onNodeInserted(...)` | -- | Interno, non considerare |
| `_onNodeDeleted(...)` | -- | Interno, non considerare |
| `_subscribe(...)` | -- | Interno, non considerare |

---

## Serialization

| Method | Priority | Notes |
|--------|----------|-------|
| `toXml(filename, encoding, **kw)` | ? | Bag → XML |
| `fromXml(source, **kw)` | ? | XML → Bag |
| `toJson(typed, nested)` | ? | Bag → JSON |
| `fromJson(json, listJoiner)` | ? | JSON → Bag |
| `fromYaml(y, listJoiner)` | ? | YAML → Bag |
| `pickle(destination, bin)` | ? | Bag → pickle |
| `unpickle(source)` | ? | pickle → Bag |
| `fillFrom(source, **kw)` | ? | Riempie da sorgente |
| `_fromSource(...)` | -- | Interno, non considerare |
| `_sourcePrepare(...)` | -- | Interno, non considerare |
| `_fromXml(...)` | -- | Interno, non considerare |
| `_fromJson(...)` | -- | Interno, non considerare |
| `_fromYaml(...)` | -- | Interno, non considerare |
| `_unpickle(...)` | -- | Interno, non considerare |

---

## Conversion

| Method | Priority | Notes |
|--------|----------|-------|
| `asDict(ascii, lower)` | P2 | Da implementare - Bag → dict (1 livello). `dict(bag)` non funziona perché `__iter__` itera sui nodi |
| `asDictDeeply(ascii, lower)` | ? | Bag → dict (ricorsivo) |
| `asString(encoding, mode)` | ? | Bag → string |
| `__str__(exploredNodes, mode)` | ? | Rappresentazione string |

---

## Query & Iteration

| Method | Priority | Notes |
|--------|----------|-------|
| `digest(what, condition, asColumns)` | ? | Estrae liste di valori/attr |
| `columns(cols, attrMode)` | ? | Digest come colonne |
| `filter(cb, _mode)` | ? | Filtra nodi |
| `walk(callback, _mode)` | ? | Visita tutti i nodi |
| `traverse()` | ? | Generatore depth-first |
| `cbtraverse(pathlist, callback, result)` | ? | Walk con callback per step |
| `getIndex()` | ? | Indice completo |
| `getIndexList(asText)` | ? | Lista path |
| `getLeaves()` | ? | Solo foglie |
| `nodesByAttr(attr, _mode, **kw)` | ? | Nodi con attributo |
| `findNodeByAttr(attr, value, _mode)` | ? | Primo nodo con attr=value |
| `isEmpty(zeroIsNone, blankIsNone)` | ? | Bag vuota? |

---

## Copy & Merge

| Method | Priority | Notes |
|--------|----------|-------|
| `copy()` | ? | Copia shallow |
| `deepcopy()` | ? | Copia deep |
| `update(otherbag, resolved, ignoreNone)` | ? | Merge in place |
| `merge(otherbag, **options)` | ? | DEPRECATED - merge con opzioni |

---

## Comparison

| Method | Priority | Notes |
|--------|----------|-------|
| `__eq__(other)` | ? | `bag1 == bag2` |
| `__ne__(other)` | ? | `bag1 != bag2` |
| `diff(other)` | ? | Differenze tra bag |

---

## Sort & Aggregation

| Method | Priority | Notes |
|--------|----------|-------|
| `sort(pars)` | ? | Ordina nodi |
| `sum(what)` | ? | Somma valori |
| `summarizeAttributes(attrnames)` | ? | Somma attributi |

---

## Resolver

| Method | Priority | Notes |
|--------|----------|-------|
| `getResolver(path)` | ? | Ritorna resolver |
| `setResolver(path, resolver)` | ? | Setta resolver |
| `setCallBackItem(path, callback)` | ? | BagCbResolver |

---

## Formula (legacy)

**NOTA: Sistema Formula non sarà portato - funzionalità legacy non più utilizzata.**

| Method | Priority | Notes |
|--------|----------|-------|
| `defineSymbol(**kwargs)` | NO | Non portare - legacy |
| `defineFormula(**kwargs)` | NO | Non portare - legacy |
| `formula(formula, **kwargs)` | NO | Non portare - legacy |

---

## Validation

**NOTA: Sistema Validation non sarà portato - gestito diversamente nella nuova architettura.**

| Method | Priority | Notes |
|--------|----------|-------|
| `addValidator(path, validator, params)` | NO | Non portare |
| `removeValidator(path, validator)` | NO | Non portare |

---

## Pickle Support

| Method | Priority | Notes |
|--------|----------|-------|
| `__getstate__()` | P2 | Da implementare - Per pickle |
| `makePicklable()` | P2 | Da implementare - Prepara per pickle |
| `restoreFromPicklable()` | P2 | Da implementare - Ripristina da pickle |

---

## Structure Building (da GnrStructData)

**NOTA: Metodi gestiti dal Builder system - modulo separato (06-builder/).**

| Method | Priority | Notes |
|--------|----------|-------|
| `child(tag, childname, childcontent, _parentTag)` | BUILDER | Gestito dal Builder system |
| `rowchild(childname, _pkey, **kw)` | BUILDER | Da considerare quando si implementa il Builder |

---

## Misc

| Method | Priority | Notes |
|--------|----------|-------|
| `toTree(group_by, caption, attributes)` | ? | Flat → Tree |
| `popAttributesFromNodes(blacklist)` | ? | Rimuove attr da tutti |
| `getFormattedValue(joiner, omitEmpty)` | ? | Valore formattato |
| `__pow__(kwargs)` | ? | Da valutare - `bag ** {'attr': v}` setta attr |
| `_setModified(...)` | -- | Interno, non considerare |
| `_deepIndex(...)` | -- | Interno, non considerare |
