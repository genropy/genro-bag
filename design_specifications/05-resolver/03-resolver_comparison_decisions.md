# Resolver Comparison & Design Decisions

**Status**: 🔴 DA REVISIONARE
**Version**: 0.1.0
**Last Updated**: 2025-01-02

Questo documento confronta BagResolver (originale) con TreeStoreResolver e raccoglie le decisioni per il nuovo resolver di genro-bag.

---

## Legenda Decisioni

Per ogni differenza, annotare la decisione:

- ⬜ **Non deciso** - Da discutere
- 🅾️ **Originale** - Mantenere approccio BagResolver
- 🆃 **TreeStore** - Adottare approccio TreeStoreResolver
- 🆕 **Nuova soluzione** - Approccio diverso da entrambi

---

## 1. Entry Point per la Risoluzione

### BagResolver (Originale)
```python
# Callable pattern - resolver è chiamabile
value = resolver()           # __call__ è l'entry point
value = resolver(timeout=30) # può accettare kwargs per override
```

Il resolver implementa `__call__(**kwargs)` che:
1. Se kwargs diversi da self.kwargs → aggiorna e resetta cache
2. Gestisce la logica di caching
3. Chiama `load()` se necessario

### TreeStoreResolver
```python
# Metodo _htraverse come entry point
value = resolver._htraverse()                    # senza path rimanente
value = resolver._htraverse('child.grandchild')  # con path rimanente
```

Non è callable. `_htraverse` gestisce:
1. Logica di caching
2. Chiamata a `load()`
3. Continuazione del traversal se `remaining_path`

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Entry point | `__call__` | `_htraverse` |
| Callable | Sì | No |
| Override kwargs a runtime | Sì | No |
| Supporto remaining_path | No (proxy a Bag) | Sì (integrato) |

### Decisione

🅾️ **Scelta**: `__call__` come entry point (pattern originale)

**Note**:
```
Motivazioni:
- Permette kwargs dinamici: resolver(foo=1) - coerente con decisione #12
- Sintassi pythonica e naturale
- Uniformità con JavaScript dove resolve(optkwargs) è il pattern

Il resolver è callable:
- resolver() → usa parametri correnti
- resolver(**kwargs) → aggiorna parametri, invalida cache, ricarica
```

---

## 2. Sistema di Parametri

### BagResolver (Originale)
```python
class UrlResolver(BagResolver):
    # Dichiarazione a livello di classe
    classKwargs = {'cacheTime': 300, 'readOnly': False, 'timeout': 30}
    classArgs = ['url']  # args posizionali mappati ad attributi

    def load(self):
        return fetch(self.url, timeout=self.timeout)

# Uso
resolver = UrlResolver('http://...', cacheTime=60, custom='x')
# self.url = 'http://...'        (da classArgs)
# self.cacheTime = 60            (override da kwargs)
# self.readOnly = False          (default da classKwargs)
# self.timeout = 30              (default da classKwargs)
# self.kwargs = {'custom': 'x'}  (extra kwargs)
# self.custom = 'x'              (attachKwargs)
```

Caratteristiche:
- `classArgs`: lista di nomi per args posizionali
- `classKwargs`: dict con defaults per kwargs
- Extra kwargs salvati in `self.kwargs` E come attributi
- `_initArgs` e `_initKwargs` salvati per serializzazione

### TreeStoreResolver
```python
class DirectoryResolver(TreeStoreResolver):
    def __init__(self, path: str, include: str = "", **kwargs):
        super().__init__(**kwargs)  # cache_time, read_only passati qui
        self.path = path
        self.include = include
        self._init_args = (path,)   # per serializzazione
        self._init_kwargs['include'] = include  # per serializzazione

# Uso
resolver = DirectoryResolver('/path', include='*.py', cache_time=300)
```

