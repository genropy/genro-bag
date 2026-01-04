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
| `addItem()` | La nuova Bag non ammette label duplicate. Usa `set_item()` che sovrascrive se la label esiste |
| `appendNode()` | Aggiungeva nodi "raw" senza controllo duplicati. Usa `set_item()` |
| `getDeepestNode()` | Non usato nel codebase. Se necessario, usare `_traverse_until()` internamente |
| `diff()` | Non portato. L'originale aveva problemi: ritorno misto (None/str), solo prima differenza, non gestiva tutti i casi. Da rivalutare se serve con design migliore (ritorno strutturato) |
| `copy()` | Deprecato. L'originale delegava a `copy.copy()` che faceva shallow copy (bug: nodi condivisi). Usa `deepcopy()` |
| `filter()` | Non portato. Nessun uso trovato nel codebase. Per filtrare usare `get_nodes(condition)` o `digest(condition=...)` |

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

### sort

**Originale:**
- Parametro `pars` (stringa o callable)
- Modes: `a`, `asc`, `>` per ascending; altri per descending
- Sempre case-insensitive per label

**Nuovo:**
- Parametro rinominato `key`
- Modes semplificati con controllo case sensitivity:
  - `a`: ascending case-insensitive (default)
  - `A`: ascending case-sensitive
  - `d`: descending case-insensitive
  - `D`: descending case-sensitive
- I vecchi modes (`asc`, `desc`, `>`) non sono più supportati

### sum

**Nuovo parametro:**

- `condition`: filtro opzionale (callable che riceve BagNode e ritorna bool)
- Permette di sommare solo i nodi che soddisfano la condizione
- Esempio: `bag.sum('#v', condition=lambda n: n.get_attr('active'))`

---

## Parametri Rinominati

| Metodo | Parametro Originale | Parametro Nuovo |
|--------|---------------------|-----------------|
| `set_item` | `_removeNullAttributes` | `_remove_null_attributes` |
| `digest` | `asColumns` | `as_columns` |
| `columns` | `attrMode` | `attr_mode` |
| `get_node` | `asTuple` | `as_tuple` |
| `sort` | `pars` | `key` |

---

## Nuovo Parametro `static` per Resolver

La nuova Bag introduce il parametro `static` nei metodi `get_node` e `get_item`:

- `static=False` (default): durante la navigazione, i resolver vengono triggerati se presenti
- `static=True`: i resolver NON vengono triggerati, si ottiene il valore "statico"

**Nota importante**: il default è `False` per compatibilità con il comportamento originale, ma in contesti sync è consigliabile usare `static=True` per evitare problemi con resolver async.

I metodi sync come `set_attr`, `get_attr`, `del_attr` usano internamente `static=True`.

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

---

## Serializzazione XML: to_xml

### Parametri Rimossi

| Parametro Originale | Comportamento Nuovo |
|---------------------|---------------------|
| `typeattrs` | Incluso in `typed` |
| `typevalue` | Incluso in `typed` |
| `addBagTypeAttr` | Incluso in `typed` |
| `omitRoot` | Incluso in `typed` (inverso) |
| `omitUnknownTypes` | Sempre omette (comportamento `True`) |
| `unresolved` | Sempre unresolved (comportamento `True`) |
| `autocreate` | Sempre autocreate (comportamento `True`) |
| `self_closed_tags` | Incluso in `html` |
| `forcedTagAttr` | Incluso in `html` (usa `tag` attribute) |
| `output_encoding` | Rimosso (caso raro, gestire prima) |
| `catalog` | Usa `genro_tytx` internamente |
| `mode4d` | Rimosso (obsoleto) |

### Nuovo Parametro `typed`

Il parametro `typed: bool = True` unifica il comportamento dei tipi:

**`typed=True`** (default, formato Genropy):
- Preserva tipi su valori e attributi
- Marca i nodi Bag con tipo
- Wrappa in root element (`<GenRoBag>`)

**`typed=False`** (XML puro):
- Nessuna informazione di tipo
- No wrapper root
- Output XML generico

**Mapping da originale:**
```python
# Originale
toXml(typeattrs=True, typevalue=True, addBagTypeAttr=True, omitRoot=False)
# Nuovo equivalente
to_xml(typed=True)

# Originale
toXml(typeattrs=False, typevalue=False, addBagTypeAttr=False, omitRoot=True)
# Nuovo equivalente
to_xml(typed=False)
```

### Nuovo Parametro `html`

Il parametro `html: bool = False` attiva la modalità HTML:

**`html=True`**:
- Usa attributo `tag` come nome tag XML (ex `forcedTagAttr='tag'`)
- Auto-chiude solo void elements HTML (`br`, `img`, `meta`, `hr`, `input`, `link`, etc.)
- Implica `typed=False`

