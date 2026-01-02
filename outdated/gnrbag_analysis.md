# Analisi Struttura gnrbag.py

## File Info
- Dimensione: 131 KB
- Linee: ~3000+
- Creato: 2004-2007
- Ultimo aggiornamento: 2025-03-11

## Struttura Generale

### Header e Imports (linee ~1-70)
- Licenza LGPL
- Docstring del modulo
- Import standard library
- Import gnr.core

### Classi Helper (linee ~70-100)
- `AllowMissingDict`
- `BagNodeException`
- `BagException`
- `BagAsXml`
- `BagValidationError`
- `BagDeprecatedCall`

### Classe BagNode (linee ~100-500)
**Metodi principali:**
- `__init__` - Inizializzazione
- `__eq__`, `__ne__` - Confronto
- `getValue/setValue` - Gestione valore
- `getAttr/setAttr` - Gestione attributi
- `resolver` property - Gestione resolver
- `subscribe/unsubscribe` - Sistema eventi

**Punti da verificare:**
- [ ] Docstring completi e accurati
- [ ] Commenti inline dove necessario
- [ ] Gestione resolver chiara
- [ ] Sistema validatori documentato

### Classe Bag (linee ~500-3000+)

#### Inizializzazione e Proprietà (linee ~500-700)
- `__init__`
- Properties: `parent`, `parentNode`, `fullpath`, `attributes`, `modified`, ecc.
- `backref` system

#### Accesso Dati (linee ~700-1000)
- `__contains__`
- `getItem/__getitem__`
- `get`
- `_htraverse` - **METODO CRITICO**
- `__iter__`, `__len__`

#### Modifica Dati (linee ~1000-1300)
- `setItem/__setitem__`
- `addItem`
- `_set` - Metodo interno
- `_insertNode`
- `pop/popNode`
- `clear`
- `update`

#### Utility e Query (linee ~1300-1600)
- `keys`, `values`, `items`
- `digest` - Query avanzate
- `sort`
- `toTree`
- `has_key`
- `getNode`

#### Serializzazione (linee ~1600-2200)
- `toXml` e helper
- `fromXml` e `_fromXml`
- `pickle/unpickle`
- `fromJson/_fromJson`
- `fromYaml/_fromYaml`
- `_sourcePrepare` - Detection formato

#### Traversal e Ricerca (linee ~2200-2500)
- `getIndex/_deepIndex`
- `getNodeByAttr`
- `getDeepestNode`
- `walk`
- `filter`
- `traverse`

#### Eventi e Subscriptions (linee ~2500-2700)
- `subscribe/unsubscribe`
- `_onNodeChanged`
- `_onNodeInserted`
- `_onNodeDeleted`

#### Formule e Resolver (linee ~2700-2900)
- `defineSymbol`
- `defineFormula`
- `formula`
- Sistema formule (DA RIMUOVERE in V2)

#### Utility Finali (linee ~2900-3000+)
- Vari metodi helper
- Conversioni
- Comparazioni

## Problemi Potenziali da Verificare

### Priorità Alta
1. **Docstring mancanti** - Molti metodi hanno "TODO"
2. **Commenti obsoleti** - Riferimenti a versioni vecchie
3. **Codice commentato** - Va rimosso o documentato
4. **Metodi deprecati** - Va segnalato chiaramente

### Priorità Media
5. **Esempi nei docstring** - Alcuni obsoleti o mancanti
6. **Type hints** - Completamente assenti (da aggiungere in V2)
7. **Inconsistenze naming** - Già documentate nel design doc

### Priorità Bassa
8. **Ottimizzazioni** - Commenti su performance
9. **Edge cases** - Comportamenti non documentati

## Prossimi Step

1. ✅ Analisi struttura completata
2. ⏳ Analisi dettagliata BagNode
3. ⏳ Analisi dettagliata Bag.__init__ e properties
4. ⏳ Analisi metodi core (get/set/traverse)
5. ⏳ Analisi serializzazione
6. ⏳ Creazione checklist problemi
7. ⏳ Preparazione PR

## Note per V2

Questi elementi vanno RIMOSSI in V2:
- [ ] Sistema Formule (`defineFormula`, `defineSymbol`, `formula`)
- [ ] Sistema Validatori (BagValidationList)
- [ ] Metodi deprecati marcati

Questi vanno MANTENUTI:
- [x] Sistema Resolver
- [x] Sistema Eventi/Trigger
- [x] Tutte le serializzazioni
- [x] Path traversal
