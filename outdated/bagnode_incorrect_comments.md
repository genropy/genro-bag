# BagNode - Commenti Errati/Inconsistenti con il Codice

## ❌ ERRORE CRITICO #1: getValue() - mode='weak' NON ESISTE

**Linea**: ~195

```python
def getValue(self, mode=''):
    """Return the value of the BagNode. It is called by the property .value
        
    :param mode='static': allow to get the resolver instance instead of the calculated value
    :param mode='weak': allow to get a weak ref stored in the node instead of the actual object"""
```

**CODICE REALE**:
```python
def getValue(self, mode=''):
    if not self._resolver == None:
        if 'static' in mode:  # ✅ Implementato
            return self._value
        # ❌ NON C'È GESTIONE DI 'weak'!
```

**PROBLEMA**: Il docstring documenta `mode='weak'` ma il codice non lo gestisce affatto!

**VERIFICA**: Cerca `'weak'` nel codice → NON TROVATO

**FIX**: Rimuovere completamente la documentazione di 'weak':
```python
:param mode: mode string. If 'static' is in mode, return the raw stored value
             instead of resolving it through a resolver
```

---

## ⚠️ ERRORE #2: getValue() - "resolver instance" è SBAGLIATO

**Docstring dice**:
```python
:param mode='static': allow to get the resolver instance instead of the calculated value
```

**CODICE REALE**:
```python
if 'static' in mode:
    return self._value  # ← Ritorna _value, NON il resolver!
```

**PROBLEMA**: Con mode='static' ritorna `self._value` (il valore statico), NON `self._resolver` (l'istanza del resolver)!

**FIX CORRETTO**:
```python
:param mode: mode string. If 'static' is in mode, return the stored value
             without evaluating the resolver (if present)
```

---

## ⚠️ INCONSISTENZA #3: __eq__() docstring vs implementazione

**Docstring**:
```python
"""One BagNode is equal to another one if its key, value, attributes and resolvers are the same"""
```

**CODICE**:
```python
def __eq__(self, other):
    try:
        if isinstance(other, self.__class__) and (self.attr == other.attr):
            if self._resolver == None:
                return self._value == other._value  # ✅ Confronta value
            else:
                return self._resolver == other._resolver  # ✅ Confronta resolver
        else:
            return False
    except:
        return False  # ❌ Cattura TUTTE le eccezioni silenziosamente!
```

**PROBLEMA**: 
1. Il docstring dice "key" ma dovrebbe dire "label"
2. Il `try/except` cattura TUTTO senza logging - comportamento non documentato

**FIX**:
```python
"""Two BagNodes are equal if they have the same:
- class type
- label  
- attributes
- value (if no resolver) or resolver instance (if resolver present)

Note: Returns False if any comparison raises an exception."""
```

---

## 🤔 DUBBIO #4: _set_parentbag() - Commentato misterioso

**Linea**: ~150

```python
def _get_parentbag(self):
    return self._parentbag
        #return self._parentbag()  # ← Commentato, era weakref?
```

**E anche**:
```python
def _set_parentbag(self, parentbag):
    self._parentbag = None
    if parentbag != None:
        if parentbag.backref or True:  # ← "or True" rende la condizione inutile!
            #self._parentbag=weakref.ref(parentbag)  # ← Era weakref prima
            self._parentbag = parentbag
```

**PROBLEMA**: 
1. Codice commentato suggerisce che prima usava `weakref`
2. `if parentbag.backref or True:` è sempre True → condizione inutile!
3. Nessuna spiegazione del PERCHÉ è stato cambiato

**SUGGERIMENTO**: 
- O rimuovere i commenti
- O documentare perché si è passati da weakref a riferimento diretto

---

## ⚠️ ERRORE #5: setAttr() - Codice locked commentato senza spiegazione

**Linea**: ~345

```python
def setAttr(self, attr=None, trigger=True, _updattr=True, ...):
    if not _updattr:
        self.attr.clear()
        #if self.locked:
        #raise BagNodeException("Locked node %s" % self.label)
```

**PROBLEMA**: 
- `setValue()` CHECK il lock → `if self.locked: raise BagNodeException(...)`
- `setAttr()` NON check il lock (codice commentato)

**INCONSISTENZA**: Perché setValue può bloccare ma setAttr no?

**DOMANDA**: È intenzionale o è un bug nascosto?

---

## 📝 PROBLEMA #6: _index() mismatch nel commento

Nel file Bag (correlato):

**Docstring dice**:
```python
"""The mach is not case sensitive"""  # ← Typo: "mach" invece di "match"
```

**CODICE REALE**:
```python
for idx, el in enumerate(self._nodes):
    if el.label == label:  # ← Case SENSITIVE! (==, non .lower())
        result = idx
        break
```

**PROBLEMA**: Il commento dice "not case sensitive" ma il codice USA `==` che È case sensitive!

---

## 🔍 ALTRI PROBLEMI MINORI

### 7. Inconsistenza nome "key" vs "label"

Molti docstring usano "key" ma dovrebbe essere "label":
- `__eq__`: "its key, value..." → dovrebbe essere "its label, value..."
- BagNode usa sempre `label`, non `key`

### 8. setValue() - Commento fuorviante su deferred

**Linea**: ~240 (circa)
```python
newcurrnode = curr._nodes[i]
newcurr = newcurrnode.value #maybe a deferred
# if deferred : 
#return deferred.addcallback(this.getItem(path rimanente))
```

**PROBLEMA**: Commento su "deferred" ma non c'è gestione dei deferred nel codice!

---

## 📊 RIEPILOGO ERRORI

| # | Tipo | Gravità | Linea | Problema |
|---|------|---------|-------|----------|
| 1 | Parametro inesistente | 🔴 ALTA | ~195 | mode='weak' documentato ma non implementato |
| 2 | Descrizione sbagliata | 🔴 ALTA | ~195 | mode='static' non ritorna il resolver |
| 3 | Terminologia | 🟡 MEDIA | ~130 | "key" invece di "label" |
| 4 | Comportamento non doc. | 🟡 MEDIA | ~130 | try/except cattura tutto silenziosamente |
| 5 | Codice morto | 🟡 MEDIA | ~150 | weakref commentato senza spiegazione |
| 6 | Condizione inutile | 🟡 MEDIA | ~155 | `or True` rende check inutile |
| 7 | Inconsistenza | 🟠 BASSA | ~345 | locked check presente in setValue ma non in setAttr |
| 8 | Typo + errore | 🟡 MEDIA | Bag | "not case sensitive" ma codice È case sensitive |

---

## 🎯 AZIONI CORRETTIVE

### Priorità 1 - Fix Immediati
- [ ] Rimuovere mode='weak' da getValue docstring
- [ ] Correggere descrizione mode='static' 
- [ ] Decidere su gestione locked in setAttr

### Priorità 2 - Pulizia
- [ ] Rimuovere tutti i commenti su weakref O documentare il cambio
- [ ] Rimuovere `or True` dalla condizione parentbag
- [ ] Standardizzare "label" (non "key") ovunque

### Priorità 3 - Miglioramenti
- [ ] Documentare comportamento try/except in __eq__
- [ ] Rimuovere commenti su deferred se non implementato