Caratteristiche:
- Standard Python `__init__` con kwargs
- Subclass deve chiamare `super().__init__(**kwargs)`
- Subclass deve settare manualmente `_init_args` e aggiornare `_init_kwargs`
- Nessun meccanismo automatico di mapping

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Dichiarazione params | Class variables | `__init__` signature |
| Args posizionali | `classArgs` mapping | Manuale |
| Defaults | `classKwargs` dict | Python defaults |
| Extra kwargs | Auto-attached | Stored in `_init_kwargs` |
| Serialization tracking | Automatico | Manuale |
| Hook post-init | `init()` method | Nessuno |

### Decisione

🅾️ **Scelta**: Sistema classKwargs/classArgs (originale)

**Note**:
```
Motivazioni:
- Serializzazione automatica: _initArgs/_initKwargs salvati per ricreare resolver
- instanceKwargs permette propagazione a child resolver (es. DirectoryResolver)
- Dichiarativo: subclass dichiara parametri, base class gestisce mapping
- Hook init() per setup aggiuntivo senza gestire super().__init__()

Pattern uso:
class MyResolver(Resolver):
    classKwargs = {'cache_time': 300, 'read_only': False, 'timeout': 30}
    classArgs = ['url']

    def load(self):
        return fetch(self.url, timeout=self.timeout)

# Uso
resolver = MyResolver('http://...', cache_time=60)
child = MyResolver(other_url, **resolver.instanceKwargs)  # propaga config
```

---

## 3. Naming Convention

### BagResolver (Originale)
```python
cacheTime      # camelCase
readOnly       # camelCase
parentNode     # camelCase
_initArgs      # camelCase
_initKwargs    # camelCase
_cacheTime     # camelCase
_cacheTimeDelta    # camelCase
_cacheLastUpdate   # camelCase
```

### TreeStoreResolver
```python
cache_time         # snake_case
read_only          # snake_case
parent_node        # snake_case
_init_args         # snake_case
_init_kwargs       # snake_case
_cache_time        # snake_case
_cache_time_delta  # snake_case
_cache_timestamp   # snake_case (diverso nome!)
```

### Differenze Chiave

| Attributo | BagResolver | TreeStoreResolver |
|-----------|-------------|-------------------|
| Cache time | `cacheTime` | `cache_time` |
| Read only | `readOnly` | `read_only` |
| Parent node | `parentNode` | `parent_node` |
| Last update | `_cacheLastUpdate` | `_cache_timestamp` |

### Decisione

🆃 **Scelta**: snake_case (PEP8), wrapper mappa per compatibilità

**Mapping:**
| Interno (snake_case) | Wrapper JS (camelCase) |
|---------------------|------------------------|
| `cache_time` | `cacheTime` |
| `read_only` | `readOnly` |
| `parent_node` | `parentNode` |
| `_init_args` | `_initArgs` |
| `_init_kwargs` | `_initKwargs` |

**Note**:
```
Motivazioni:
- Codice Python segue PEP8 (snake_case)
- Wrapper JavaScript fa mapping automatico snake_case ↔ camelCase
- Uniformità: Python pythonic, JS idiomatico
- Nessun compromesso: ogni linguaggio usa le sue convenzioni

Il wrapper gestisce la conversione:
- Python: resolver.cache_time = 300
- JS: resolver.cacheTime = 300  (wrapper converte)
```

---

## 4. Gestione Cache - Stato Iniziale

### BagResolver (Originale)
```python
def _set_cacheTime(self, cacheTime):
    self._cacheTime = cacheTime
    if cacheTime != 0:
        # ...
        self._cacheLastUpdate = datetime.min  # Valore sentinel
```

Usa `datetime.min` come sentinel per "mai aggiornato".

### TreeStoreResolver
```python
@cache_time.setter
def cache_time(self, value: int) -> None:
    self._cache_time = value
    if value != 0:
        # ...
        self._cache_timestamp = None  # None come sentinel
```

Usa `None` come sentinel per "mai aggiornato".

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Sentinel "never updated" | `datetime.min` | `None` |
| Check in `expired` | `== datetime.min` | `is None` |

### Decisione

🆕 **Scelta**: `None` come sentinel + `or datetime.min` nel calcolo

