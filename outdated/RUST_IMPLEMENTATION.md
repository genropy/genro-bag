# GnrBag Rust Implementation - Design Notes

**Version**: 0.1.0
**Last Updated**: 2025-12-07
**Status**: Pre-Alpha (Discussion Only)

## Objective

Rewrite GnrBag in Rust with bindings for Python (PyO3) and JavaScript (wasm-bindgen).

**Goal**: DRY - Single codebase serving both Python and JavaScript.
**NOT for performance** - Goal is code sharing, not speedup.

## Current Implementations

| Language | Location | Usage |
|----------|----------|-------|
| Python | `gnrpy/gnr/core/gnrbag.py` (~3500 lines) | ORM, GUI, server store, client-server comm |
| JavaScript | `gnrjs/gnr_d11/js/gnrbag.js` | SPA store (lives all day), reactive triggers |

## Genropy Architecture Context

In a Genropy page, there are **two main Bags**:

### DATASTORE (Data + Control)

- User data (`abc.name = "Mario"`)
- Mutable widget properties (`xx.zz.color = "red"`)
- Changes → update existing DOM attributes (no rebuild)
- Bidirectional binding with `^` pointer syntax

```html
<input value="^abc.name" color="^xx.zz.color" />
```

When `abc.name` changes → input displays new value.
When user types → value written back to `abc.name`.

### DATASOURCE (Structure)

- Widget definitions, layouts, panels
- Changes → Builder reconstructs DOM
- Add/remove widgets dynamically
- Lazy loading of panels from server

### Page Lifecycle

1. User requests page → server assigns `page_id`
2. Server renders lightweight HTML with `genro` object
3. `genro` calls server `main` method with `page_id`, URL, params
4. Server returns XML (page structure) → goes to DATASOURCE
5. Server may also send data → goes to DATASTORE
6. Builder constructs HTML/widgets from DATASOURCE
7. Widgets bind to DATASTORE via `^path` pointers

### Resolvers in Both Bags

| Bag | Resolver For | Example |
|-----|--------------|---------|
| DATASTORE | Lazy loading data | Load customer list on demand |
| DATASOURCE | Lazy loading UI structure | Tab panels loaded on click |

**Tab Container Example** (DATASOURCE resolver):

```
DATASOURCE:
└── tabContainer
    ├── tab1: { ...content loaded... }
    ├── tab2: RESOLVER → click → fetch from server → replace with structure
    └── tab3: RESOLVER → click → fetch from server → replace with structure
```

When user clicks tab2:
1. DATASOURCE triggers resolver
2. Resolver fetches from server (async)
3. Server returns XML/structure
4. Resolver writes to DATASOURCE (replaces itself)
5. Builder sees change → constructs tab DOM

## What Rust Handles

1. **Data Structure**: `Bag` and `BagNode` storage
2. **Path Operations**: get/set by path (`a.b.c`, `#0`, `#^parent`)
3. **Serialization**: MessagePack (primary), JSON (TYTX), XML (legacy)
4. **Localization**: `!![en]Book` → `Libro` translation during serialization
5. **Type System**: All TYTX types (Decimal, Date, DateTime, Time, etc.)

## What Stays in Host Language

| Feature | Reason |
|---------|--------|
| Resolvers | Lazy loading callbacks (Python/JS functions) |
| Triggers | Reactive callbacks on path changes |
| Validators | Validation logic |
| Callable execution | RPC function invocation |

## Architecture Decision: Internal Rust Structure

The Bag uses **internal Rust structures** (not native Python/JS containers). This enables:

1. **Path traversal** written once in Rust
2. **Serialization** MessagePack native, zero FFI
3. **FFI cost** paid only at boundaries (insert/extract values)

The Rust Bag "pretends" to be native containers via protocol implementation:

- Python: `__getitem__`, `__setitem__`, `__iter__`, `__len__`
- JavaScript: `Proxy` handlers or explicit get/set methods

## Core Data Structures

