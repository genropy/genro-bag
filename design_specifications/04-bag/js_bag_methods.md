# JavaScript Bag Methods (gnrbag.js)

Elenco completo dei metodi delle classi `GnrBagNode`, `GnrBag` e `GnrBagResolver` dalla versione JavaScript.

**Legenda priorità**:
- `P1` = Priority 1 (core, subito)
- `P2` = Priority 2 (dopo il core)
- `P3` = Priority 3 (nice to have)
- `NO` = Non implementare (deprecated/legacy)
- `?` = Da decidere

---

## GnrBagNode

### Constructor & Properties

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(parentbag, label, value, _attr, _resolver)` | ? | Costruttore |
| `_id` | ? | ID univoco auto-incrementato |
| `label` | ? | Label del nodo |
| `locked` | ? | Flag locked |
| `_value` | ? | Valore interno |
| `_status` | ? | 'loaded', 'loading', 'resolving', 'unloaded' |
| `_onChangedValue` | ? | Callback on change |

### Navigation

| Method | Priority | Notes |
|--------|----------|-------|
| `getParentBag()` | ? | Ritorna parent Bag |
| `setParentBag(parentbag)` | ? | Setta parent con backref handling |
| `getParentNode()` | ? | Ritorna parent node (via parentbag._parentnode) |
| `getFullpath(mode, root)` | ? | Path completo, mode: '#', '##', label |
| `isChildOf(bagOrNode)` | ? | Verifica parentela |
| `isAncestor(n)` | ? | Verifica se è ancestor |
| `isDescendant(n)` | ? | Verifica se è descendant |
| `parentshipLevel(node)` | ? | Livello di parentela |
| `orphaned()` | ? | Disconnette dal parent |
| `backrefOk()` | ? | Verifica integrità backref |

### Value Methods

| Method | Priority | Notes |
|--------|----------|-------|
| `getValue(mode, optkwargs)` | ? | Get con resolver, mode: 'static', 'reload', 'notrigger' |
| `getValue2(mode, optkwargs)` | ? | Debug version |
| `setValue(value, doTrigger, _attributes, _updattr, _fired)` | ? | Set con trigger |
| `clearValue(doTrigger)` | ? | Setta a null |
| `getStaticValue()` | ? | Ritorna _value diretto |
| `setStaticValue(value)` | ? | Setta _value diretto |
| `getFormattedValue(kw, mode)` | ? | Valore formattato con label |
| `refresh(always)` | ? | Ricarica se expired |
| `doWithValue(cb, kwargs)` | ? | Async callback pattern |

### Resolver Methods

| Method | Priority | Notes |
|--------|----------|-------|
| `setResolver(resolver)` | ? | Setta resolver con bidirectional link |
| `getResolver()` | ? | Ritorna resolver |
| `resetResolver()` | ? | Reset resolver |
| `isExpired()` | ? | Verifica expired via resolver |
| `isLoaded()` | ? | Status == 'loaded' |
| `isLoading()` | ? | Status == 'loading' |

### Attribute Methods

| Method | Priority | Notes |
|--------|----------|-------|
| `getAttr(label, _default)` | ? | Get singolo attr o tutti |
| `setAttr(attr, doTrigger, updateAttr, changedAttr)` | ? | Set con opzioni |
| `setAttribute(label, value, doTrigger)` | ? | Set singolo attr |
| `updAttributes(attrDict, doTrigger)` | ? | Update attrs |
| `replaceAttr(attributes)` | ? | Rimpiazza tutti |
| `delAttr(attrToDelete)` | ? | Elimina attrs (comma-separated ok) |
| `hasAttr(label, value)` | ? | Verifica esistenza |
| `getInheritedAttributes(attrname)` | ? | Attributi ereditati |
| `attributeOwnerNode(attrname, attrvalue, caseInsensitive)` | ? | Trova owner di attributo |

### Utility Methods

| Method | Priority | Notes |
|--------|----------|-------|
| `getStringId()` | ? | Ritorna 'n_' + _id |
| `_toXmlBlock(kwargs)` | ? | Serializza a XML |
| `toJSONString()` | ? | Serializza a JSON |

---

## GnrBag

### Constructor & Parent

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(source, kw)` | ? | Costruttore |
| `newNode(parentbag, label, value, _attr, _resolver)` | ? | Factory per nodi |
| `fillFrom(source, kw)` | ? | Riempie da array, object, xml string, bag |
| `getParent()` | ? | Ritorna _parent |
| `setParent(parent)` | ? | Setta _parent |
| `getParentNode()` | ? | Ritorna _parentnode |
| `setParentNode(node)` | ? | Setta _parentnode |
| `getRoot()` | ? | Risale alla root bag |
| `attributes()` | ? | Attributi del parentnode |
| `resolver()` | ? | Resolver del parentnode |

