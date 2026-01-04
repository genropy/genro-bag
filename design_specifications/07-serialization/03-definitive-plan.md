# Piano Definitivo Serializzazione

**Version**: 1.1.0
**Last Updated**: 2026-01-04
**Status**: 🟡 APPROVATO PARZIALMENTE - Signature to_xml approvata

---

## Architettura Finale

### Due Famiglie di Funzioni

| Famiglia | Funzioni | Scopo | Estensioni |
|----------|----------|-------|------------|
| **TYTX** | `to_tytx`, `from_tytx` | Serializzazione Bag type-preserving (ecosistema Genropy) | `.bag.json`, `.bag.mp` |
| **XML** | `to_xml`, `from_xml` | XML generico + legacy GenRoBag | `.xml` |

### Decisione Chiave: NO XML in TYTX

**TYTX usa solo trasporti JSON e MessagePack**, non XML.

Motivazione:
- XML ha già il suo formato legacy (GenRoBag con `_T`)
- TYTX è pensato per efficienza e compattezza
- Evita confusione tra "XML TYTX" e "XML legacy"

---

## Famiglia TYTX

### `to_tytx(bag, transport, filename, compact)` ✅ IMPLEMENTATO

Serializza Bag in formato TYTX con type-preservation.

```python
def to_tytx(
    bag: Bag,
    transport: Literal["json", "msgpack"] = "json",
    filename: str | None = None,
    compact: bool = False,
) -> str | bytes | None:
```

**Trasporti:**
- `"json"` → JSON string, estensione `.bag.json`
- `"msgpack"` → bytes binari, estensione `.bag.mp`

**Formato wire:**
```json
{"rows": [["parent", "label", "tag", "value", {"attr": "val"}], ...]}
```

**Marker speciali:**
- `"::X"` → nodo Bag (branch)
- `"::NN"` → None
- `"42::L"`, `"2025-01-04::D"`, etc. → tipi TYTX

### `from_tytx(data, transport)` ✅ IMPLEMENTATO

Deserializza da formato TYTX.

```python
def from_tytx(
    data: str | bytes,
    transport: Literal["json", "msgpack"] = "json",
) -> Bag:
```

---

## Famiglia XML

### `to_xml(bag, ...)` ✅ SIGNATURE DEFINITA

Serializza Bag in XML. Supporta sia export generico che formato legacy GenRoBag.

```python
def to_xml(
    bag: Bag,
    filename: str | None = None,
    encoding: str = "UTF-8",
    # Typing
    typed: bool = True,        # tipi + root wrapper (True=Genropy, False=XML puro)
    legacy: bool = False,      # _T attr vs ::TYPE suffix
    # Structure
    root_tag: str = "GenRoBag",
    doc_header: bool | str | None = None,
    # Formatting
    pretty: bool = False,
    html: bool = False,        # HTML void elements handling (auto-detect da filename)
    # Callbacks
    translate_cb: Callable[[str], str] | None = None,
) -> str | None:
```

**Parametri chiave:**

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `typed` | `True` | `True`: tipi su valori/attributi, `<GenRoBag>` wrapper. `False`: XML puro |
| `legacy` | `False` | `True`: usa `_T` attribute. `False`: usa TYTX suffix |
| `root_tag` | `"GenRoBag"` | Nome tag root (usato solo se `typed=True`) |
| `doc_header` | `None` | `True`=auto, `str`=custom, `None/False`=niente |
| `pretty` | `False` | Indentazione |
| `html` | `False` | `True`: usa attr `tag` come nome tag, auto-chiude solo void elements HTML. Auto-detect da filename `.html`/`.htm` |
| `translate_cb` | `None` | Callback per traduzione valori |

**Comportamenti sempre attivi (parametri rimossi):**
- `unresolved=True` → sempre serializza senza risolvere resolver
- `autocreate=True` → sempre crea directory per filename
- `omitUnknownTypes=True` → sempre omette tipi sconosciuti

**Parametro `typed` controlla:**
- `typed=True`: `typeattrs=True`, `typevalue=True`, `addBagTypeAttr=True`, `omitRoot=False`
- `typed=False`: `typeattrs=False`, `typevalue=False`, `addBagTypeAttr=False`, `omitRoot=True`