```rust
pub struct Bag {
    nodes: Vec<BagNode>,
    on_change: Option<PyObject>,  // Python callback for triggers (PyO3)
    // or: Option<js_sys::Function> for WASM
}

pub struct BagNode {
    label: String,
    value: BagValue,
    attrs: HashMap<String, BagValue>,
    resolver: Option<PyObject>,  // Live Python/JS callable (not serializable)
    resolver_marker: Option<ResolverMarker>,  // Serializable marker for round-trip
}

pub enum BagValue {
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Decimal(rust_decimal::Decimal),
    String(String),
    Date(chrono::NaiveDate),
    DateTime(chrono::DateTime<Utc>),
    Time(chrono::NaiveTime),
    Bag(Box<Bag>),
    List(Vec<BagValue>),
    Callable(CallableMarker),   // Opaque marker
    Resolver(ResolverMarker),   // Opaque marker
}
```

## Callable Pattern

Callables are **NOT executed by Rust** - serialized as markers for round-trip:

```
Server (Python)     →  Serialize  →  Client (JS)
rpc_load_data()        "rpc_load_data::CALLABLE"    stores string as-is

Client (JS)         →  Lazy Load  →  Server (Python)
sends string back      "rpc_load_data::CALLABLE"    looks up in RPC registry → executes
```

```rust
pub struct CallableMarker {
    name: String,
    module: Option<String>,
}
```

## Resolver Pattern

Two modes for resolvers:

### 1. Live Resolver (Runtime)

Rust holds a **reference to the actual Python/JS callable**:

```rust
#[pyclass]
pub struct BagNode {
    resolver: Option<PyObject>,  // Live Python callable
}

#[pymethods]
impl BagNode {
    fn get_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        if let Some(ref resolver) = self.resolver {
            resolver.call0(py)  // Calls Python function
        } else {
            self.value.to_py(py)
        }
    }
}
```

### 2. Serializable Marker (Round-trip)

For serialization, Rust stores metadata only:

```rust
pub struct ResolverMarker {
    resolver_type: String,  // "BagCbResolver", "UrlResolver", etc.
    resolver_module: String,
    args: Vec<BagValue>,
    kwargs: HashMap<String, BagValue>,
    cache_time: i64,
}
```

### Example: Live Resolver (Python)

```python
from datetime import datetime
import zoneinfo

bag = Bag()

def get_london_time():
    tz = zoneinfo.ZoneInfo("Europe/London")
    return datetime.now(tz).strftime("%H:%M:%S")

def get_tokyo_time():
    tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    return datetime.now(tz).strftime("%H:%M:%S")

# Rust holds reference to Python functions
bag.set_resolver("orario.londra", get_london_time)
bag.set_resolver("orario.tokyo", get_tokyo_time)

# Each access calls the Python function via PyO3
print(bag.get("orario.londra"))  # → "14:30:45"
print(bag.get("orario.tokyo"))   # → "23:30:45"
```

### Example: Live Resolver (JavaScript/WASM)

```javascript
import { Bag } from './genro_bag_wasm.js';

const bag = new Bag();

function getLondonTime() {
    return new Date().toLocaleTimeString('en-GB', { timeZone: 'Europe/London' });
}

function getTokyoTime() {
    return new Date().toLocaleTimeString('ja-JP', { timeZone: 'Asia/Tokyo' });
}

// WASM holds reference to JS functions
bag.set_resolver("orario.londra", getLondonTime);
bag.set_resolver("orario.tokyo", getTokyoTime);

// Each access calls the JS function via wasm-bindgen
console.log(bag.get("orario.londra"));  // → "14:30:45"
console.log(bag.get("orario.tokyo"));   // → "23:30:45"
```

### Rust Implementation (PyO3)

```rust
#[pymethods]
impl Bag {
    fn set_resolver(&mut self, py: Python<'_>, path: &str, resolver: PyObject) {
        let mut node = BagNode::new(path.to_string());
        node.resolver = Some(resolver);
        self.nodes.insert(path.to_string(), node);
    }

    fn get(&self, py: Python<'_>, path: &str) -> PyResult<PyObject> {
        if let Some(node) = self.nodes.get(path) {
            if let Some(ref resolver) = node.resolver {
                resolver.call0(py)  // Call Python function
            } else {
                node.value.to_py(py)
            }
        } else {
            Ok(py.None())
        }
    }
}
```