### Core Access

| Method | Priority | Notes |
|--------|----------|-------|
| `getItem(path, dft, mode, optkwargs)` | ? | Get gerarchico |
| `setItem(path, value, _attributes, kwargs)` | ? | Set gerarchico, kwargs: _duplicate, _updattr, doTrigger, _position, lazySet, fired |
| `get(label, dflt, mode, optkwargs)` | ? | Get singolo livello con sintassi speciale (?, ~, #attr, #keys, #node, #digest:) |
| `set(label, value, _attributes, kwargs)` | ? | Set singolo livello |
| `addItem(path, value, _attributes, kwargs)` | ? | Set con _duplicate=true |
| `fireItem(path, value, attributes, reason)` | ? | Set + immediate reset a null |
| `pop(path, doTrigger)` | ? | Rimuove e ritorna value |
| `popNode(path, doTrigger)` | ? | Rimuove e ritorna node |
| `delItem(path, doTrigger)` | ? | Alias di pop |
| `clear(triggered)` | ? | Svuota bag |

### Node Access

| Method | Priority | Notes |
|--------|----------|-------|
| `getNode(path, asTuple, autocreate, _default)` | ? | Ritorna BagNode |
| `_getNode(label, autocreate, _default)` | ? | GetNode interno |
| `getNodes(condition)` | ? | Lista nodi, condition opzionale |
| `getNodeByAttr(attr, value, caseInsensitive)` | ? | Cerca nodo per attributo |
| `getNodeByValue(path, value)` | ? | Cerca nodo per valore |
| `findNodeById(id)` | ? | Trova nodo per _id |

### Path Traversal

| Method | Priority | Notes |
|--------|----------|-------|
| `htraverse(pathlist, autocreate)` | ? | Core navigation, usa `#parent` (non `#^`) |
| `index(label)` | ? | Trova indice per label, supporta `#n`, `#attr=value` |
| `_pop(label, doTrigger)` | ? | Pop interno |
| `_insertNode(node, position, _doTrigger)` | ? | Insert con posizione |
| `moveNode(fromPos, toPos, doTrigger)` | ? | Sposta nodo(i) |

### Iteration & Query

| Method | Priority | Notes |
|--------|----------|-------|
| `len()` | ? | Numero nodi |
| `keys()` | ? | Lista labels |
| `values()` | ? | Lista valori |
| `items()` | ? | Lista {key, value} |
| `forEach(callback, mode, kw)` | ? | Itera sui nodi (non ricorsivo) |
| `walk(callback, mode, kw, notRecursive)` | ? | Walk ricorsivo |
| `digest(what, asColumns)` | ? | Estrae liste, what: #k, #v, #a.attr, path |
| `columns(cols, attrMode)` | ? | Digest come colonne |
| `getIndex()` | ? | Indice completo [path, node] |
| `getIndexList(asText)` | ? | Lista path |
| `_deepIndex(path, resList, exploredNodes)` | ? | Index interno |

### Attributes

| Method | Priority | Notes |
|--------|----------|-------|
| `setAttr(path, attr, args)` | ? | Setta attributi su path |
| `getAttr(path, attr, dflt)` | ? | Legge attributo da path |

### Backref & Triggers

| Method | Priority | Notes |
|--------|----------|-------|
| `getBackRef()` | ? | Ritorna _backref |
| `hasBackRef()` | ? | _backref == true |
| `setBackRef(node, parent)` | ? | Attiva backref mode |
| `clearBackRef()` | ? | Disattiva backref |
| `delParentRef()` | ? | Rimuove parent ref |
| `backrefOk()` | ? | Verifica integrità |
| `onNodeTrigger(kw)` | ? | Trigger eventi: kw.evt = 'upd', 'ins', 'del' |
| `runTrigger(kw)` | ? | Esegue callbacks |
| `subscribe(subscriberId, kwargs)` | ? | kwargs: {upd, ins, del, any} |
| `unsubscribe(subscriberId, events)` | ? | Rimuove subscription |

### Conversion & Serialization

| Method | Priority | Notes |
|--------|----------|-------|
| `asDict(recursive, excludeNullValues)` | ? | Bag → object/array |
| `asObj(formatAttributes)` | ? | Bag → object singolo livello |
| `asObjList(labelAs, formatAttributes)` | ? | Bag → array di objects |
| `asString()` | ? | Rappresentazione string |
| `__str__(mode)` | ? | String representation |
| `__str2__(mode)` | ? | String representation (HTML) |
| `toXml(kwargs)` | ? | Bag → XML |
| `toXmlBlock(kwargs)` | ? | XML interno |
| `fromXmlDoc(source, clsdict)` | ? | XML → Bag |
| `getFormattedValue(kw, mode)` | ? | Valore formattato |
| `asHtmlTable(kw, mode)` | ? | Bag → HTML table |
| `asNestedTable(kw, mode)` | ? | Bag → nested HTML table |

### Copy & Merge

| Method | Priority | Notes |
|--------|----------|-------|
| `deepCopy(deep)` | ? | Copia profonda |
| `update(bagOrObj, mode, reason)` | ? | Merge in place |
| `concat(b)` | ? | Concatena nodi |
| `merge()` | ? | TODO (vuoto) |

### Sort & Aggregation

| Method | Priority | Notes |
|--------|----------|-------|
| `sort(pars)` | ? | Ordina nodi, pars: '#k:a', '#v:d', '#a.attr:a*' |
| `sum(path, strictmode)` | ? | Somma valori |

### Formula (legacy)

| Method | Priority | Notes |
|--------|----------|-------|
| `formula(formula, kwargs)` | ? | Crea GnrBagFormula |
| `defineSymbol(kwargs)` | ? | Definisce simboli |
| `defineFormula(kwargs)` | ? | Definisce formula |
| `setCallBackItem(path, callback, parameters, kwargs)` | ? | BagCbResolver |

### Utility

| Method | Priority | Notes |
|--------|----------|-------|
| `getFullpath(mode, root)` | ? | Path completo |
| `isEqual(otherbag)` | ? | Confronta bag |
| `get_modified()` | ? | Flag modified |
| `set_modified(value)` | ? | Setta modified con subscription |
| `_setModified()` | ? | Callback interno |
| `getResolver(path)` | ? | Ritorna resolver da path |
| `pathsplit()` | ? | TODO (vuoto) |
| `rowchild(tag, kw)` | ? | Crea child con label da tag o attr |
| `doWithItem(path, cb, dflt)` | ? | Async callback pattern |

---

## GnrBagResolver

### Constructor & Properties

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(kwargs, isGetter, cacheTime, load)` | ? | Costruttore |
| `kwargs` | ? | Parametri per load |
| `isGetter` | ? | Se true, non setta valore |
| `cacheTime` | ? | >0: TTL, 0: sempre, <0: una volta |
| `lastUpdate` | ? | Timestamp ultimo resolve |
| `_pendingDeferred` | ? | Lista deferred in attesa |
| `_attributes` | ? | Attributi del resolver |

### Core Methods

| Method | Priority | Notes |
|--------|----------|-------|
| `load(kwargs, cb)` | ? | Da implementare nelle sottoclassi |
| `resolve(optkwargs, destinationNode)` | ? | Risolve e ritorna valore |
| `expired(kwargs)` | ? | Verifica se scaduto |
| `reset()` | ? | Reset lastUpdate |
| `onSetResolver(node)` | ? | Hook quando settato su nodo |

### Cache & Deferred

| Method | Priority | Notes |
|--------|----------|-------|
| `setCacheTime(cacheTime)` | ? | Setta TTL |
| `getCacheTime()` | ? | Ritorna TTL |
| `meToo(cb)` | ? | Aggiunge callback a pending |
| `cancelMeToo(r)` | ? | Cancella pending |
| `runPendingDeferred(pendingDeferred)` | ? | Esegue pending callbacks |

### Parent & Attributes

| Method | Priority | Notes |
|--------|----------|-------|
| `setParentNode(parentNode)` | ? | Setta parent node |
| `getParentNode(parentnode)` | ? | Ritorna parent node |
| `getAttr()` | ? | Ritorna _attributes |
| `setAttr(attributes)` | ? | Update _attributes |

### Proxy Methods (delegate to resolved bag)

| Method | Priority | Notes |
|--------|----------|-------|
| `htraverse(kwargs)` | ? | Delegate a resolved bag |
| `keys()` | ? | Delegate |
| `items()` | ? | Delegate |
| `values()` | ? | Delegate |
| `digest(k)` | ? | Delegate |
| `sum(k)` | ? | Delegate |
| `contains()` | ? | Delegate |
| `len()` | ? | Delegate |
| `resolverDescription()` | ? | toString del resolved |

---

## GnrBagFormula (extends GnrBagResolver)

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(root, expr, symbols, kwargs)` | ? | Formula con template |
| `load()` | ? | Eval expression |

---

## GnrBagCbResolver (extends GnrBagResolver)

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(kwargs, isGetter, cacheTime)` | ? | Callback resolver |
| `load(kwargs)` | ? | Chiama method con parameters |

---

## GnrBagGetter (extends GnrBagResolver)

| Method | Priority | Notes |
|--------|----------|-------|
| `constructor(bag, path, what)` | ? | what: 'node', 'value', 'attr' |
| `load()` | ? | Ritorna node/value/attr |

---

## Utility Functions

| Function | Notes |
|----------|-------|
| `isBag(obj)` | Verifica se è GnrBag |
| `gnr.bagRealPath(path)` | Risolve #parent nel path |
| `fromKwargs(kwargs)` | Converte kwargs per formula |

---

## Differenze chiave Python vs JavaScript

| Aspetto | Python | JavaScript |
|---------|--------|------------|
| Parent reference | `#^` | `#parent` |
| Path alias | `../` → `#^.` | `../` → `#parent.` |
| Node status | Non presente | `_status`: loaded, loading, resolving, unloaded |
| Async handling | - | dojo.Deferred |
| Node ID | Non presente | `_id` auto-incrementato |
| `locked` | Rimosso | Presente |
| `fireItem` | Non presente | Set + immediate null |
| `lazySet` | Non presente | Skip se valore uguale |
| Formula | BagFormula | GnrBagFormula |
| Query syntax | - | `label?attr`, `label~path`, `#attr`, `#keys`, `#node`, `#digest:` |

---

## Sintassi speciale nel path (JavaScript)

| Sintassi | Esempio | Significato |
|----------|---------|-------------|
| `?attr` | `node?name` | Ritorna/setta attributo |
| `?#attr` | `node?#attr` | Ritorna tutti gli attributi |
| `?#keys` | `node?#keys` | Ritorna keys della bag |
| `?#node` | `node?#node` | Ritorna il nodo stesso |
| `?#digest:what` | `node?#digest:#k,#v` | Ritorna digest |
| `~path` | `node~subpath` | Accede a subpath o attr |
| `?attr?=expr` | `node?value?=#v*2` | Eval expression su valore |
| `#parent` | `a.#parent.b` | Vai al parent |
| `../` | `a/../b` | Alias per #parent |
| `#n` | `#0`, `#1` | Accesso per indice |
| `#attr=value` | `#id=123` | Cerca per attributo |