**Implementazione:**
```python
def __init__(self):
    self._cache_timestamp = None  # None = mai aggiornato

@property
def expired(self):
    if self._cache_time == 0:
        return True
    return (datetime.now() - (self._cache_timestamp or datetime.min)) > self._cache_time_delta
```

**Note**:
```
Combina il meglio di entrambi gli approcci:
- None come sentinel: semanticamente chiaro ("nessun timestamp")
- or datetime.min: calcolo unico senza branch aggiuntivo
- Il risultato di (now - datetime.min) è sempre > qualsiasi TTL ragionevole
```

---

## 5. Supporto Async

### BagResolver (Originale)
```python
def load(self):
    """Sync only - no async support"""
    pass

def __call__(self, **kwargs):
    # ...
    return self.load()  # chiamata sincrona
```

Nessun supporto async. Operazioni I/O bloccano.

### TreeStoreResolver
```python
@smartasync
async def load(self) -> Any:
    """Async with sync transparency via @smartasync"""
    raise NotImplementedError

def _htraverse(self, remaining_path=None):
    # ...
    result = self.load()  # smartasync gestisce sync/async
```

`@smartasync` decorator permette:
- Da contesto sync: esegue via `asyncio.run()`
- Da contesto async: ritorna coroutine per `await`

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Async support | No | Sì via `@smartasync` |
| Blocking I/O | Sì | Evitabile |
| Dipendenza | Nessuna | `genro_toolbox.smartasync` |

### Decisione

🆕 **Scelta**: @smartasync + Lock/Future nel Resolver (non nel Node)

**Principio**: Il Resolver incapsula tutta la sua logica (caricamento + concorrenza).
Il Node rimane semplice e non deve conoscere i dettagli async del resolver.

**Componenti:**

1. **`@smartasync` su `load()`**: trasparenza sync/async
2. **Lock nel Resolver**: serializza chi inizia il load
3. **Future nel Resolver**: condivide risultato con chi arriva durante il load

**Design:**
```python
class Resolver:
    __slots__ = (..., '_lock', '_loading_future')

    def __init__(self, *args, **kwargs):
        # ...
        self._lock = None           # Lock creato on-demand
        self._loading_future = None # Future per condividere risultato

    def __call__(self, **kwargs) -> Any:
        read_only = self._kw.get('read_only', True)

        if read_only:
            # Pure getter: ogni chiamata indipendente, nessun lock
            return self._resolve_with_kwargs(kwargs) if kwargs else self.load()

        # Cached mode: gestione concorrenza
        return self._resolve_cached()

    async def _resolve_cached(self) -> Any:
        """Risoluzione con gestione concorrenza per read_only=False."""
        # Fast path: cache valida (gestita dal Node, qui per completezza)
        if not self.expired:
            return None  # Segnala al Node di usare _value

        # Se c'è già un Future in corso, attendi quello (no lock)
        if self._loading_future is not None:
            return await self._loading_future

        # Primo arrivato: crea lock e future
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()

        async with self._lock:
            # Double-check dopo lock
            if not self.expired:
                return None  # Un altro thread ha completato

            # Crea Future per chi arriva mentre carico
            import asyncio
            loop = asyncio.get_event_loop()
            self._loading_future = loop.create_future()
            try:
                result = await self.load()
                self._cache_last_update = datetime.now()
                self._loading_future.set_result(result)
                return result
            except Exception as e:
                self._loading_future.set_exception(e)
                raise
            finally:
                self._loading_future = None

    @smartasync
    async def load(self):
        """Implementato dalle subclass. @smartasync gestisce sync/async."""
        raise NotImplementedError


class Node:
    """Node rimane semplice - delega al resolver."""

    def get_value(self):
        if self._resolver is None:
            return self._value

        if self._resolver.read_only:
            return self._resolver()  # Resolver gestisce tutto

        if self._resolver.expired:
            result = self._resolver()  # Resolver gestisce lock/future
            if result is not None:
                self._value = result

        return self._value
```

**Flusso temporale:**
```
T0: Request 1 → resolver() → expired, future=None → lock, crea future, load()
T1: Request 2 → resolver() → expired, future=SET → await future (bypass lock)
T2: Request 3 → resolver() → expired, future=SET → await future (bypass lock)
T3: load() completa → future.set_result() → tutti ricevono risultato
T4: rilascia lock, future=None
```

