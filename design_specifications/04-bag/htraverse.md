# Confronto completo: Bag._htraverse vs TreeStore._htraverse

## Riferimenti sorgente

| Componente | File |
|------------|------|
| **Bag** | `genro-bag/src/genro_bag/bag.py` |
| **TreeStore** | `genro-treestore/src/genro_treestore/store/core.py` (righe 358-425) |

## Signature

| Bag | TreeStore |
|-----|-----------|
| Input path: `pathlist` (str o list) | Input path: `path` (str) |
| Parametri: `autocreate`, `returnLastMatch` | Parametri: `autocreate` |
| Return: `(bag/node, label/remaining_path)` | Return: `(store, label)` |

## Approccio

| Bag | TreeStore |
|-----|-----------|
| Algoritmo: Ricorsivo | Algoritmo: Iterativo (loop for) |
| Parsing path: `gnrstring.smartsplit()` con sostituzione `../` → `#^.` | Parsing path: `path.split(".")` semplice |
| Struttura dati: Lista `_nodes` + `_index(label)` O(n) | Struttura dati: Dict `_nodes` O(1) |

## Funzionalità

| Feature | Bag | TreeStore |
|---------|-----|-----------|
| Risalita al parent (`#^`, `../`) | ✅ Sì | ❌ No |
| `returnLastMatch` | ✅ Sì | ❌ No |
| Sintassi posizionale (`#N`) | ✅ Sì (in `_index`) | ✅ Sì (`_parse_path_segment`) |
| Gestione resolver durante traversal | ❌ No | ✅ Sì |
| Conversione leaf→branch con autocreate | ✅ Sì | ✅ Sì |

## Creazione nodi intermedi (autocreate=True)

**Bag:**
```python
newnode = BagNode(curr, label=label, value=curr.__class__())
curr._nodes.append(newnode)  # DIRETTO sulla lista
if self.backref:
    self._onNodeInserted(newnode, i, reason='autocreate')
```

**TreeStore:**
```python
child_store = TreeStore(builder=current._builder)
node = TreeStoreNode(key, {}, value=child_store, parent=current)
child_store.parent = node  # MANUALE
current._insert_node(node)  # Chiama metodo
```

## Conversione leaf→branch (autocreate su nodo esistente non-bag)

**Bag:**
```python
if autocreate and not hasattr(newcurr, '_htraverse'):
    newcurr = curr.__class__()
    self._nodes[i].value = newcurr  # Assegnazione diretta
```

**TreeStore:**
```python
if not node.is_branch:
    if autocreate:
        child_store = TreeStore(builder=current._builder)
        child_store.parent = node
        node._value = child_store  # Assegnazione diretta a _value
```

## Gestione errori / path non trovato

**Bag:**
```python
if i < 0:
    if autocreate:
        # crea
    elif returnLastMatch:
        return self.parentNode, '.'.join([label] + pathlist)
    else:
        return None, None
```

**TreeStore:**
```python
if key not in current._nodes:
    if autocreate:
        # crea
    else:
        raise KeyError(f"Path segment '{key}' not found")
```

| Bag | TreeStore |
|-----|-----------|
| Path non trovato: Ritorna `(None, None)` o last match | Path non trovato: Solleva `KeyError` |

## Gestione resolver

**Bag:** Nessuna gestione in `_htraverse`. I resolver vengono risolti altrove (nel getter di value).

**TreeStore:** Risolve inline durante il traversal:
```python
if node._resolver is not None:
    resolver = node._resolver
    if resolver.cache_time != 0 and not resolver.expired:
        resolved = resolver._cache
    else:
        resolved = resolver.load()
        if resolver.cache_time != 0:
            resolver._update_cache(resolved)
    node._value = resolved
```

## returnLastMatch - Dettaglio

Usato in Bag per `getDeepestNode()`: trova il nodo più profondo che esiste e ritorna il path rimanente.

**Caso 1: Nodo non trovato**
```python
return self.parentNode, '.'.join([label] + pathlist)
```
Ritorna il parent e il path completo non trovato.

**Caso 2: Nodo trovato ma non è una Bag (leaf)**
```python
return newcurrnode, '.'.join(pathlist)
```
Ritorna il nodo leaf e il path rimanente.

**Uso tipico:** Permettere ai resolver di gestire il path rimanente.

## Riepilogo differenze critiche

| Aspetto | Bag | TreeStore |
|---------|-----|-----------|
| Algoritmo | Ricorsiva | Iterativa |
| `returnLastMatch` | ✅ Sì (importante per resolver) | ❌ No |
| Risalita `#^`/`../` | ✅ Sì | ❌ No |
| Resolver in traversal | ❌ No | ✅ Sì |
| Errore vs None | Ritorna `None` | Solleva `KeyError` |
| Inserimento nodi | `_nodes.append()` diretto | Chiama `_insert_node()` |
| Backref figlio | Automatico via setter `parentbag` | Manuale (`child_store.parent = node`) |
