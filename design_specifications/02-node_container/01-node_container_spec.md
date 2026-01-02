# NodeContainer Specification

**Status**: 🔴 DA REVISIONARE

## Overview

NodeContainer è un dizionario ordinato con supporto per inserimento posizionale e riordinamento degli elementi. Combina le caratteristiche di un `dict` con quelle di una lista ordinata.

## Struttura Interna

NodeContainer mantiene due strutture dati sincronizzate:

1. **Dict interno**: per accesso O(1) per chiave
2. **Lista ordinata**: per mantenere l'ordine e supportare accesso posizionale

```
NodeContainer:
  _dict: {'a': 1, 'b': 2, 'c': 3}
  _list: ['a', 'b', 'c']  # ordine delle chiavi
```

## Sintassi di Accesso

L'accesso agli elementi supporta tre notazioni **intercambiabili in tutti i metodi**:

| Sintassi | Tipo | Esempio |
|----------|------|---------|
| `'label'` | per nome | `d['foo']` |
| `3` | indice numerico | `d[3]` |
| `'#3'` | indice stringa | `d['#3']` |

Tutte e tre le notazioni funzionano ovunque: `__getitem__`, `__setitem__`, `__delitem__`, `pop()`, `move()`, etc.

```python
d = NodeContainer()
d['foo'] = 1
d['bar'] = 2
d['baz'] = 3

# Accesso equivalente
d['bar']   # → 2
d[1]       # → 2
d['#1']    # → 2
```

## Accesso a Chiavi Mancanti

NodeContainer **non solleva mai eccezioni** per chiavi/indici mancanti. Restituisce sempre `None`:

```python
d = NodeContainer()
d['foo'] = 1

d['missing']   # → None (chiave mancante)
d[99]          # → None (indice fuori range)
d['#99']       # → None (indice fuori range)
d.get('x')     # → None
d.get('x', 5)  # → 5 (default esplicito)
```

Il metodo `__contains__` è supportato per verificare l'esistenza:

```python
'foo' in d     # → True
'missing' in d # → False
0 in d         # → True (indice 0 esiste)
99 in d        # → False (indice fuori range)
```

## Inserimento con Posizione

Il parametro `_position` controlla dove inserire un nuovo elemento:

| Espressione | Significato |
|-------------|-------------|
| `>` | Append alla fine (default) |
| `<` | Inserisci all'inizio |
| `#n` | Inserisci alla posizione n |
| `<label` | Inserisci prima di label |
| `>label` | Inserisci dopo label |
| `<#n` | Inserisci prima della posizione n |
| `>#n` | Inserisci dopo la posizione n |
| `n` (int) | Indice numerico diretto |

### Esempi

```python
d = NodeContainer()
d.set('a', 1)                      # [a]
d.set('b', 2)                      # [a, b]
d.set('c', 3, _position='<')       # [c, a, b]
d.set('d', 4, _position='<b')      # [c, a, d, b]
d.set('e', 5, _position='>#1')     # [c, a, e, d, b]
d.set('f', 6, _position='#0')      # [f, c, a, e, d, b]
```

## Sovrascrittura

Quando si assegna un valore a una chiave esistente, il valore viene sovrascritto **mantenendo la posizione originale**:

```python
d = NodeContainer()
d['x'] = 1
d['y'] = 2
d['z'] = 3
# ordine: x, y, z

d['y'] = 99
# ordine: x, y, z (invariato)
# d['y'] → 99
```

## Metodo move()

Il metodo `move()` permette di riposizionare uno o più elementi senza rimuoverli dal dizionario.

### Signature

```python
def move(self, what, position):
    """Sposta uno o più elementi a una nuova posizione.

    Args:
        what: Elemento(i) da spostare. Può essere:
            - str: singola label ('foo') o indice stringa ('#3')
            - int: indice numerico (3)
            - str con virgole: multipli elementi ('foo,bar,baz')
            - list: lista mista di riferimenti ([3, 'egg', '#2'])

        position: Destinazione usando la sintassi _position
    """
```

### Esempi

```python
d = NodeContainer({'a': 1, 'b': 2, 'c': 3, 'foo': 4, 'bar': 5, 'egg': 6})
# ordine: a, b, c, foo, bar, egg

# Spostamento singolo
d.move('foo', '<')           # foo all'inizio → foo, a, b, c, bar, egg
d.move(2, '>')               # elemento in pos 2 alla fine
d.move('#3', '>foo')         # elemento in pos 3 dopo foo

# Spostamento multiplo con stringa
d.move('foo,bar', '>egg')    # foo e bar dopo egg, mantenendo ordine relativo

# Spostamento multiplo con lista
d.move([3, 'egg', '#2'], '<')  # tutti all'inizio, mantenendo ordine relativo
```

### Ordine Relativo

