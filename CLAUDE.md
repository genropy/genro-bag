# Claude Code Instructions - genro-bag

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## MODO MANUALE

Quando l'utente dice `:modomanuale` o `modo manuale`:

**REGOLA ASSOLUTA**: Fai **SOLO ED ESATTAMENTE** quello che viene chiesto.

- **NON** lanciare i test se non richiesto
- **NON** aggiungere nulla di extra
- **NON** "completare" o "migliorare" nulla
- **NON** anticipare passi successivi
- Lo scopo **NON** è far passare i test
- Lo scopo è **mantenere l'allineamento** per lavorare in modo sinergico
- **Se un test fallisce**: dire SOLO quale test fallisce e perché, poi STOP. Nessuna proposta di soluzione, nessuna analisi aggiuntiva.

Se fai diverso, si perde tempo a riallinearsi.

---

## REGOLA FONDAMENTALE: LE DECISIONI LE PRENDE L'UTENTE

**ESTREMAMENTE IMPORTANTE: MAI prendere decisioni autonome su cosa aggiungere o rimuovere dal codice.**

Questo include:
- Rimuovere codice (anche se sembra "dead code" o non coperto)
- Aggiungere ottimizzazioni
- Semplificare implementazioni
- Cambiare approcci architetturali

**SEMPRE chiedere PRIMA di fare qualsiasi modifica che implichi una scelta.**

Se identifichi un problema (es. branch non coperto, codice apparentemente inutile), DEVI:
1. Spiegare il problema
2. Proporre le possibili soluzioni
3. **ASPETTARE** la decisione dell'utente

**MAI procedere con una soluzione senza approvazione esplicita.**

---

## Project-Specific Context

### Current Status
- Development Status: Pre-Alpha
- Has Implementation: No (only structure)

### Project Description

genro-bag is the modernized bag system for the Genropy framework. The Bag is a hierarchical data container with XML serialization capabilities, used throughout Genropy for:
- Configuration management
- Data interchange
- UI component state
- Form data handling

## Critical Testing Rules

### Rule: NO Private Methods in Tests

**I test NON DEVONO MAI usare metodi privati (che iniziano con `_`).**

Questa regola è CRITICA perché:
1. Un test che usa metodi privati testa l'implementazione, non il comportamento
2. Se il test fallisce, la tentazione è modificare l'implementazione per farlo passare
3. Questo rompe il codice di produzione per far passare un test invalido

**Prima di scrivere QUALSIASI test**:
1. Verificare che NON si usino metodi/attributi che iniziano con `_`
2. Se serve accedere a qualcosa di privato, il test è sbagliato
3. Ripensare il test usando solo l'API pubblica

## Coding Style Rules

### Rule: Use safe_is_instance to Avoid Circular Imports

**MAI usare import locali a metà metodo per evitare import circolari.**

Usare invece `safe_is_instance` da `genro_toolbox.typeutils`:

```python
# ❌ SBAGLIATO - import locale a metà metodo
def set_item(self, path, value):
    from .resolver import BagResolver  # import circolare evitato ma brutto
    if isinstance(value, BagResolver):
        ...

# ✅ CORRETTO - safe_is_instance
from genro_toolbox.typeutils import safe_is_instance

def set_item(self, path, value):
    if safe_is_instance(value, "genro_bag.resolver.BagResolver"):
        ...
```

`safe_is_instance` controlla il tipo tramite la MRO (Method Resolution Order) senza importare la classe, evitando import circolari in modo pulito.

---

### Rule: Minimal Code - No Redundant Lines

**Mai aggiungere righe di codice ridondanti o controlli inutili.**

Meno righe = meno rischio di errori = codice più leggibile.

**Pattern SBAGLIATI**:

```python
# if ridondante prima di for su dizionario vuoto
options = data.get("config", {})
if options:
    for key, val in options.items():
        process(key, val)

# variabile intermedia non necessaria
bucket = store.get(name, {})
entry = bucket.setdefault(key, {})
entry["value"] = x
```

**Pattern CORRETTI**:

```python
# for itera zero volte su dizionario vuoto
for key, val in data.get("config", {}).items():
    process(key, val)

# concatenare setdefault
store.get(name, {}).setdefault(key, {})["value"] = x
```

**Regola generale**: prima di creare una variabile intermedia o aggiungere un `if`, chiedersi se è davvero necessaria.

---

**All general policies are inherited from the parent document.**
