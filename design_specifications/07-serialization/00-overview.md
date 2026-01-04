# Serialization Overview

**Version**: 0.2.0
**Last Updated**: 2026-01-04
**Status**: 🟡 APPROVATO PARZIALMENTE - Architettura approvata, dettagli implementativi da revisionare

---

## Decisioni Architetturali (2026-01-04)

### 1. Separazione XML Puro vs TYTX

**Decisione**: `to_xml` e `from_xml` saranno metodi XML **puri**, non per interscambio nell'ecosistema Genropy.

| Metodo | Scopo | Ecosistema |
|--------|-------|------------|
| `to_xml()` / `from_xml()` | XML standard, nessuna magia | Esterno (interoperabilità) |
| `to_json()` / `from_json()` | JSON standard, nessuna magia | Esterno (interoperabilità) |
| `flattener()` | Generator di nodi appiattiti | Interno (pipeline) |
| `to_tytx()` / `from_tytx()` | Serializzazione type-preserving | Interno (Genropy) |

### 2. Pipeline Composabile con Iteratori

```
┌─────────────────────────────────────────────────────────────────┐
│                        BAG                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                       ┌──────────┐
                       │ flattener│  ← Generator di tuple
                       └──────────┘
                              │
                              ▼
                   ┌─────────────────┐
                   │   Iteratori     │
                   │   Composabili   │
                   └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │Localizer │   │  Filter  │   │  Altri   │
        └──────────┘   └──────────┘   └──────────┘
                              │
                              ▼
                   ┌─────────────────┐
                   │   Serializer    │
                   │   (TYTX, ...)   │
                   └─────────────────┘
```

### 3. Tipo `::X` per Bag in TYTX

**Decisione**: La Bag viene serializzata con suffix `::X` in TYTX.

```python
# Bag come root
to_tytx(mia_bag)
# → '[["", "name", null, "test", {}], ...]::X'

# Bag dentro una struttura
to_tytx([33, mia_bag, 'kk'])
# → '[33, "[[...]]::X", "kk"]::JS'
```

**Marker `::X`**:
- Indica "questo è una Bag serializzata come flattened JSON"
- I valori dentro le tuple usano suffissi TYTX (`::L`, `::D`, etc.)
- `"::X"` come valore indica "questo nodo è una Bag (branch)"

### 4. Hook Registration in genro-tytx