### Rust Implementation (WASM)

```rust
#[wasm_bindgen]
impl Bag {
    pub fn set_resolver(&mut self, path: &str, resolver: js_sys::Function) {
        let mut node = BagNode::new(path.to_string());
        node.resolver = Some(resolver);
        self.nodes.insert(path.to_string(), node);
    }

    pub fn get(&self, path: &str) -> Result<JsValue, JsValue> {
        if let Some(node) = self.nodes.get(path) {
            if let Some(ref resolver) = node.resolver {
                resolver.call0(&JsValue::NULL)  // Call JS function
            } else {
                Ok(node.value.to_js())
            }
        } else {
            Ok(JsValue::NULL)
        }
    }
}
```

## Resolver Cache System

The Python `BagResolver` implements a cache mechanism that Rust must replicate.

### Cache Semantics (from Python gnrbag.py)

| `cache_time` value | Behavior |
|--------------------|----------|
| `0` | No cache - always call `load()` |
| `> 0` | Cache for N seconds |
| `< 0` | Cache **forever** (`timedelta.max`) |

### Python Reference Implementation

```python
# From gnrbag.py lines 2661-2703

def _set_cacheTime(self, cacheTime):
    self._cacheTime = cacheTime
    if cacheTime != 0:
        if cacheTime < 0:
            self._cacheTimeDelta = timedelta.max  # Infinite cache
        else:
            self._cacheTimeDelta = timedelta(0, cacheTime)  # N seconds
        self._cache = None
        self._cacheLastUpdate = datetime.min

def _get_expired(self):
    if self._cacheTime == 0 or self._cacheLastUpdate == datetime.min:
        return True  # No cache or never updated
    return (datetime.now() - self._cacheLastUpdate) > self._cacheTimeDelta

def __call__(self, **kwargs):
    # If kwargs change → reset cache
    if kwargs and kwargs != self.kwargs:
        self.kwargs.update(kwargs)
        self._attachKwargs()
        self.reset()

    # No cache mode
    if self.cacheTime == 0:
        return self.load()

    # Cache logic
    if self.expired:
        result = self.load()
        self._cacheLastUpdate = datetime.now()
        self._cache = result
    else:
        result = self._cache
    return result

def reset(self):
    self._cache = None
    self._cacheLastUpdate = datetime.min
```

### Rust Data Structure with Cache

```rust
pub struct BagNode {
    label: String,
    value: BagValue,
    attrs: HashMap<String, BagValue>,

    // Resolver (live callable)
    resolver: Option<PyObject>,  // or js_sys::Function for WASM

    // Resolver metadata (serializable)
    resolver_marker: Option<ResolverMarker>,

    // Cache state
    cache_time: i64,                           // 0=no cache, <0=infinite, >0=seconds
    cached_value: Option<BagValue>,            // The cached result
    cache_last_update: Option<DateTime<Utc>>,  // When cache was last populated
}

impl BagNode {
    /// Check if cache is expired
    fn is_cache_expired(&self) -> bool {
        // No cache mode
        if self.cache_time == 0 {
            return true;
        }

        // Never updated
        let Some(last_update) = self.cache_last_update else {
            return true;
        };

        // Infinite cache (cache_time < 0)
        if self.cache_time < 0 {
            return false;
        }

        // Check expiration
        let elapsed = Utc::now() - last_update;
        elapsed.num_seconds() > self.cache_time
    }

    /// Reset cache (called when kwargs change)
    fn reset_cache(&mut self) {
        self.cached_value = None;
        self.cache_last_update = None;
    }
}
```

### Rust Implementation with Cache (PyO3)