**Note**:
```
Motivazioni:
- Separazione responsabilità: Resolver sa come caricare E come serializzare i caricamenti
- Node rimane semplice: chiama resolver(), ottiene valore
- Resolver è una "black box": incapsula tutta la complessità
- Future evita load() duplicati durante caricamento
- @smartasync permette load() async chiamabile da contesto sync

Use case principale: Bag condivisa in contesto ASGI (uvicorn/FastAPI)
- Più request concorrenti sullo stesso path
- Un solo load(), risultato condiviso

Quando NON serve (ottimizzazione automatica):
- read_only=True: nessun lock/future (ogni chiamata indipendente)
- Contesto sync single-thread: lock mai conteso
- Cache valida: fast path senza lock
```

---

## 6. Proxy Behavior

### BagResolver (Originale)
```python
def __getitem__(self, k):
    return self()[k]

def keys(self):
    return list(self().keys())

def items(self):
    return list(self().items())

def values(self):
    return list(self().values())

def _htraverse(self, *args, **kwargs):
    return self()._htraverse(*args, **kwargs)

def getNode(self, k):
    return self().getNode(k)
```

Il resolver agisce come **proxy trasparente** alla Bag risolta.

### TreeStoreResolver
```python
# Nessun metodo proxy
# Il resolver NON è un proxy
```

Non implementa alcun metodo proxy. Accesso solo via node/store.

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| `resolver['key']` | Funziona (proxy) | AttributeError |
| `resolver.keys()` | Funziona (proxy) | AttributeError |
| `resolver.items()` | Funziona (proxy) | AttributeError |
| Uso diretto | Possibile | Solo via node/store |

### Decisione

🅾️ **Scelta**: Proxy espliciti (originale)

**Note**:
```
Motivazioni:
- Retrocompatibilità con codice esistente
- Sintassi più naturale: resolver['key'] vs node.value['key']
- Costo implementativo minimo (pochi metodi delegati)

Metodi proxy mantenuti:
- __getitem__(k) → self()[k]
- keys() → self().keys()
- items() → self().items()
- values() → self().values()
- _htraverse(*args, **kwargs) → self()._htraverse(*args, **kwargs)
- get_node(k) → self().get_node(k)
```

---

## 7. Serialization

### BagResolver (Originale)
```python
def resolverSerialize(self, args=None, kwargs=None):
    attr = {}
    attr['resolverclass'] = self.__class__.__name__
    attr['resolvermodule'] = self.__class__.__module__
    attr['args'] = self._initArgs
    attr['kwargs'] = self._initKwargs
    attr['kwargs']['cacheTime'] = self.cacheTime
    return attr

# NO deserialize nel resolver base
# Deserializzazione gestita altrove in Genropy
```

### TreeStoreResolver
```python
def serialize(self) -> dict[str, Any]:
    return {
        "resolver_module": self.__class__.__module__,
        "resolver_class": self.__class__.__name__,
        "args": self._init_args,
        "kwargs": {
            "cache_time": self.cache_time,
            "read_only": self.read_only,
            **self._init_kwargs,
        },
    }

@classmethod
def deserialize(cls, data: dict[str, Any]) -> TreeStoreResolver:
    module = importlib.import_module(data["resolver_module"])
    resolver_cls = getattr(module, data["resolver_class"])
    return resolver_cls(*data.get("args", ()), **data.get("kwargs", {}))
```

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Metodo serialize | `resolverSerialize()` | `serialize()` |
| Metodo deserialize | No (esterno) | Sì (`deserialize()`) |
| Keys nel dict | `resolverclass`, `resolvermodule` | `resolver_class`, `resolver_module` |
| Round-trip completo | No | Sì |

### Decisione

🆕 **Scelta**: `serialize()` / `deserialize()` simmetrici (snake_case)

