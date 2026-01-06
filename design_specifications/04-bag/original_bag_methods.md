# Original Bag Methods

Elenco completo dei metodi della classe `Bag` originale (gnrbag.py).

**Legenda priorità**:
- `✓` = Implementato
- `P2` = Priority 2 (dopo il core)
- `P3` = Priority 3 (nice to have)
- `NO` = Non implementare (deprecated/legacy)
- `?` = Da decidere

---

## Initialization & Properties

| Method | Priority | Notes |
|--------|----------|-------|
| `__init__(source, **kwargs)` | ✓ | Costruttore |
| `parent` (property) | ✓ | Riferimento al parent Bag |
| `fullpath` (property) | ✓ | Path completo dalla root |
| `node` (property) | NO | DEPRECATED - usa `parent_node` |
| `parentNode` (property) | ✓ | `parent_node` - Nodo parent |
| `attributes` (property) | ✓ | Attributi del parentNode |
| `rootattributes` (property) | ✓ | `root_attributes` - Attributi root |
| `modified` (property) | ✓ | Flag modificato |
| `backref` (property) | ✓ | Modalità backref |
| `nodes` (property) | ✓ | Lista nodi (via `_nodes`) |

---

## Core Access (dict-like)

| Method | Priority | Notes |
|--------|----------|-------|
| `__getitem__(path)` | ✓ | `bag['a.b.c']` |
| `__setitem__(path, value)` | ✓ | `bag['a.b.c'] = v` |
| `__delitem__(path)` | ✓ | `del bag['a.b.c']` |
| `__contains__(what)` | ✓ | `'a.b' in bag` |
| `__iter__()` | ✓ | `for node in bag` |
| `__len__()` | ✓ | `len(bag)` |
| `__call__(what)` | ✓ | `bag()` returns keys |
| `getItem(path, default, mode)` | ✓ | `get_item` - Get con default |
| `setItem(path, value, **kw)` | ✓ | `set_item` - Set con attributi |
| `get(label, default, mode)` | ✓ | Get singolo livello |
| `setdefault(path, default)` | ✓ | Come dict.setdefault |
| `pop(path, dflt)` | ✓ | Rimuove e ritorna |
| `popNode(path)` | ✓ | `pop_node` - Rimuove e ritorna nodo |
| `clear()` | ✓ | Svuota la bag |
| `keys()` | ✓ | Lista labels (con `iter=True` per generatore) |
| `values()` | ✓ | Lista valori (con `iter=True` per generatore) |
| `items()` | ✓ | Lista (label, value) (con `iter=True` per generatore) |
| `iteritems()` | NO | Usa `items(iter=True)` |
| `iterkeys()` | NO | Usa `keys(iter=True)` |
| `itervalues()` | NO | Usa `values(iter=True)` |
| `has_key(path)` | NO | Usa `path in bag` |

---

## Node Access

| Method | Priority | Notes |
|--------|----------|-------|
| `getNode(path, asTuple, autocreate, default)` | ✓ | `get_node` |
| `getNodes(condition)` | ✓ | `get_nodes` - Lista nodi filtrati |
| `getNodeByAttr(attr, value, path)` | ✓ | `get_node_by_attr` |
| `getNodeByValue(label, value)` | ✓ | `get_node_by_value` |
| `getDeepestNode(path)` | NO | Non usato. Usa `_traverse_until()` se serve |
| `appendNode(label, value, **kw)` | NO | Usa `set_item()` |
| `addItem(path, value, **kw)` | NO | Usa `set_item()` (no duplicati) |

---

## Attributes

| Method | Priority | Notes |
|--------|----------|-------|
| `setAttr(path, _attributes, **kw)` | ✓ | `set_attr` |
| `getAttr(path, attr, default)` | ✓ | `get_attr` |
| `delAttr(path, attr)` | ✓ | `del_attr` |
| `getInheritedAttributes()` | ✓ | `get_inherited_attributes` |

---

## Path Traversal (Internal)

**NOTA: Metodi privati - non considerare nel confronto (gestiti internamente).**

| Method | Priority | Notes |
|--------|----------|-------|
| `_htraverse(...)` | -- | Interno, implementato |
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
| `setBackRef(node, parent)` | ✓ | `set_backref` |
| `clearBackRef()` | ✓ | `clear_backref` |
| `delParentRef()` | ✓ | `del_parent_ref` |
| `subscribe(id, update, insert, delete, any)` | ✓ | `subscribe` |
| `unsubscribe(id, **kw)` | ✓ | `unsubscribe` |
| `_onNodeChanged(...)` | -- | Interno `_on_node_changed` |
| `_onNodeInserted(...)` | -- | Interno `_on_node_inserted` |
| `_onNodeDeleted(...)` | -- | Interno `_on_node_deleted` |
| `_subscribe(...)` | -- | Interno, non considerare |

---

## Serialization

