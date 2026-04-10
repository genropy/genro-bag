# genro-bag Analysis Report

**Obiettivo**: Valutare se `genro-bag` possa sostituire `gnr.core.gnrbag`, fungendo da base su cui
`gnr.core.gnrbag` si rimappa come sottoclasse adattativa (`from genro_bag import Bag` → sottoclasse
con alias camelCase e metodi mancanti).

**Data**: 2026-04-08
**Versioni**: genro-bag 0.15.0, genro-tytx 0.8.0

---

**sorgenti**:

/Users/fporcari/Development/genro-ng/meta-genro-modules/sub-projects/genro-bag
/Users/fporcari/Development/genro-ng/meta-genro-modules/sub-projects/genro-tytx
/Users/fporcari/Development/genropy/gnrpy/gnr/core

## 1. Stato di salute

| Metrica | Valore |
|---------|--------|
| Test totali | 1594 (1550 pass, 44 network deselected) |
| Test falliti | 0 |
| Copertura | ~83% |
| Source LOC | ~6,500 |
| Test LOC | ~11,750 |
| Dipendenze | genro-toolbox >=0.6.1, genro-tytx >=0.1.0 |

---

## 2. Architettura a confronto

| Aspetto | gnr.core.gnrbag | genro-bag |
|---------|----------------|-----------|
| Struttura | Monolitico, 3380 LOC, 1 file | Modulare, 7 mixin, ~3100 LOC, 12 file |
| Classi nel modulo | 21 | 5 core + 9 resolver separati |
| Type hints | Zero | Completi (PEP 561) |
| Async | No | Si (via genro_toolbox smartasync) |
| Naming | camelCase | snake_case |
| `__slots__` | No | Si (BagNode) |
| Duplicate labels | Permessi | **NON permessi** |

---

## 3. Problemi trovati in genro-bag

### 3.1 Critici

**Nessun logging** — Zero `import logging` nel codice sorgente. `_background_load()` nel resolver
fa `except Exception: pass` (resolver.py:437-438). In produzione impossibile diagnosticare.

**Exception silenziate**:

| File | Riga | Problema |
|------|------|----------|
| resolver.py | 437-438 | `except Exception: pass` in `_background_load()` |
| bagnode.py | 142-143 | `except Exception: return False` in `__eq__()` |
| _serialize.py | 93 | `except Exception:` nel pretty-print XML |
| _parse.py | 347, 367 | `except Exception:` nella decodifica TYTX |

### 3.2 Medi

**Violazioni coding rules**:

- 6 `@classmethod` (parse.py:4, populate.py:1, resolver.py:1)
- 2 `@staticmethod` (serialize.py:2)
- `RETRY_POLICIES` dict globale mutabile (resolver.py:44-66)
- 68 `# type: ignore` distribuiti su 9 file

**Codice duplicato**: sync_wrapper e async_wrapper in retry decorator (resolver.py:89-149)
quasi identici — differenza solo `time.sleep` vs `asyncio.sleep`.

### 3.3 Bassi

- File test obsoleti: `_old_test_bag_node.py`, `_old_test_bagnode_container.py`
- Directory vuota `builders/xsd/`
- `__ne__` ridondante in bagnode.py (Python 3.10+ lo deriva da `__eq__`)
- `__future__` annotations mancanti in 4 `__init__.py`

---

## 4. API gap: cosa manca in genro-bag

### 4.1 Metodi mancanti — criticita ALTA

| Metodo originale | Descrizione | Note |
|-----------------|-------------|------|
| `child()` / `rowchild()` | Factory per sotto-bag con tag | Usati pesantemente in Genropy |
| `merge()` | Merge di due Bag con opzioni upd/add | Usato in configurazioni |
| `copy()` / `deepcopy()` | Copia della Bag | Usato ovunque |

### 4.2 Metodi mancanti — criticita MEDIA

| Metodo originale | Descrizione |
|-----------------|-------------|
| `formula()` / `defineFormula()` / `defineSymbol()` | Sistema formule (BagFormula) |
| `addValidator()` / `removeValidator()` (su Bag) | Validazione — presente su BagNode ma non su Bag |
| `toTree()` | Raggruppamento gerarchico |
| `nodesByAttr()` / `findNodeByAttr()` | Ricerca per attributo con mode |

### 4.3 Metodi mancanti — criticita BASSA

| Metodo | Note |
|--------|------|
| `addItem()` | set_item copre il caso |
| `pickle()` / `unpickle()` | **getstate** c'e |
| `traverse()` | walk() copre |
| `getDeepestNode()` / `getLeaves()` / `getIndex()` | Poco usati |
| `fromYaml()` | Raramente usato |
| `__pow__()` | Quasi mai usato |
| `asString()` / `summarizeAttributes()` / `popAttributesFromNodes()` | Marginali |