**Implementazione:**
```python
def serialize(self) -> dict[str, Any]:
    return {
        "resolver_module": self.__class__.__module__,
        "resolver_class": self.__class__.__name__,
        "args": self._init_args,
        "kwargs": {
            "cache_time": self.cache_time,
            "read_only": self.read_only,
            **self._init_kwargs,
        },
    }

@classmethod
def deserialize(cls, data: dict[str, Any]) -> "Resolver":
    module = importlib.import_module(data["resolver_module"])
    resolver_cls = getattr(module, data["resolver_class"])
    return resolver_cls(*data.get("args", ()), **data.get("kwargs", {}))
```

**Note**:
```
Motivazioni:
- Nomi metodi snake_case (coerente con decisione #3)
- Chiavi output snake_case (resolver_class, resolver_module)
- Round-trip completo: serialize() + deserialize() nella stessa classe
- deserialize() come @classmethod: permette ricostruzione da qualsiasi subclass
- Simmetria: chi serializza può deserializzare
```

---

## 8. Hook per Subclassi

### BagResolver (Originale)
```python
def __init__(self, *args, **kwargs):
    # ... setup complesso con classArgs/classKwargs ...
    self.init()  # hook per subclassi

def init(self):
    """Hook chiamato alla fine di __init__.
    Subclassi possono override senza chiamare super().__init__()"""
    pass

def load(self):
    """Da implementare. Base non fa nulla."""
    pass
```

Due hook:
- `init()`: setup aggiuntivo post-init
- `load()`: caricamento valore (base fa `pass`)

### TreeStoreResolver
```python
def __init__(self, cache_time=0, read_only=True, **kwargs):
    # setup diretto
    # NO hook init()

@smartasync
async def load(self) -> Any:
    """Da implementare. Base solleva NotImplementedError."""
    raise NotImplementedError("Subclasses must implement load()")
```

Un solo hook:
- `load()`: caricamento valore (base solleva eccezione)
- Nessun `init()` hook

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Hook post-init | `init()` | Nessuno |
| `load()` base | `pass` (no-op) | `NotImplementedError` |
| Subclass init | Può evitare `super().__init__()` | Deve chiamare `super().__init__()` |

### Decisione

🆕 **Scelta**: `init()` hook + `load()` con NotImplementedError

**Implementazione:**
```python
class Resolver:
    def __init__(self, *args, **kwargs):
        # ... setup classKwargs/classArgs ...
        self.init()  # hook per subclass

    def init(self):
        """Hook per setup aggiuntivo nelle subclass.
        Override senza bisogno di chiamare super().__init__()."""
        pass

    @smartasync
    async def load(self):
        """Da implementare nelle subclass."""
        raise NotImplementedError("Subclasses must implement load()")
```

**Note**:
```
Motivazioni:
- init() hook: coerente con sistema classKwargs/classArgs (decisione #2)
- Le subclass non devono gestire super().__init__(), solo init()
- load() con NotImplementedError: errore esplicito se non implementato
- Meglio di pass silenzioso che ritorna None
```

---

## 9. Equality

### BagResolver (Originale)
```python
def __eq__(self, other):
    try:
        if isinstance(other, self.__class__) and (self.kwargs == other.kwargs):
            return True
    except:
        return False
```

Due resolver sono uguali se:
- Stessa classe
- Stesso `self.kwargs` (solo extra kwargs!)

**Nota**: Non confronta `classKwargs` processati, solo extras.

### TreeStoreResolver
```python
# Nessun __eq__ definito
# Usa default object identity
```

Equality è object identity (`is`).

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| `__eq__` custom | Sì | No |
| Confronto | `kwargs` dict | Object identity |
| `r1 == r2` | True se stessa classe e kwargs | True solo se stesso oggetto |

### Decisione

🆕 **Scelta**: Fingerprint calcolato all'init per `__eq__`

**Implementazione:**
```python
def __init__(self, *args, **kwargs):
    # ... setup classKwargs/classArgs ...
    self._fingerprint = self._compute_fingerprint()

def _compute_fingerprint(self):
    """Calcola hash basato su serialize()."""
    data = self.serialize()
    # Converte in struttura hashable
    return hash(json.dumps(data, sort_keys=True))

def __eq__(self, other):
    if not isinstance(other, self.__class__):
        return False
    return self._fingerprint == other._fingerprint
```