```rust
#[pymethods]
impl BagNode {
    fn get_value(&mut self, py: Python<'_>) -> PyResult<PyObject> {
        // No resolver → return static value
        let Some(ref resolver) = self.resolver else {
            return self.value.to_py(py);
        };

        // No cache mode (cache_time == 0)
        if self.cache_time == 0 {
            return resolver.call0(py);
        }

        // Check cache
        if !self.is_cache_expired() {
            if let Some(ref cached) = self.cached_value {
                return cached.to_py(py);
            }
        }

        // Cache miss or expired → call resolver
        let result = resolver.call0(py)?;

        // Store in cache
        self.cached_value = Some(BagValue::from_py(&result, py)?);
        self.cache_last_update = Some(Utc::now());

        Ok(result)
    }
}
```

### Rust Implementation with Cache (WASM)

```rust
#[wasm_bindgen]
impl BagNode {
    pub fn get_value(&mut self) -> Result<JsValue, JsValue> {
        // No resolver → return static value
        let Some(ref resolver) = self.resolver else {
            return Ok(self.value.to_js());
        };

        // No cache mode (cache_time == 0)
        if self.cache_time == 0 {
            return resolver.call0(&JsValue::NULL);
        }

        // Check cache
        if !self.is_cache_expired() {
            if let Some(ref cached) = self.cached_value {
                return Ok(cached.to_js());
            }
        }

        // Cache miss or expired → call resolver
        let result = resolver.call0(&JsValue::NULL)?;

        // Store in cache
        self.cached_value = Some(BagValue::from_js(&result)?);
        self.cache_last_update = Some(Utc::now());

        Ok(result)
    }
}
```

### Cache in ResolverMarker (Serialization)

When serializing a resolver with cache state:

```rust
pub struct ResolverMarker {
    resolver_type: String,      // "BagCbResolver", "UrlResolver", etc.
    resolver_module: String,
    args: Vec<BagValue>,
    kwargs: HashMap<String, BagValue>,
    cache_time: i64,            // Serialized
    // Note: cached_value and cache_last_update are NOT serialized
    // Cache is runtime-only, rehydrated resolver starts with empty cache
}
```

### Example: Resolver with Cache

```python
# Python usage
from gnr.core.gnrbag import Bag, BagCbResolver

def fetch_weather():
    # Expensive API call
    return requests.get("https://api.weather.com/london").json()

bag = Bag()

# Cache for 5 minutes (300 seconds)
bag.setItem("weather", BagCbResolver(fetch_weather, cacheTime=300))

# First call → API request, stores in cache
print(bag["weather"])  # Calls fetch_weather()

# Second call within 5 minutes → returns cached value
print(bag["weather"])  # Returns cached result, no API call

# After 5 minutes → cache expired, new API request
time.sleep(301)
print(bag["weather"])  # Calls fetch_weather() again
```

```python
# Infinite cache (cache_time < 0)
bag.setItem("config", BagCbResolver(load_config, cacheTime=-1))

# First call → loads config
print(bag["config"])  # Calls load_config()

# All subsequent calls → always cached (never expires)
print(bag["config"])  # Returns cached result forever
```

## Traversal with Resolvers

The Python `_htraverse` method (gnrbag.py line 766) handles path traversal. When it encounters a resolver during traversal, it calls the resolver to populate the node, then continues.

### Key Insight: `hasattr(newcurr, '_htraverse')`

```python
# From gnrbag.py line 806
isbag = hasattr(newcurr, '_htraverse')
if isbag:
    return newcurr._htraverse(pathlist, ...)
```

Both `Bag` and `BagResolver` have `_htraverse`. When the resolver is called:

```python
# BagResolver._htraverse (line 2727)
def _htraverse(self, *args, **kwargs):
    return self()._htraverse(*args, **kwargs)
    #      ^^^^^ calls resolver, returns Bag, continues traversal
```

### Two Resolver Scenarios

**Case 1: Resolver as Leaf Node (terminal)**

```javascript
bag.get("tabContainer.tab2");  // tab2 IS the resolver
// Fire & forget → async fetch → writes to bag → trigger/builder reacts
// No await needed - purely event-driven
```

**Case 2: Resolver During Traversal (mid-path)**

```javascript
bag.get("alfa.beta.gamma.delta");  // beta is resolver, must reach delta
//        ↓
//      beta: RESOLVER → must wait for it to populate
//        ↓
//      then continue to gamma.delta
// HERE await is needed (or sync)
```