### 4.4 Classi mancanti

| Classe | Criticita | Note |
|--------|-----------|------|
| BagFormula | Media | Mini-linguaggio di formule |
| BagValidationList | Media | Container validatori |
| VObjectBag / GeoCoderBag | Bassa | Quasi mai usate |
| NetBag / XmlDocResolver / TraceBackResolver | Bassa | UrlResolver copre |

---

## 5. Differenza critica: Duplicate Labels

`gnr.core.gnrbag` permette label duplicate. `genro-bag` **NO** (documentato in _core.py:65).

**Da verificare**: quante volte il codice Genropy crea effettivamente nodi con label duplicati.
Se il pattern e diffuso, e un **showstopper** per la sostituzione diretta.

---

## 6. Nuove funzionalita in genro-bag

| Feature | Descrizione |
|---------|-------------|
| Retry policies | 3 policy predefinite con backoff esponenziale |
| Active cache | Background refresh con timer (cache_time < 0) |
| TYTX format | Formato nativo Genropy per serializzazione tipizzata |
| Async support | Pieno async/await tramite genro_toolbox |
| OpenAPI resolver | Caricamento spec OpenAPI |
| node_tag / xml_tag | Distinzione tra tag semantico e tag XML |
| node_class | Factory class configurabile per sottoclassi |
| query() | Deep traversal e pattern avanzati |
| relative_path() | Calcolo path relativo tra nodi |
| `__slots__` | Ottimizzazione memoria su BagNode |

---

## 7. Strategia di rimappatura

### Approccio

```python
# gnr/core/gnrbag.py (nuovo)
from genro_bag import Bag as BaseBag

class Bag(BaseBag):
    """Backward-compatible Bag wrapping genro-bag."""

    # Alias camelCase -> snake_case
    getItem = BaseBag.get_item
    setItem = BaseBag.set_item
    getAttr = BaseBag.get_attr
    setAttr = BaseBag.set_attr
    # ... etc

    # Metodi mancanti
    def child(self, tag, childname, childcontent, **kwargs):
        ...

    def merge(self, otherbag, upd_values=True, add_values=True):
        ...
```

### Fattibilita

| Aspetto | Difficolta | Note |
|---------|-----------|------|
| Alias camelCase | Facile | Puro mapping |
| copy/deepcopy | Facile | Poche righe |
| child() / rowchild() | Media | Implementazione specifica |
| merge() | Media | Logica complessa nell'originale |
| Formula system | Complessa | Mini-linguaggio |
| Duplicate labels | **BLOCCANTE** | Richiede modifica in genro-bag core |

---

## 8. Piano di azione

### Fase 1 — Pulizia genro-bag

- [ ] Fix exception silenziate
- [ ] Aggiungere logging
- [ ] Rimuovere test obsoleti
- [ ] Rimuovere directory vuota builders/xsd/
- [ ] Allineare versione installata

### Fase 2 — Gap analysis su codebase Genropy

- [ ] Contare uso di child(), merge(), copy() nel codebase
- [ ] Verificare uso reale dei duplicate labels
- [ ] Mappare differenze comportamentali sottili

### Fase 3 — Prototipo wrapper (in replacement/)

- [ ] gnrbag.py: Bag come sottoclasse di genro_bag.Bag
- [ ] Alias camelCase
- [ ] Metodi mancanti critici
- [ ] Far girare test gnr.core.gnrbag originali

### Fase 4 — Test di integrazione

- [ ] Usare wrapper in app Genropy reale
- [ ] Monitorare differenze
- [ ] Iterare

---

## 9. File di riferimento

| File | Percorso | Cosa guardare |
|------|----------|--------------|
| Bag core | genro-bag/src/genro_bag/bag/_core.py | Classe principale, set_item/get_item |
| BagNode | genro-bag/src/genro_bag/bagnode.py | Exception silenziata in **eq** |
| Resolver | genro-bag/src/genro_bag/resolver.py | _background_load silente, retry duplicato |
| Parser | genro-bag/src/genro_bag/bag/_parse.py | from_xml, @classmethod factory |
| Serializer | genro-bag/src/genro_bag/bag/_serialize.py | to_xml, pretty-print workaround |
| Events | genro-bag/src/genro_bag/bag/_events.py | Propagazione eventi |
| Query | genro-bag/src/genro_bag/bag/_query.py | query(), walk(), digest() |
| Originale | gnr.core/gnrbag.py | API completa, 3380 LOC |
| Originale XML | gnr.core/gnrbagxml.py | Serializzazione XML separata |