**Note**:
```
Motivazioni:
- Confronto O(1) invece di ricostruire dict ogni volta
- Basato su serialize(): confronta tutti i parametri (non solo kwargs come originale)
- Calcolato una volta all'init, immutabile
- Nessun __hash__: non serve usare resolver come chiavi dict/set
```

---

## 10. Parent Node Reference

### BagResolver (Originale)
```python
def _get_parentNode(self):
    if hasattr(self, '_parentNode'):
        return self._parentNode

def _set_parentNode(self, parentNode):
    if parentNode == None:
        self._parentNode = None
    else:
        # Nota: weakref era commentato
        # self._parentNode = weakref.ref(parentNode)
        self._parentNode = parentNode

parentNode = property(_get_parentNode, _set_parentNode)
```

- Property con getter/setter espliciti
- Codice per weakref commentato (non usato)
- Riferimento forte al parent node

### TreeStoreResolver
```python
__slots__ = ("parent_node", ...)

def __init__(self, ...):
    self.parent_node: TreeStoreNode | None = None
```

- Semplice attributo in `__slots__`
- Riferimento forte al parent node
- Type hint esplicito

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Implementazione | Property esplicita | Attributo diretto |
| Weakref | Commentato/non usato | Non considerato |
| Naming | `parentNode` | `parent_node` |

### Decisione

🆕 **Scelta**: Attributo diretto + snake_case (`parent_node`)

**Implementazione:**
```python
class Resolver:
    def __init__(self, *args, **kwargs):
        self.parent_node: Node | None = None
        # ... resto dell'init ...
```

**Note**:
```
Motivazioni:
- La property originale era vestigio storico (weakref mai implementato)
- Getter/setter non fanno nulla di speciale, solo assignment
- Attributo diretto = stesso comportamento, meno codice
- snake_case coerente con decisione #3
```

---

## 11. Memory Management

### BagResolver (Originale)
```python
# Nessun __slots__
# Attributi in __dict__
# _attributes = {} legacy (forse non usato)
```

Usa `__dict__` standard. Commento nel codice: "ma servono ?????" per `_attributes`.

### TreeStoreResolver
```python
__slots__ = (
    "parent_node",
    "_cache_time",
    "read_only",
    "_cache",
    "_cache_timestamp",
    "_cache_time_delta",
    "_init_args",
    "_init_kwargs",
)
```

Usa `__slots__` per efficienza memoria.

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Storage | `__dict__` | `__slots__` |
| Memory footprint | Maggiore | Minore |
| Dynamic attributes | Possibili | No (senza `__dict__`) |
| Legacy cruft | `_attributes` dict | Nessuno |

### Decisione

🆕 **Scelta**: `__slots__` + `_kw` dict per parametri classKwargs/classArgs

**Implementazione:**
```python
class Resolver:
    __slots__ = ('_kw', '_init_args', '_init_kwargs',
                 'parent_node', '_fingerprint', '_cache_last_update')

    def __init__(self, *args, **kwargs):
        self._kw = {}
        # classArgs -> _kw
        for j, arg in enumerate(args):
            self._kw[self.class_args[j]] = arg
        # classKwargs -> _kw
        for name, default in self.class_kwargs.items():
            self._kw[name] = kwargs.get(name, default)

# Uso nelle subclass:
class UrlResolver(Resolver):
    class_kwargs = {'cache_time': 0, 'timeout': 30}
    class_args = ['url']

    def load(self):
        return fetch(self._kw['url'], timeout=self._kw['timeout'])
```

**Note**:
```
Motivazioni:
- __slots__ per risparmio memoria
- _kw dict contiene tutti i parametri classKwargs/classArgs
- Accesso uniforme: self._kw['param_name']
- Eventuale layer di compatibilità può mappare self.param -> self._kw['param']
```

---

## 12. Dynamic kwargs Update at Runtime