**`html=False`** (default, XML):
- Usa label come nome tag
- Auto-chiude tutti i tag vuoti (`<tag/>`)

**Auto-detect da filename**: Se `filename` termina con `.html` o `.htm`, `html=True` viene attivato automaticamente.

**Mapping da originale:**
```python
# Originale (HTML)
toXml(omitRoot=True, forcedTagAttr='tag', addBagTypeAttr=False,
      typeattrs=False, self_closed_tags=['meta', 'br', 'img'])
# Nuovo equivalente
to_xml(html=True)
# oppure
to_xml(filename='page.html')  # auto-detect
```

### Signature Completa

```python
def to_xml(
    bag: Bag,
    filename: str | None = None,
    encoding: str = "UTF-8",
    # Typing
    typed: bool = True,        # tipi + root wrapper
    legacy: bool = False,      # _T attr vs ::TYPE suffix
    # Structure
    root_tag: str = "GenRoBag",
    doc_header: bool | str | None = None,
    # Formatting
    pretty: bool = False,
    html: bool = False,        # HTML mode (auto-detect da filename)
    # Callbacks
    translate_cb: Callable[[str], str] | None = None,
) -> str | None:
```

### Esempi di Migrazione

```python
# Originale: serializzazione standard
bag.toXml()
# Nuovo
to_xml(bag)

# Originale: XML senza tipi
bag.toXml(typeattrs=False, typevalue=False)
# Nuovo
to_xml(bag, typed=False)

# Originale: legacy format con _T
bag.toXml()  # default originale usava _T
# Nuovo
to_xml(bag, legacy=True)

# Originale: HTML output
bag.toXml(omitRoot=True, forcedTagAttr='tag', addBagTypeAttr=False,
          typeattrs=False, self_closed_tags=['meta', 'br', 'img'])
# Nuovo
to_xml(bag, html=True)

# Originale: salva su file con autocreate
bag.toXml('/path/to/file.xml', autocreate=True)
# Nuovo (autocreate sempre attivo)
to_xml(bag, filename='/path/to/file.xml')
```

---

## Deserializzazione XML: from_xml

### Parametri Rimossi

| Parametro Originale | Comportamento Nuovo |
|---------------------|---------------------|
| `catalog` | Usa `genro_tytx` internamente |
| `bagcls` | Rimosso (usa sempre `Bag`) |
| `avoidDupLabel` | Sempre attivo (la nuova Bag non ammette duplicati) |

### Gestione Label Duplicate

La nuova Bag **non supporta label duplicate**. Quando `from_xml` incontra tag con lo stesso nome, aggiunge automaticamente suffissi:

```xml
<root>
    <item>a</item>
    <item>b</item>
    <item>c</item>
</root>
```

Risultato: labels `item`, `item_1`, `item_2`

Questo comportamento era opzionale nell'originale (`avoidDupLabel=True`), ora è **sempre attivo**.

### Auto-detect Legacy Mode

Quando `legacy=None` (default), `from_xml` analizza l'XML per determinare il formato:
- Se trova attributi `_T` o `T` → modo legacy
- Altrimenti → prova TYTX suffix (`::TYPE`)

### Parametro `attr_in_value`

Con `attr_in_value=True`, gli attributi XML vengono memorizzati come dati strutturati invece che come attributi del nodo:

```xml
<item id="123" name="test">content</item>
```

- `attr_in_value=False` (default): `bag['item']` = `'content'`, attributi in `node.attr`
- `attr_in_value=True`: `bag['item']` = `Bag({'__attributes': Bag({'id': '123', 'name': 'test'}), '__content': 'content'})`

### Signature Completa

```python
def from_xml(
    source: str | bytes,
    # Type decoding
    typed: bool = True,
    legacy: bool | None = None,  # None=auto-detect
    # Parsing options
    empty: Callable[[], Any] | None = None,
    attr_in_value: bool = False,
) -> Bag:
```

### Esempi di Migrazione

```python
# Originale: parsing standard
bag.fromXml('<root><item>value</item></root>')
# Nuovo
bag = from_xml('<root><item>value</item></root>')

# Originale: con factory per valori vuoti
bag.fromXml(xml_string, empty=lambda: '')
# Nuovo
bag = from_xml(xml_string, empty=lambda: '')

# Originale: con gestione duplicati
bag.fromXml(xml_string, avoidDupLabel=True)
# Nuovo (sempre attivo)
bag = from_xml(xml_string)

# Originale: forza legacy mode
bag.fromXml(xml_string, catalog=gnrclasses.GnrClassCatalog())
# Nuovo
bag = from_xml(xml_string, legacy=True)
```
