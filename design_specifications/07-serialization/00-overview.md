# Serialization Overview

**Version**: 0.1.0
**Last Updated**: 2026-01-04
**Status**: 🔴 DA REVISIONARE

---

## Strategia di Serializzazione

### Formato Primario: TYTX

**genro-bag** userà **TYTX** come formato primario di serializzazione.

TYTX (Type-preserving Transfer) è un formato sviluppato internamente che preserva i tipi Python nativi attraverso la serializzazione:

- `Decimal` → rimane `Decimal` (non float)
- `date`, `datetime`, `time` → preservati
- `None`, `bool`, `int`, `float`, `str` → preservati
- Strutture nested → preservate

### Perché TYTX

| Aspetto | XML Legacy | JSON Standard | TYTX |
|---------|------------|---------------|------|
| Type preservation | ❌ Tutto stringa | ❌ Perde Decimal, date | ✅ Completo |
| Parsing | Lento | Veloce | Veloce |
| Dimensione | Grande | Media | Compatta |
| Human readable | ✅ | ✅ | ✅ (JSON) |
| Binary option | ❌ | ❌ | ✅ (MessagePack) |

### Metodi Legacy nel Compatibility Layer

I vecchi metodi di serializzazione XML della Bag originale **non saranno reimplementati** nel core di genro-bag. Resteranno disponibili nel **compatibility layer** per retrocompatibilità:

```
genro-bag (core)           genro-bag-compat (layer)
─────────────────          ──────────────────────────
to_tytx()          ←──     toXml()  → chiama to_tytx() + conversione
from_tytx()        ←──     fromXml() → parsing XML → from_tytx()
                           pickle() → deprecato
                           unpickle() → deprecato
```

### Metodi Core (genro-bag)

| Metodo | Descrizione |
|--------|-------------|
| `bag.to_tytx(transport='json')` | Serializza in JSON TYTX |
| `bag.to_tytx(transport='msgpack')` | Serializza in MessagePack binario |
| `Bag.from_tytx(data)` | Deserializza da TYTX |
| `bag.flattened()` | Generatore di tuple per serializzazione |
| `bag.walk()` | Traversal depth-first |

### Metodi Compatibility Layer (genro-bag-compat)

| Metodo Legacy | Implementazione |
|---------------|-----------------|
| `toXml()` | Wrapper → to_tytx() + XML envelope |
| `fromXml()` | Parse XML → from_tytx() |
| `pickle()` | Deprecato, warning |
| `unpickle()` | Deprecato, warning |
| `as_dict()` | Conversione a dict Python |
| `as_dict_deeply()` | Conversione ricorsiva |

---

## Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    Application Code                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   bag.to_tytx()              bag.toXml()  (compat)     │
│        │                          │                     │
│        ▼                          ▼                     │
│   ┌─────────┐              ┌─────────────┐             │
│   │  TYTX   │◄─────────────│  XML Layer  │             │
│   │ Encoder │              │  (wrapper)  │             │
│   └────┬────┘              └─────────────┘             │
│        │                                                │
│        ▼                                                │
│   ┌─────────────────┐                                  │
│   │  bag.flattened()│  ← Generatore tuple              │
│   └────────┬────────┘                                  │
│            │                                            │
│            ▼                                            │
│   ┌─────────────────┐                                  │
│   │   bag.walk()    │  ← Traversal depth-first         │
│   └─────────────────┘                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Formato Wire TYTX

### Struttura Base

```json
{
  "rows": [
    ["", "config_0", "config", null, {"name": "app"}],
    ["config_0", "db_0", "section", null, {}],
    ["config_0.db_0", "host_0", "setting", "localhost", {}]
  ]
}
```

Ogni riga: `[parent_path, label, tag, value, attributes]`

### Compact Mode

```json
{
  "rows": [
    [null, "config_0", "config", null, {"name": "app"}],
    [0, "db_0", "section", null, {}],
    [1, "host_0", "setting", "localhost", {}]
  ],
  "paths": {"0": "config_0", "1": "config_0.db_0"}
}
```

- `parent` diventa codice numerico
- `paths` mappa codici → path
- ~30% più compatto senza gzip

---

## Dipendenze

| Package | Uso | Obbligatorio |
|---------|-----|--------------|
| `genro-tytx` | Encoding/decoding TYTX | Sì |
| `msgpack` | Transport binario | Opzionale |

---

## Riferimenti

- [01-overview.md](01-overview.md) - Dettagli tecnici walk/flattened
- [02-implementation-plan.md](02-implementation-plan.md) - Piano implementazione
- `genro-treestore/store/serialization.py` - Implementazione reference
- `genro-tytx` - Package TYTX