**Parametro `html` controlla:**
- `html=False` (XML): usa label come tag, auto-chiude tutti i tag vuoti (`<tag/>`)
- `html=True` (HTML): usa attributo `tag` come nome tag, auto-chiude solo void elements (`br`, `img`, `meta`, `hr`, `input`, `link`, etc.). Implica `typed=False`.
- **Auto-detect**: se `filename` termina con `.html` o `.htm`, `html=True` automaticamente

**Parametri rimossi (rispetto all'originale):**
- `typeattrs`, `typevalue`, `addBagTypeAttr`, `omitRoot` → fusi in `typed`
- `self_closed_tags`, `forcedTagAttr` → fusi in `html`
- `unresolved` → sempre `True`
- `autocreate` → sempre `True`
- `omitUnknownTypes` → sempre `True` (omette tipi sconosciuti)
- `output_encoding` → rimosso (caso raro)
- `catalog` → usa genro_tytx
- `mode4d` → rimosso (obsoleto)

**Esempi output:**

```python
bag = Bag()
bag['name'] = 'test'
bag['count'] = 42

# Default Genropy (typed=True)
to_xml(bag)
# → '<GenRoBag><name>test</name><count>42::L</count></GenRoBag>'

# Legacy mode (attributo _T)
to_xml(bag, legacy=True)
# → '<GenRoBag><name>test</name><count _T="L">42</count></GenRoBag>'

# XML puro (typed=False)
to_xml(bag, typed=False)
# → '<name>test</name><count>42</count>'

# HTML mode
to_xml(bag, typed=False, html=True)
# → '<div></div><br/>'  # div non auto-chiuso, br sì
```

### `from_xml(source, ...)` ✅ SIGNATURE DEFINITA

Deserializza XML in Bag. Gestisce sia XML generico che formato legacy.

```python
def from_xml(
    source: str | bytes,
    # Type decoding
    typed: bool = True,
    legacy: bool | None = None,
    # Parsing options
    empty: Callable[[], Any] | None = None,
    attr_in_value: bool = False,
) -> Bag:
```

**Parametri chiave:**

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `typed` | `True` | Decodifica informazioni tipo |
| `legacy` | `None` | `None`=auto-detect, `True`=forza legacy, `False`=forza TYTX |
| `empty` | `None` | Factory per valori vuoti |
| `attr_in_value` | `False` | Se `True`, attributi in `__attributes` sub-Bag invece di `node.attr` |

**Parametri rimossi (rispetto all'originale):**
- `catalog` → usa `genro_tytx` internamente
- `bagcls` → usa sempre `Bag`
- `avoidDupLabel` → sempre attivo (la nuova Bag non ammette duplicati)

**Gestione duplicati (SEMPRE attiva):**

La nuova Bag non supporta label duplicate. `from_xml` aggiunge automaticamente suffissi:

```xml
<root>
    <item>a</item>
    <item>b</item>
    <item>c</item>
</root>
```

→ Labels: `item`, `item_1`, `item_2`

**Auto-detect legacy:**

Quando `legacy=None`, `from_xml` analizza l'XML:
- Se trova attributi `_T` o `T` → modo legacy
- Altrimenti → prova TYTX suffix

---

## Dettagli Implementazione `to_xml`

### Sanitize Tag XML

**SEMPRE attivo** in `to_xml`, non opzionale.

I nomi tag XML hanno regole rigide:
- Non possono iniziare con numero
- Non possono contenere spazi o caratteri speciali
- Solo lettere, numeri, underscore, punto, trattino

**Algoritmo:**
```python
import re

def _sanitize_xml_tag(tag: str, namespaces: list[str]) -> tuple[str, bool]:
    """Sanitize tag name for XML.

    Args:
        tag: Original tag name
        namespaces: List of active namespace prefixes (e.g., ['soap', 'xsi'])

    Returns:
        (sanitized_tag, was_modified)
    """
    if not tag:
        return '_none_', True

    original = tag

    # Preserve namespace prefix (e.g., "soap:Envelope")
    if ':' in tag:
        prefix = tag.split(':')[0]
        if prefix in namespaces:
            return tag, False  # Keep as-is

    # Replace invalid chars with underscore (keep letters, digits, underscore, dot, hyphen)
    tag = re.sub(r'[^\w.-]', '_', tag, flags=re.ASCII)
    # Replace double underscore with single
    tag = tag.replace('__', '_')
    # Prefix with underscore if starts with digit
    if tag[0].isdigit():
        tag = '_' + tag

    return tag, tag != original
```

**Se modificato:** salva originale in attributo `_tag`:

```python
# Label: "my item" → tag: "my_item", attr: {"_tag": "my item"}
```

**In `from_xml`:** se c'è `_tag`, usa quello come label.

---

### Namespace XML

I namespace si gestiscono tramite **attributi `xmlns:*` sui nodi della Bag**:

```python
bag.set_item('root', Bag(), _attributes={'xmlns:soap': 'http://schemas.xmlsoap.org/soap/envelope/'})
```

**Gestione nel codice:**
- Estrarre namespace attivi dagli attributi: `[k[6:] for k in attr.keys() if k.startswith('xmlns:')]`
- Passare lista namespace ai nodi figli per preservare tag con prefisso
- Non c'è un parametro `namespaces` - vengono letti automaticamente dagli attributi

---

### Tag Speciale `__flatten__`

Se il label di un nodo è `__flatten__`, emette **solo il contenuto** senza tag wrapper:

```python
bag['__flatten__'] = '<custom>xml</custom>'
to_xml(bag, typed=False)
# → '<custom>xml</custom>'  (no <__flatten__> wrapper)
```

Utile per inserire XML raw in una posizione specifica.

---

### Escape Valori e `::HTML` Suffix

**Escape standard** con `xml.sax.saxutils.escape()` per caratteri speciali:
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`

**Eccezione `::HTML`**: Se un valore stringa termina con `::HTML`, il suffix viene rimosso e il contenuto **NON viene escaped**:

```python
bag['content'] = '<b>bold</b>::HTML'
to_xml(bag, typed=False)
# → '<content><b>bold</b></content>'  (no escape, no ::HTML suffix)

bag['content'] = '<b>bold</b>'
to_xml(bag, typed=False)
# → '<content>&lt;b&gt;bold&lt;/b&gt;</content>'  (escaped)
```

---

### Encoding Attributi

Gli attributi del nodo (`node.attr`) diventano attributi XML.

**Quando `typed=True`:**
- Gli attributi usano **sempre** encoding TYTX (suffix nel valore)
- Anche in `legacy=True`, gli attributi hanno suffix TYTX

```python
bag.set_item('item', 'test', size=100, active=True)

# typed=True, legacy=False
to_xml(bag)
# → '<GenRoBag><item size="100::L" active="true::B">test</item></GenRoBag>'

# typed=True, legacy=True
to_xml(bag, legacy=True)
# → '<GenRoBag><item size="100::L" active="true::B">test</item></GenRoBag>'
#   (attributi sempre con suffix, solo il valore usa _T)
```

**Quando `typed=False`:**
- Attributi convertiti a stringa semplice (no suffix)
- Attributi con valore `False` vengono **omessi**

```python
# typed=False
to_xml(bag, typed=False)
# → '<item size="100" active="true">test</item>'
```

**Quote attributi:** Usare `saxutils.quoteattr()` per escape e quote corretti.

---

### Encoding Valore del Nodo

**Quando `typed=True, legacy=False` (TYTX moderno):**
```xml
<count>42::L</count>
<price>19.99::R</price>
<today>2025-01-04::D</today>
```

**Quando `typed=True, legacy=True` (GenRoBag originale):**
```xml
<count _T="L">42</count>
<price _T="R">19.99</price>
<today _T="D">2025-01-04</today>
```

**Quando `typed=False`:**
```xml
<count>42</count>
<price>19.99</price>
<today>2025-01-04</today>
```

---

### Bag Vuota vs Bag con Figli

**Bag con figli:** Il tag contiene i figli, nessun marker tipo:
```xml
<config>
  <host>localhost</host>
  <port>8080::L</port>
</config>
```

**Bag vuota (quando `typed=True`):** Marker tipo per distinguere da stringa vuota:
```python
bag['empty_bag'] = Bag()
bag['empty_string'] = ''

# typed=True, legacy=False
to_xml(bag)
# → '<GenRoBag><empty_bag>::X</empty_bag><empty_string></empty_string></GenRoBag>'

# typed=True, legacy=True
to_xml(bag, legacy=True)
# → '<GenRoBag><empty_bag _T="BAG"></empty_bag><empty_string></empty_string></GenRoBag>'
```

---

### Resolver Serialization

Quando un nodo ha un resolver e non è stato risolto, serializza le info del resolver:

```python
# Se node.resolver esiste e non ha attributo _xmlEager
if node.resolver and not getattr(node.resolver, '_xmlEager', None):
    attr['_resolver'] = json.dumps(node.resolver.serialize())
```

**Nota:** Il resolver non viene triggerato durante la serializzazione (sempre `unresolved=True`).

---

### Filtro Attributi (omitUnknownTypes)

**Sempre attivo.** Gli attributi con tipi non serializzabili vengono omessi:

Tipi ammessi:
- `str`, `bytes`
- `int`, `float`, `Decimal`
- `bool`, `None`
- `date`, `time`, `datetime`
- `list`, `tuple`, `dict`

Callable ammessi solo se hanno attributo `is_rpc`, `__safe__`, o nome che inizia con `rpc_`.

---

## HTML Void Elements

Lista dei void elements HTML (auto-chiusi quando `html=True`):

```python
HTML_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}
```

---

## Funzioni Rimosse

### Rimosse da `to_tytx` / `from_tytx`: ✅ FATTO
- Parametro `transport="xml"` - non più supportato
- Riferimenti a `.bag.xml` extension

### Rimosse: ✅ FATTO
- `to_xml_raw` - logica integrata in `to_xml`
- `from_xml_raw` - logica integrata in `from_xml`

### Mantenute:
- `node_flattener` - helper per TYTX (usa `bag.walk()`)

---

## JSON Serialization

Formato legacy per interoperabilità, usa internamente `genro_tytx` per encoding tipi.

### `to_json(bag, typed, nested)` ⏳ DA IMPLEMENTARE

```python
def to_json(
    bag: Bag,
    typed: bool = True,
    nested: bool = False,
) -> str:
```

### `from_json(source, list_joiner)` ⏳ DA IMPLEMENTARE

```python
def from_json(
    source: str,
    list_joiner: str | None = None,
) -> Bag:
```

---

## Estensioni File

| Estensione | Formato | Funzione |
|------------|---------|----------|
| `.bag.json` | TYTX JSON | `to_tytx(transport='json')` |
| `.bag.mp` | TYTX MessagePack | `to_tytx(transport='msgpack')` |
| `.xml` | XML (generico o legacy) | `to_xml()` |

---

## Dipendenze

| Package | Uso | Obbligatorio |
|---------|-----|--------------|
| `genro-tytx` | Encoding/decoding TYTX | Sì |
| `msgpack` | Transport MessagePack | Opzionale (runtime) |

---

## Piano Implementazione

### Fase 1: Cleanup `to_tytx` / `from_tytx` ✅ COMPLETATO
1. ✅ Rimuovere `transport="xml"` option
2. ✅ Aggiornare docstring e type hints
3. ✅ Rimuovere `to_xml_raw` e `from_xml_raw`

### Fase 2: Implementare `to_xml` ⏳ IN CORSO
1. Creare funzione `sanitize_xml_tag()`
2. Implementare serializzazione con:
   - Sanitize tag sempre
   - `_tag` attribute per tag modificati
   - Type encoding (TYTX suffix o `_T` attribute)
   - Parametro `typed` unificato
   - Parametro `html` per void elements
   - doc_header, pretty, etc.
3. Gestione filename e autocreate

### Fase 3: Implementare `from_xml`
1. Parsing XML con ElementTree
2. Gestione duplicati (counter per label)
3. Recupero label da `_tag` se presente
4. Auto-detect legacy mode
5. Type decoding (TYTX o `_T`)

### Fase 4: Implementare `to_json` / `from_json`

### Fase 5: Cleanup finale
1. Aggiornare docstring modulo
2. Aggiornare `__init__.py` exports

---

## Encoding Tipi Legacy vs TYTX

| Tipo | Legacy (`_T`) | TYTX (suffix) |
|------|---------------|---------------|
| int | `_T="L"` | `::L` |
| float | `_T="R"` | `::R` |
| Decimal | `_T="N"` | `::N` |
| bool | `_T="B"` | `::B` |
| date | `_T="D"` | `::D` |
| datetime | `_T="DT"` | `::DT` |
| time | `_T="H"` | `::H` |
| str | (niente) | (niente) |
| Bag | `_T="BAG"` | `::X` |
| None | (niente) | `::NN` |

---

## Riferimenti

- `gnrbagxml.py` - Implementazione originale legacy
- `genro-tytx` - Package encoding TYTX
- `serialization.py` - Implementazione corrente