### Sync vs Async Strategy

**Current (Sync)**:
- Python: `requests.post()` blocks
- JavaScript: `XMLHttpRequest` sync (deprecated but works)

**Future (Async)**:
- Python: `await aiohttp.post()`
- JavaScript: `await fetch()`

### Proposed API for WASM

```rust
impl Bag {
    /// Async get - handles resolvers at any path position
    /// Returns Promise in JS
    pub async fn get(&self, path: &str) -> Result<JsValue, JsValue> {
        // During traversal:
        // - If resolver is leaf → fire & forget, return immediately
        // - If resolver is mid-path → await, then continue traversal
    }
}
```

**JavaScript usage**:

```javascript
// Case 1: Leaf resolver (fire & forget)
bag.get("tabContainer.tab2");  // triggers async load
// Builder reacts when data arrives - no need to await

// Case 2: Mid-path resolver (must await)
let value = await bag.get("alfa.beta.gamma.delta");
// Waits for beta to resolve, then returns delta value
```

### Resolver Writes to Target Path

The resolver doesn't return a value - it **writes directly to the Bag**:

```javascript
// Resolver receives target path in params
resolver({ targetPath: "alfa.beta" });

// Resolver internally does:
async function resolver(params) {
    const data = await fetch('/api/data');
    bag.set(params.targetPath, data);  // writes to bag
    // Triggers fire, builder reacts
}
```

This pattern enables **fire & forget** for leaf resolvers while still supporting **await** for mid-path traversal.

## Async Strategy: Fire & Forget with Triggers

### The Reactive Pattern

Genropy uses a **trigger-driven, eventually consistent** model:

1. **Never blocks** - `get()` always returns immediately
2. **Fire & forget** - unresolved resolver starts async load, returns `undefined`
3. **Trigger-driven** - when resolver completes, triggers notify dependents

### DataController Example

```javascript
// DataController declaration
dataController('SET riga.totale = qta * prezzo',
               qta='^.quantity',
               prezzo='^@prodotto_id.price')
```

Where:
- `^.quantity` - reactive binding to quantity (relative path)
- `^@prodotto_id.price` - binding through resolver:
  - `@prodotto_id` is a **resolver** pointing to product record
  - `.price` is a field **inside** the Bag populated by the resolver

### Flow When Product Changes

```
prodotto_id changes
  → cache invalidated, @prodotto_id empties
  → DataController tries to read @prodotto_id.price
  → @prodotto_id not resolved → resolver fires (fire & forget)
  → get returns undefined
  → formula CANNOT compute → riga.totale stays unchanged

  ... async server call ...

  → server responds
  → resolver populates @prodotto_id with product Bag
  → trigger fires on @prodotto_id.price (it changed!)
  → DataController re-fires
  → this time @prodotto_id.price EXISTS
  → formula computes → SET riga.totale = qta * prezzo
```

### Nested Resolvers (Edge Case)

Theoretically possible:

```javascript
bag.get("@prodotto_id.@listino_id.prezzo")
//       ↓              ↓
//    resolver 1    resolver 2 (inside product)
```

This requires **N round-trips** for N nested resolvers:

```
get("@prodotto_id.@listino_id.prezzo")

→ @prodotto_id not resolved
→ fire resolver (product)
→ return undefined
→ STOP (can't even KNOW @listino_id exists!)

... product arrives ...

→ trigger on @prodotto_id
→ DataController re-fires
→ get("@prodotto_id.@listino_id.prezzo")
→ @prodotto_id RESOLVED, traverse...
→ @listino_id not resolved
→ fire resolver (listino)
→ return undefined
→ STOP

... listino arrives ...

→ trigger on @prodotto_id.@listino_id
→ DataController re-fires
→ get("@prodotto_id.@listino_id.prezzo")
→ everything resolved → return 42.50
```

### Why Nested Resolvers Are Rare in Practice

**SQL joins avoid the N round-trip problem**:

```python
# Instead of nested resolvers (slow):
bag.get("@prodotto_id.@listino_id.prezzo")  # 2 resolvers = 2 round-trips

# Use SQL join to bring data in one fetch:
SELECT
    r.*,
    p.name AS product_name,
    p.price AS product_price,      -- joined from product
    l.prezzo AS listino_prezzo     -- joined from listino
FROM righe r
JOIN prodotti p ON r.prodotto_id = p.id
JOIN listini l ON p.listino_id = l.id
```

Genropy's mapper with `@prodotto_id.price AS product_price` generates the join automatically.

### Comparison: Sync (Today) vs Async (Rust/WASM)

**Today (JS synchronous)**:

```
@prodotto_id.@listino_id.prezzo (discouraged!)

→ resolver 1 → BLOCKS UI → waits server → ok
→ resolver 2 → BLOCKS UI → waits server → ok
→ finally get price

Total time: latency1 + latency2 (UI BLOCKED!)
```

**With Rust/WASM (fire & forget)**:

```
@prodotto_id.@listino_id.prezzo

→ resolver 1 → fire & forget → return undefined (UI FREE!)
... server responds, trigger ...
→ resolver 2 → fire & forget → return undefined (UI FREE!)
... server responds, trigger ...
→ price available

Total time: latency1 + latency2 (but UI NEVER blocked)
```

### Benefits of Fire & Forget

Same total latency for data, but:
- ✅ UI always responsive
- ✅ Other calculations/renders can proceed
- ✅ Consistent pattern (always fire & forget)
- ✅ Nested resolvers remain discouraged for latency, but at least don't block

### Rust Implementation

```rust
impl Bag {
    /// Get value at path - never blocks, fire & forget for unresolved resolvers
    pub fn get(&self, path: &str) -> JsValue {
        for segment in path.segments() {
            match self.traverse(segment) {
                Node::Value(v) => continue,
                Node::Resolver(r) if r.is_resolved() => continue,
                Node::Resolver(r) => {
                    // Unresolved: fire async load, return immediately
                    r.fire();  // spawns Promise/async task
                    return JsValue::UNDEFINED;
                }
                Node::NotFound => return JsValue::UNDEFINED,
            }
        }
        // Complete path traversed, return value
        self.current_value()
    }
}
```

The resolver's `fire()` method:
1. Spawns async fetch (Promise in JS, async task in Rust)
2. On completion, calls `bag.set(target_path, data)`
3. `set()` fires triggers
4. Triggers cause DataController to re-evaluate

## Serialization: MessagePack

Primary format with Extension Types:

| Ext Type | Code | Rust Type |
|----------|------|-----------|
| 1 | N | Decimal |
| 2 | D | Date |
| 3 | DH | DateTime |
| 4 | H | Time |
| 5 | CALLABLE | CallableMarker |
| 6 | RESOLVER | ResolverMarker |

**BagNode format**: `[label, value, attrs]` (3-element array)

## Localization

Two localization patterns, both handled **during serialization** (not regex post-processing):

### Pattern 1: UI Strings (`!![lang]`)

Global dictionary for application strings:

```
!![lang]Text to translate
!![en]Book  →  "Libro" (if target_lang="it")
```

Can appear in **both values and attributes**:

```xml
<node label="!![en]Name" tooltip="!![en]Help">!![en]Book</node>
```

**Dictionary Format** (JSON, ~5k entries, ~1MB):

```json
{
  "en_user_not_allowed": {
    "base": "User not allowed",
    "it": "Utente non autorizzato",
    "de": "Benutzer nicht erlaubt"
  }
}
```

### Pattern 2: Record Translations (`_translations`)

Multilingual data from DB records. The `_translations` field contains per-field translations:

```python
# DB record
{
    "id": 123,
    "name": "Widget Pro",
    "description": "A great widget",
    "_translations": {
        "name": {"it": "Widget Pro", "de": "Widget Pro"},
        "description": {"it": "Un ottimo widget", "de": "Ein tolles Widget"}
    }
}
```

**Serialization behavior**:

1. `_translations` is a **sibling field** in the Bag (not per-node attribute)
2. Serializer extracts `_translations`, does **NOT** emit it
3. For each sibling field, checks if translation exists for target language
4. Emits translated value (or original as fallback)