Quando si spostano più elementi, l'ordine relativo tra loro viene preservato:

```python
d = NodeContainer()
# ordine: a, b, c, foo, bar, egg

d.move('foo,bar', '>egg')
# risultato: a, b, c, egg, foo, bar
# foo e bar mantengono il loro ordine relativo
```

## Iterazione

I metodi `keys()`, `values()`, `items()` restituiscono elementi nell'ordine della lista interna.

Accettano un parametro `iter` (default `False`):
- `iter=False` → restituisce una lista (supporta slicing)
- `iter=True` → restituisce un iteratore

```python
d = NodeContainer()
d.set('c', 3)
d.set('a', 1)
d.set('b', 2)

d.keys()           # → ['c', 'a', 'b'] (lista)
d.keys(iter=True)  # → <iterator>

d.values()         # → [3, 1, 2] (lista)
d.items()          # → [('c', 3), ('a', 1), ('b', 2)] (lista)
```

## Slicing

Lo slicing si applica ai risultati di `keys()`, `values()`, `items()`:

```python
d = NodeContainer()
# ordine: a, b, c, d, e

d.keys()[1:3]      # → ['b', 'c']
d.values()[1:3]    # → [valori di b e c]
d.items()[1:3]     # → [('b', vb), ('c', vc)]
```

## Update

Il metodo `update()` segue la semantica standard di `dict`:

- **Chiavi esistenti**: sovrascrive il valore, mantiene la posizione originale
- **Chiavi nuove**: append in coda (equivale a `_position='>'`)

```python
d = NodeContainer()
d['a'] = 1
d['b'] = 2
d['c'] = 3
# ordine: a, b, c

d.update({'b': 99, 'x': 10, 'y': 20})
# ordine: a, b, c, x, y
# d['b'] → 99 (valore aggiornato, posizione invariata)
# x e y aggiunti in coda
```

## Clone

Il metodo `clone()` crea un nuovo NodeContainer con un sottoinsieme degli elementi.

### Signature

```python
def clone(self, selector=None):
    """Crea un clone con gli elementi selezionati.

    Args:
        selector: Può essere:
            - None: clona tutto
            - str: riferimenti separati da virgola ('alfa,beta,#9')
            - list: lista mista di riferimenti ([1, 5, '#8', 'kkk'])
            - callable: funzione che riceve (key, value) e ritorna True/False

    Returns:
        Nuovo NodeContainer con gli elementi selezionati, nell'ordine originale
    """
```

### Esempi

```python
d = NodeContainer()
d['a'] = 1
d['b'] = 2
d['c'] = 3
d['d'] = 4
d['e'] = 5
# ordine: a, b, c, d, e

# Clone totale
d.clone()                    # → NodeContainer con a, b, c, d, e

# Clone con stringa
d.clone('b,c,#4')            # → NodeContainer con b, c, e (ordine preservato)

# Clone con lista di riferimenti
d.clone([1, 'c', '#4'])      # → NodeContainer con b, c, e (ordine preservato)

# Clone con callable
d.clone(lambda k, v: v > 2)  # → NodeContainer con c, d, e (valori > 2)
```

## Metodi Standard Dict

NodeContainer supporta l'interfaccia standard di `dict`:

- `__getitem__(key)` - accesso per chiave, indice, o `#n`
- `__setitem__(key, value)` - assegnazione (supporta `_position` via `set()`)
- `__delitem__(key)` - rimozione per chiave, indice, o `#n`
- `__contains__(key)` - test di appartenenza
- `__len__()` - numero di elementi
- `__iter__()` - iterazione sulle chiavi in ordine
- `keys()` - vista delle chiavi in ordine
- `values()` - vista dei valori in ordine
- `items()` - vista delle coppie in ordine
- `get(key, default=None)` - accesso con default
- `pop(key, *default)` - rimozione con restituzione
- `clear()` - svuota il dizionario
- `update(other)` - aggiorna da altro dict/iterable

## API Completa

```python
class NodeContainer:
    # Costruttori
    def __init__(self, data=None): ...

    # Accesso
    def __getitem__(self, key): ...
    def __setitem__(self, key, value): ...
    def __delitem__(self, key): ...
    def get(self, key, default=None): ...

    # Inserimento con posizione
    def set(self, key, value, _position='>'): ...

    # Spostamento
    def move(self, what, position): ...

    # Rimozione
    def pop(self, key, *default): ...
    def clear(self): ...

    # Iterazione
    def __iter__(self): ...
    def __len__(self): ...
    def __contains__(self, key): ...
    def keys(self, iter=False): ...
    def values(self, iter=False): ...
    def items(self, iter=False): ...

    # Aggiornamento
    def update(self, other=None, **kwargs): ...

    # Clone
    def clone(self, selector=None): ...
```