| Method | Priority | Notes |
|--------|----------|-------|
| `toXml(filename, encoding, **kw)` | ✓ | `to_xml` (via BagSerializer mixin) |
| `fromXml(source, **kw)` | ✓ | `from_xml` (via BagParser mixin) |
| `toJson(typed, nested)` | ✓ | `to_json` |
| `fromJson(json, listJoiner)` | ✓ | `from_json` |
| `fromYaml(y, listJoiner)` | ? | Da valutare |
| `pickle(destination, bin)` | ✓ | Supporto pickle nativo |
| `unpickle(source)` | ✓ | Supporto pickle nativo |
| `fillFrom(source, **kw)` | ✓ | `fill_from` |
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
| `asDict(ascii, lower)` | ✓ | `as_dict` - Bag → dict (1 livello) |
| `asDictDeeply(ascii, lower)` | NO | Usa `to_json(serialize=False)` |
| `asString(encoding, mode)` | NO | Usa `str(bag)` |
| `__str__(exploredNodes, mode)` | ✓ | Rappresentazione string |

---

## Query & Iteration

| Method | Priority | Notes |
|--------|----------|-------|
| `digest(what, condition, asColumns)` | ✓ | Alias retrocompatibile per `query()` |
| `query(what, condition, iter, deep, leaf, branch, limit)` | ✓ | **NUOVO** - Sostituisce digest con più funzionalità |
| `columns(cols, attrMode)` | ✓ | `columns` (usa digest) |
| `filter(cb, _mode)` | NO | Usa `get_nodes(condition)` o `query(condition=...)` |
| `walk(callback, _mode)` | ✓ | Generatore o callback mode |
| `traverse()` | NO | Usa `walk()` senza callback |
| `cbtraverse(pathlist, callback, result)` | NO | Uso raro. Usa loop su `get_node` |
| `getIndex()` | NO | Usa `query('#p', deep=True)` |
| `getIndexList(asText)` | NO | Usa `query('#p', deep=True)` |
| `getLeaves()` | NO | Usa `query('#p,#v', deep=True, branch=False)` |
| `nodesByAttr(attr, _mode, **kw)` | NO | Usa `query('#n', condition=lambda n: n.get_attr('x') == v)` |
| `findNodeByAttr(attr, value, _mode)` | NO | Usa `get_node_by_attr` o `query('#n', condition=...)` |
| `isEmpty(zeroIsNone, blankIsNone)` | ✓ | `is_empty` |

---

## Copy & Merge

| Method | Priority | Notes |
|--------|----------|-------|
| `copy()` | NO | Bug: shallow copy. Usa `deepcopy()` |
| `deepcopy()` | ✓ | Copia deep |
| `update(otherbag, resolved, ignoreNone)` | ✓ | Merge in place |
| `merge(otherbag, **options)` | NO | DEPRECATED - usa `update()` |

---

## Comparison

| Method | Priority | Notes |
|--------|----------|-------|
| `__eq__(other)` | ✓ | `bag1 == bag2` |
| `__ne__(other)` | ✓ | `bag1 != bag2` |
| `diff(other)` | NO | Design problematico. Da rivalutare se serve |

---

## Sort & Aggregation

| Method | Priority | Notes |
|--------|----------|-------|
| `sort(pars)` | ✓ | `sort(key)` - Ordina nodi |
| `sum(what)` | ✓ | `sum(what, condition, deep)` - Somma valori (usa `query`) |
| `summarizeAttributes(attrnames)` | NO | Usa `sum('#a.attr1,#a.attr2', deep=True)` |

---

## Resolver

| Method | Priority | Notes |
|--------|----------|-------|
| `getResolver(path)` | ✓ | `get_resolver` |
| `setResolver(path, resolver)` | ✓ | `set_resolver` |
| `setCallBackItem(path, callback)` | ✓ | `set_callback_item` |

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
| `__getstate__()` | ✓ | Per pickle |
| `makePicklable()` | ✓ | `_make_picklable` (interno) |
| `restoreFromPicklable()` | ✓ | `_restore_from_picklable` (interno) |

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
| `toTree(group_by, caption, attributes)` | NO | Uso raro |
| `popAttributesFromNodes(blacklist)` | NO | Uso raro |
| `getFormattedValue(joiner, omitEmpty)` | NO | Uso raro |
| `__pow__(kwargs)` | ? | Da valutare - `bag ** {'attr': v}` setta attr |
| `_setModified(...)` | -- | Interno, non considerare |
| `_deepIndex(...)` | -- | Interno, non considerare |

---

## Riepilogo

### Metodi Implementati (✓)
La maggior parte dei metodi core sono stati implementati con naming snake_case.

### Nuovi Metodi
- `query(what, condition, iter, deep, leaf, branch)` - Estende `digest` con iteratori, traversal ricorsivo e filtri leaf/branch

### Metodi Deprecati (NO)
- Metodi Python 2 (`iteritems`, `iterkeys`, `itervalues`, `has_key`)
- Metodi con bug (`copy`)
- Metodi legacy (`merge`, `filter`, `traverse`, `cbtraverse`)
- Metodi coperti da `query`: `nodesByAttr`, `findNodeByAttr`, `getLeaves`, `summarizeAttributes`
- Sistema Formula e Validation

### Da Valutare (?)
- `getNodeByValue`
- `fromYaml`
- `__pow__`