```python
def serialize_bag(bag, localizer):
    translations = bag.pop("_translations", None)  # extract and remove

    for node in bag.nodes():
        value = node.value

        # Pattern 1: UI strings
        if isinstance(value, str) and value.startswith("!!["):
            value = localizer.translate_ui(value)

        # Pattern 2: Record translations
        if translations and node.label in translations:
            value = localizer.translate_record(value, translations[node.label])

        # ... serialize node with translated value
```

### Rust Implementation

```rust
pub struct Localizer {
    dict: HashMap<String, HashMap<String, String>>,  // UI strings
    target_lang: String,
}

impl Localizer {
    pub fn from_json(json: &str, target_lang: &str) -> Self;

    /// Translate !![lang]text pattern
    pub fn translate_ui(&self, text: &str) -> Cow<str>;

    /// Translate using record's _translations
    pub fn translate_record(&self, value: &str, field_translations: &HashMap<String, String>) -> Cow<str> {
        field_translations
            .get(&self.target_lang)
            .map(|s| Cow::Borrowed(s.as_str()))
            .unwrap_or(Cow::Borrowed(value))
    }
}
```

### Why Localize During Serialization (Not Regex Post-Processing)

Since `!![lang]` appears in **both values and attributes**, regex on XML/JSON becomes fragile:
- Must match `="!![en]..."` (attributes) AND `>!![en]...<` (values)
- Must handle XML escaping (`&amp;`, `&lt;`, etc.)
- Risk of breaking on CDATA, comments, edge cases

**Better**: Pass `Localizer` to serializer, translate each string as it's written. One pass, clean code, no regex on structured data.

## Python Wrapper Pattern

```python
class Bag:
    def __init__(self):
        self._rust = RustBag()      # Rust core
        self._resolvers = {}        # Python resolvers by path
        self._triggers = {}         # Python triggers by path

    def setItem(self, path, value, **attrs):
        if isinstance(value, BagResolver):
            marker = value.to_marker()
            self._rust.set_item(path, marker, attrs)
            self._resolvers[path] = value
        else:
            self._rust.set_item(path, value, attrs)

    def getValue(self, path):
        value = self._rust.get_value(path)
        if isinstance(value, ResolverMarker) and path in self._resolvers:
            return self._resolvers[path]()
        return value

    def toMessagePack(self, localizer=None):
        return self._rust.to_msgpack(localizer)
```

## JS Wrapper Pattern (WASM)

```javascript
class GnrBag {
    constructor() {
        this._rust = new wasm.Bag();
        this._triggers = new Map();
    }

    setItem(path, value, attrs) {
        this._rust.setItem(path, value, attrs);
        this._fireTriggers(path);
    }

    subscribe(path, callback) {
        this._triggers.set(path, callback);
    }
}
```

## Dependencies

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
rmp-serde = "1.1"           # MessagePack
serde_json = "1.0"
chrono = { version = "0.4", features = ["serde"] }
rust_decimal = { version = "1.33", features = ["serde"] }
pyo3 = { version = "0.20", optional = true }
wasm-bindgen = { version = "0.2", optional = true }

[features]
python = ["pyo3"]
wasm = ["wasm-bindgen"]
```

## Migration Phases

1. Core data structure (Bag, BagNode, BagValue)
2. Path operations (get/set/delete)
3. MessagePack serialization
4. Localization
5. Python bindings (PyO3)
6. WASM bindings
7. Legacy XML/JSON compat (if needed)

## Open Questions

- [ ] XML serialization in Rust or Python-only?
- [ ] Hierarchical path syntax (`#^`, `#parent`)?
- [ ] Validators as markers or host-only?
- [ ] WASM cold start impact?

## References

- `gnrbag.py` - Python implementation
- `gnrbag.js` - JS implementation
- `gnrbagxml.py` - XML serializer
- `gnrlocalization.py` - Localization system
- `localization.xml` - Translation dictionary

---

**Note**: Discussion document only. No implementation decisions are final.