**Issue GitHub**: [genro-tytx#31 - Add custom type registration hooks](https://github.com/genropy/genro-tytx/issues/31)

Per evitare dipendenze circolari (tytx → bag), genro-tytx fornirà un meccanismo di hook registration:

```python
# In genro-tytx
def register_type(
    cls: type,
    suffix: str,
    serializer: Callable[[Any], str],
    deserializer: Callable[[str], Any]
) -> None:
    """Register a custom type for TYTX serialization."""

# In genro-bag (all'import)
from genro_tytx import register_type

register_type(Bag, "X", _serialize_bag, _deserialize_bag)
```

### 5. Niente `is_branch` - Tipo Esplicito

**Decisione**: Non usare `is_branch` come concetto. Il tipo è esplicito:

```python
# Nel flattener
if isinstance(node.value, Bag):
    yield (parent, label, tag, "::X", attr)  # Branch
else:
    yield (parent, label, tag, to_tytx_value(node.value), attr)  # Leaf
```

La ricostruzione è univoca:
- `"::X"` → crea Bag, i figli arriveranno dopo
- `None` → valore None scalare
- `"valore::SUFFIX"` → decodifica con TYTX
- `"stringa"` → stringa pura

### 6. Nome Metodo: `flattener` (non `flattened`)

**Decisione**: Usare `flattener()` come nome del metodo generator.

---

## Strategia di Serializzazione

### Formato Primario: TYTX

**genro-bag** userà **TYTX** come formato primario di serializzazione per l'ecosistema Genropy.

TYTX (Type-preserving Transfer) preserva i tipi Python nativi:

- `Decimal` → rimane `Decimal` (non float)
- `date`, `datetime`, `time` → preservati
- `Bag` → serializzata come `::X`
- `None`, `bool`, `int`, `float`, `str` → preservati

### Perché TYTX

| Aspetto | XML Legacy | JSON Standard | TYTX |
|---------|------------|---------------|------|
| Type preservation | ❌ Tutto stringa | ❌ Perde Decimal, date | ✅ Completo |
| Bag support | Via gnrbagxml | ❌ No | ✅ Tipo ::X |
| Parsing | Lento | Veloce | Veloce |
| Dimensione | Grande | Media | Compatta |
| Human readable | ✅ | ✅ | ✅ (JSON) |
| Binary option | ❌ | ❌ | ✅ (MessagePack) |

### Metodi Core (genro-bag)

| Metodo | Descrizione |
|--------|-------------|
| `bag.to_tytx(transport='json')` | Serializza in JSON TYTX con `::X` |
| `bag.to_tytx(transport='msgpack')` | Serializza in MessagePack binario |
| `Bag.from_tytx(data)` | Deserializza da TYTX |
| `bag.flattener()` | Generatore di tuple per serializzazione |
| `bag.walk()` | Traversal depth-first |
| `bag.to_xml()` | XML puro standard |
| `bag.to_json()` | JSON puro standard |

### Metodi XML/JSON Puri

Questi metodi sono per **interoperabilità esterna**, non per ecosistema Genropy:

```python
# XML puro - senza tipi TYTX
bag.to_xml()
# → '<root><name>test</name><count>42</count></root>'

# JSON puro - senza tipi TYTX
bag.to_json()
# → '{"name": "test", "count": 42}'
```

---

## Architettura Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Code                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   bag.to_tytx()                     bag.to_xml() (puro)         │
│        │                                 │                       │
│        ▼                                 ▼                       │
│   ┌──────────────┐                 ┌──────────────┐             │
│   │  flattener() │                 │  XML Writer  │             │
│   └──────┬───────┘                 │  (standard)  │             │
│          │                         └──────────────┘             │
│          ▼                                                       │
│   ┌──────────────┐                                              │
│   │  Localizer   │  ← Iteratore opzionale                       │
│   │  (optional)  │                                              │
│   └──────┬───────┘                                              │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────┐                                              │
│   │ TYTX Encoder │  ← Aggiunge suffissi tipo                    │
│   │   + ::X      │                                              │
│   └──────────────┘                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Formato Wire TYTX con ::X

### Bag come Root

```python
bag = Bag()
bag['name'] = 'Giovanni'
bag['age'] = 42

to_tytx(bag)
# → '[["", "name", null, "Giovanni", {}], ["", "age", null, "42::L", {}]]::X'
```

### Bag Nested

```python
bag = Bag()
config = Bag()
config['host'] = 'localhost'
bag['config'] = config

to_tytx(bag)
# → '[["", "config", null, "::X", {}], ["config", "host", null, "localhost", {}]]::X'
#                           ^^^^ branch marker
```

### Bag dentro Struttura Mista

```python
to_tytx([33, bag, 'kk'])
# → '[33, "[...]::X", "kk"]::JS'
#         ^^^^^^^^ Bag serializzata come stringa con ::X
```

---

## Dipendenze

| Package | Uso | Obbligatorio |
|---------|-----|--------------|
| `genro-tytx` | Encoding/decoding TYTX + hook registration | Sì (per to_tytx) |
| `msgpack` | Transport binario | Opzionale |

---

## Riferimenti

- [01-overview.md](01-overview.md) - Dettagli tecnici walk/flattener
- [02-implementation-plan.md](02-implementation-plan.md) - Piano implementazione
- [GitHub Issue #31](https://github.com/genropy/genro-tytx/issues/31) - Hook registration in genro-tytx
- `genro-treestore/store/serialization.py` - Implementazione reference
- `genro-tytx` - Package TYTX
