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

| Method | Priority | Notes |
|--------|----------|-------|
| `_htraverse(pathlist, autocreate, returnLastMatch)` | ? | Core navigation |
| `_index(label)` | ? | Trova indice per label |
| `_pathSplit(path)` | ? | Split path in lista |
| `_set(label, value, **kw)` | ? | Set interno |
| `_pop(label)` | ? | Pop interno |
| `_getNode(label, autocreate, default)` | ? | GetNode interno |
| `_insertNode(node, position)` | ? | Insert con posizione |

---

## Backref & Triggers

| Method | Priority | Notes |
|--------|----------|-------|
| `setBackRef(node, parent)` | ? | Attiva modalità backref |
| `clearBackRef()` | ? | Disattiva backref |
| `delParentRef()` | ? | Rimuove riferimento parent |
| `subscribe(id, update, insert, delete, any)` | ? | Sottoscrivi eventi |
| `unsubscribe(id, **kw)` | ? | Rimuovi sottoscrizione |
| `_onNodeChanged(node, pathlist, evt, oldvalue)` | ? | Trigger interno update |
| `_onNodeInserted(node, ind, pathlist)` | ? | Trigger interno insert |
| `_onNodeDeleted(node, ind, pathlist)` | ? | Trigger interno delete |
| `_subscribe(id, dict, callback)` | ? | Subscribe interno |

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
| `_fromSource(source, fromFile, mode)` | ? | Parse interno |
| `_sourcePrepare(source)` | ? | Prepara sorgente |
| `_fromXml(source, fromFile, **kw)` | ? | XML interno |
| `_fromJson(json, listJoiner)` | ? | JSON interno |
| `_fromYaml(yamlgen, listJoiner)` | ? | YAML interno |
| `_unpickle(source, fromFile)` | ? | Unpickle interno |

---

## Conversion

| Method | Priority | Notes |
|--------|----------|-------|
| `asDict(ascii, lower)` | ? | Bag → dict (1 livello) |
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

| Method | Priority | Notes |
|--------|----------|-------|
| `defineSymbol(**kwargs)` | ? | Definisce simboli |
| `defineFormula(**kwargs)` | ? | Definisce formula |
| `formula(formula, **kwargs)` | ? | Crea BagFormula |

---

## Validation

| Method | Priority | Notes |
|--------|----------|-------|
| `addValidator(path, validator, params)` | ? | Aggiunge validatore |
| `removeValidator(path, validator)` | ? | Rimuove validatore |

---

## Pickle Support

| Method | Priority | Notes |
|--------|----------|-------|
| `__getstate__()` | ? | Per pickle |
| `makePicklable()` | ? | Prepara per pickle |
| `restoreFromPicklable()` | ? | Ripristina da pickle |

---

## Structure Building (da GnrStructData)

| Method | Priority | Notes |
|--------|----------|-------|
| `child(tag, childname, childcontent, _parentTag)` | ? | Crea child strutturato |
| `rowchild(childname, _pkey, **kw)` | ? | Child tipo riga |

---

## Misc

| Method | Priority | Notes |
|--------|----------|-------|
| `toTree(group_by, caption, attributes)` | ? | Flat → Tree |
| `popAttributesFromNodes(blacklist)` | ? | Rimuove attr da tutti |
| `getFormattedValue(joiner, omitEmpty)` | ? | Valore formattato |
| `__pow__(kwargs)` | ? | `bag ** {'attr': v}` setta attr |
| `_setModified(**kwargs)` | ? | Callback interno |
| `_deepIndex(path, resList, exploredItems)` | ? | Index interno |