### BagResolver (Originale)
```python
def __call__(self, **kwargs):
    # Permette override kwargs a runtime
    if kwargs and kwargs != self.kwargs:
        self.kwargs.update(kwargs)
        self._attachKwargs()
        self.reset()  # invalida cache

    # procede con risoluzione...
```

Permette di cambiare parametri del resolver a runtime senza creare nuova istanza.

### TreeStoreResolver
```python
def _htraverse(self, remaining_path=None):
    # Nessun supporto per kwargs override
    # ...
```

Non supporta override runtime. Per cambiare parametri, creare nuovo resolver.

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Runtime kwargs override | Sì | No |
| `resolver(new_param=x)` | Funziona | Non applicabile |
| Mutabilità parametri | Sì | No (immutabile dopo init) |

### Decisione

🆕 **Scelta**: kwargs solo per read_only=True

**Comportamento:**
```python
def __call__(self, **kwargs):
    if self.read_only:
        # Pure getter: kwargs permessi, merge temporaneo per questa chiamata
        merged = {**self.kwargs, **kwargs}
        return self.load(**merged)
    else:
        # Cached: kwargs NON permessi
        if kwargs:
            raise ValueError("Cannot pass kwargs to cached resolver")
        # ... logica cache con Future per concorrenza
```

**Note**:
```
Analisi del problema concorrenza:
- Se load() è in corso e arriva seconda richiesta con kwargs diversi → conflitto
- Con read_only=True: ogni chiamata è indipendente, nessun conflitto
- Con read_only=False: cache condivisa, kwargs creerebbero inconsistenza

Decisione:
- read_only=True: kwargs permessi (merge temporaneo, non permanente)
- read_only=False: kwargs vietati, parametri fissi da __init__

Questo semplifica la gestione concorrenza e rende il comportamento prevedibile.
```

---

## 13. Default Values

### BagResolver (Originale)
```python
classKwargs = {'cacheTime': 0, 'readOnly': True}
```

- `cacheTime=0`: no cache (sempre ricalcola)
- `readOnly=True`: non salva in node._value

### TreeStoreResolver
```python
def __init__(self, cache_time: int = 0, read_only: bool = True, **kwargs):
```

- `cache_time=0`: no cache (sempre ricalcola)
- `read_only=True`: non salva in node._value

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| Default cache_time | 0 | 0 |
| Default read_only | True | True |

**Nessuna differenza nei defaults.**

### Decisione

🅾️ **Scelta**: Mantenere default originali (identici)

**Implementazione:**
```python
class Resolver:
    class_kwargs = {'cache_time': 0, 'read_only': True}
```

**Note**:
```
Motivazioni:
- Default identici in entrambe le implementazioni
- cache_time=0: no cache di default (sicuro)
- read_only=True: non modifica node._value di default
- Nessun cambiamento necessario
```

---

## 14. instanceKwargs Property

### BagResolver (Originale)
```python
def _get_instanceKwargs(self):
    """Return all current parameters (classKwargs + classArgs)."""
    result = {}
    for par, dflt in list(self.classKwargs.items()):
        result[par] = getattr(self, par)
    for par in self.classArgs:
        result[par] = getattr(self, par)
    return result

instanceKwargs = property(_get_instanceKwargs)
```

Permette di ottenere tutti i parametri correnti per debug/serializzazione.

### TreeStoreResolver
```python
# Nessun equivalente
# _init_args e _init_kwargs sono separati e non riflettono stato corrente
```

Non ha equivalente. `_init_args` e `_init_kwargs` contengono valori originali, non correnti.

### Differenze Chiave

| Aspetto | BagResolver | TreeStoreResolver |
|---------|-------------|-------------------|
| `instanceKwargs` | Sì (property) | No |
| Stato corrente params | Accessibile | Non aggregato |

### Decisione

🆕 **Scelta**: Eliminare `instanceKwargs`, usare `serialize()` o `_kw`

**Note**:
```
Motivazioni:
- serialize() già ritorna tutti i parametri (decisione #7)
- _kw è accessibile direttamente se serve stato corrente
- Property ridondante = codice in più senza valore aggiunto
- Meno API surface = meno manutenzione
```

