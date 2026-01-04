# Compatibility Layer: gnrbag → genro-bag

Documento che traccia le differenze tra l'implementazione originale (gnrbag) e la nuova (genro-bag), per facilitare la migrazione del codice esistente.

---

## Naming Convention: camelCase → snake_case

| Originale (camelCase) | Nuovo (snake_case) |
|-----------------------|-------------------|
| `getItem` | `get_item` |
| `setItem` | `set_item` |
| `delItem` | `del_item` |
| `getNode` | `get_node` |
| `getNodes` | `get_nodes` |
| `popNode` | `pop_node` |
| `setAttr` | `set_attr` |
| `getAttr` | `get_attr` |
| `delAttr` | `del_attr` |
| `parentNode` | `parent_node` |
| `fullpath` | `fullpath` (invariato) |
| `rootattributes` | `root_attributes` |
| `setBackRef` | `set_backref` |
| `clearBackRef` | `clear_backref` |
| `delParentRef` | `del_parent_ref` |
| `fillFrom` | `fill_from` |
| `asDict` | `as_dict` |
| `asDictDeeply` | `as_dict_deeply` |
| `asString` | `as_string` |
| `toXml` | `to_xml` |
| `fromXml` | `from_xml` |
| `toJson` | `to_json` |
| `fromJson` | `from_json` |
| `getResolver` | `get_resolver` |
| `setResolver` | `set_resolver` |
| `getNodeByAttr` | `get_node_by_attr` |
| `getNodeByValue` | `get_node_by_value` |
| `getDeepestNode` | `get_deepest_node` |
| `appendNode` | `append_node` |
| `addItem` | `add_item` |
| `getInheritedAttributes` | `get_inherited_attributes` |
| `setCallBackItem` | `set_callback_item` |
| `nodesByAttr` | `nodes_by_attr` |
| `findNodeByAttr` | `find_node_by_attr` |
| `getIndex` | `get_index` |
| `getIndexList` | `get_index_list` |
| `getLeaves` | `get_leaves` |
| `getFormattedValue` | `get_formatted_value` |
| `isEmpty` | `is_empty` |

---

## Metodi Eliminati (Python 2 → Python 3)

| Eliminato | Sostituzione | Note |
|-----------|--------------|------|
| `iterkeys()` | `keys(iter=True)` | Parametro `iter` aggiunto |
| `itervalues()` | `values(iter=True)` | Parametro `iter` aggiunto |
| `iteritems()` | `items(iter=True)` | Parametro `iter` aggiunto |
| `has_key(path)` | `path in bag` | Era nell'originale, deprecato in Python 3 |

---

## Metodi Deprecati (non implementati)

| Metodo | Motivo |
|--------|--------|
| `node` (property) | Deprecato in originale, usa `parent_node` |
| `merge()` | Deprecato in originale, usa `update()` |

---

## Differenze di Comportamento

### setdefault

**Originale** (bug):
```python
def setdefault(self, path, default=None):
    node = self.getNode(path)
    if not node:
        self[path] = default
    else:
        return node.value  # non ritorna nulla se crea il nodo!
```

**Nuovo** (corretto):
```python
def setdefault(self, path, default=None):
    node = self.get_node(path)
    if not node:
        self[path] = default
        return default  # ritorna sempre il valore
    return node.value
```

---

## Parametri Rinominati

| Metodo | Parametro Originale | Parametro Nuovo |
|--------|---------------------|-----------------|
| `set_item` | `_removeNullAttributes` | `_remove_null_attributes` |
| `digest` | `asColumns` | `as_columns` |
| `columns` | `attrMode` | `attr_mode` |
| `get_node` | `asTuple` | `as_tuple` |

---

## Note per il Layer di Compatibilità

Per creare un layer di compatibilità che permetta al codice legacy di funzionare:

```python
# compatibility.py

class BagCompat(Bag):
    """Bag con alias camelCase per compatibilità."""

    # Alias metodi
    getItem = Bag.get_item
    setItem = Bag.set_item
    getNode = Bag.get_node
    # ... etc

    # Metodi eliminati
    def iterkeys(self):
        return self.keys(iter=True)

    def itervalues(self):
        return self.values(iter=True)

    def iteritems(self):
        return self.items(iter=True)

    def has_key(self, path):
        return path in self

    # Property deprecate
    @property
    def node(self):
        import warnings
        warnings.warn("node is deprecated, use parent_node", DeprecationWarning)
        return self.parent_node

    @property
    def rootattributes(self):
        return self.root_attributes

    @rootattributes.setter
    def rootattributes(self, value):
        self.root_attributes = value
```