---

## 15. Cache Architecture

### BagResolver (Original)

Two separate caches:

1. **Resolver internal cache** (`_cache`):
```python
def __call__(self, **kwargs):
    if self.expired:
        result = self.load()
        self._cache = result           # cache in resolver
        self._cacheLastUpdate = datetime.now()
    else:
        result = self._cache           # use resolver cache
    return result
```

2. **Node cache** (`_value`):
```python
def getValue(self, mode=''):
    if self._resolver.readOnly:
        return self._resolver()        # don't save in _value
    if self._resolver.expired:
        self.value = self._resolver()  # save in _value
    return self._value                 # use _value as cache
```

### TreeStoreResolver

Similar dual cache architecture inherited from original.

### The Problem

With `readOnly=False`:
- Node uses `_value` as cache
- Node checks `expired` to decide whether to call resolver
- But resolver ALSO has internal cache!
- **Redundant caching**

With `readOnly=True`:
- Node never saves to `_value`
- Resolver has internal cache
- But semantically: `readOnly=True` means "volatile/dynamic value"
- **Why cache a volatile value?**

### Decision

🆕 **Choice**: Simplify cache architecture

**readOnly=True implies NO cache:**
- `readOnly=True` = pure computed getter, always call `load()`
- No `cacheTime` needed, no `expired` check
- Every access → fresh `load()` call

**readOnly=False implies cache in _value:**
- `readOnly=False` = value can be cached
- `_value` IS the cache (single cache location)
- `cacheTime`/`expired` control when to re-call `load()`
- Resolver has NO internal `_cache`

**Summary:**

| readOnly | Cache Location | cacheTime | expired |
|----------|---------------|-----------|---------|
| `True` | None | Ignored | N/A |
| `False` | `node._value` | Controls TTL | Controls refresh |

**Notes**:
```
This decision eliminates redundant caching and clarifies semantics:
- readOnly=True: pure getter, always fresh (like @property)
- readOnly=False: cached value with TTL control

The resolver becomes simpler:
- load(): loads the value
- expired: tells Node whether to re-call load()
- No internal _cache needed

Cache management is Node's responsibility, not Resolver's.
```

---

## Riepilogo Decisioni

| # | Aspetto | Decisione | Note |
|---|---------|-----------|------|
| 1 | Entry Point | 🅾️ | `__call__` come originale |
| 2 | Sistema Parametri | 🅾️ | classKwargs/classArgs originale |
| 3 | Naming Convention | 🆃 | snake_case, wrapper mappa per JS |
| 4 | Cache Stato Iniziale | 🆕 | None + `or datetime.min` nel calcolo |
| 5 | Supporto Async | 🆕 | @smartasync + Lock/Node + Future per sharing |
| 6 | Proxy Behavior | 🅾️ | Proxy espliciti (originale) |
| 7 | Serialization | 🆕 | serialize()/deserialize() simmetrici, snake_case |
| 8 | Hook Subclassi | 🆕 | init() hook + load() NotImplementedError |
| 9 | Equality | 🆕 | Fingerprint all'init per __eq__ |
| 10 | Parent Node Ref | 🆕 | Attributo diretto `parent_node` (snake_case) |
| 11 | Memory Management | 🆕 | `__slots__` + `_kw` dict per parametri |
| 12 | Dynamic kwargs | 🆕 | kwargs solo per read_only=True, merge temporaneo |
| 13 | Default Values | 🅾️ | Mantenere default originali (cache_time=0, read_only=True) |
| 14 | instanceKwargs | 🆕 | Eliminato, usare serialize() o _kw |
| 15 | Cache Architecture | 🆕 | readOnly=True → no cache; readOnly=False → cache in _value |

---

## Note Aggiuntive

```
[Spazio per annotazioni generali, domande aperte, considerazioni architetturali]










```

---

## Firme Approvazione

| Ruolo | Nome | Data | Firma |
|-------|------|------|-------|
| Architect | | | |
| Reviewer | | | |
