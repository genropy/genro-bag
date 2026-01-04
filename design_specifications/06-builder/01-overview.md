# Builder System Overview

**Version**: 0.1.0
**Last Updated**: 2026-01-04
**Status**: 🔴 DA REVISIONARE

---

## Obiettivo

Portare il sistema Builder da `genro-treestore` a `genro-bag` per fornire API domain-specific fluide per la creazione di nodi.

---

## Approccio Originale Genropy: gnrstructures.py

Il file `/gnrpy/gnr/core/gnrstructures.py` contiene l'implementazione originale del pattern di strutture funzionali in Genropy.

### GnrStructData

Sottoclasse di Bag che implementa la sintassi funzionale:

```python
class GnrStructData(Bag):
    default_childname = '*_#'  # Pattern per auto-naming: tag_numero

    def child(self, tag, childname=None, childcontent=None, content=None,
              _parentTag=None, _attributes=None, _returnStruct=True,
              _position=None, _childcounter=False, **kwargs):
        """Crea un nuovo item del tipo `tag` nella struttura."""
        # Auto-genera nome: childname.replace('*', tag).replace('#', len(where))
        # Se childcontent è None e _returnStruct=True, crea nuova istanza
        # Supporta posizionamento con _position
        ...
```

**Caratteristiche chiave**:
- `default_childname = '*_#'` → sostituito con `tag_n` (es. `div_0`, `div_1`)
- `child()` metodo centrale per creare nodi
- Validazione children con decorator `@valid_children`
- `validate()` per controllare struttura dopo costruzione

### Decorator @valid_children

```python
def valid_children(**kwargs):
    def decore(func):
        setattr(func, '_valid_children', kwargs)
        return func
    return decore
```

Uso:
```python
@valid_children(div=True, span='0:3', p='1:')
def container(self, ...):
    ...
```

Sintassi cardinality: `'min:max'`
- `True` o `'0:'` → zero o più
- `'1:'` → almeno uno
- `':3'` → massimo 3
- `'1:3'` → da 1 a 3

### GnrStructObj

Classe che costruisce un albero di oggetti Python a partire da GnrStructData:

```python
class GnrStructObj(GnrObject):
    def __init__(self, tag=None, structnode=None, parent=None, ...):
        self.structnode = structnode
        self.children = GnrDict()
        # Costruisce figli ricorsivamente
        self.buildChildren(children)
```

**Pattern**:
- `structnode` → riferimento al BagNode sorgente
- `objclassdict` → dizionario che mappa tag → classe
- Lookup case-insensitive dei tag

### Differenze con TreeStore Builder

| Aspetto | gnrstructures.py | TreeStore Builder |
|---------|------------------|-------------------|
| Base class | `GnrStructData(Bag)` | `BuilderBase` separato |
| Naming | `*_#` pattern | `tag_n` pattern |
| Validazione | `@valid_children` | `@element(children=...)` |
| Cardinality | `'min:max'` string | `tag[min:max]` slice syntax |
| Timing | Post-hoc con `validate()` | In costruzione |
| Type hints | No | Sì, con parsing automatico |

---

## Il Pattern Builder Completo

Il Builder non serve solo per **costruire** la struttura, ma anche per **renderizzare/trasformare** la Bag secondo regole specifiche del dominio.

```
Builder = Costruzione + Validazione + Rendering
```

### Tre Responsabilità

1. **Costruzione**: Metodi fluidi per creare nodi (`bag.div()`, `bag.table()`)
2. **Validazione**: Regole su children ammessi e cardinality
3. **Rendering**: Trasformazione della struttura in output specifico

### Esempi di Builder

| Builder | Costruzione | Rendering |
|---------|-------------|-----------|
| HtmlBuilder | `store.div()`, `store.span()` | → HTML string |
| XmlBuilder | `store.element()` | → XML string |
| SqlBuilder | `store.table()`, `store.column()` | → SQL DDL |
| JsonSchemaBuilder | `store.object()`, `store.array()` | → JSON Schema |
| ConfigBuilder | `store.section()`, `store.setting()` | → INI/YAML/TOML |

### Metodo `render()` Generico

Ogni Builder può implementare un metodo `render()` (o `to_*()`) che trasforma la struttura:

```python
class HtmlBuilder(BuilderBase):
    def to_html(self, store) -> str:
        """Trasforma TreeStore/Bag in HTML."""
        lines = []
        for node in store.nodes:
            tag = node.tag or node.label.rsplit('_', 1)[0]
            attrs = ' '.join(f'{k}="{v}"' for k, v in node.attr.items())
            if node.is_branch:
                lines.append(f"<{tag} {attrs}>")
                lines.append(self.to_html(node.value))  # ricorsione
                lines.append(f"</{tag}>")
            else:
                lines.append(f"<{tag} {attrs}>{node.value}</{tag}>")
        return '\n'.join(lines)
```

### Pattern in TreeStore

In `genro-treestore/builders/html.py`:

```python
class HtmlBuilder(BuilderBase):
    def to_html(self, filename=None, output_dir=None) -> str:
        """Generate complete HTML."""
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            self._store_to_html(self.head, "head"),
            self._store_to_html(self.body, "body"),
            "</html>",
        ]
        return "\n".join(html_lines)

    def _store_to_html(self, store, tag, indent=0):
        """Helper ricorsivo per convertire store in HTML."""
        ...

    def _node_to_html(self, node, indent):
        """Renderizza singolo nodo."""
        ...
```

### Ereditarietà del Builder

**Caratteristica fondamentale**: Il builder è ereditato dal parent, ma può essere sovrascritto a qualsiasi livello.

```python
# Bag root con HtmlBuilder
page = Bag(builder=HtmlBuilder())
body = page.body()           # Eredita HtmlBuilder
div = body.div(id='main')    # Eredita HtmlBuilder

# Sottosezione con SvgBuilder diverso
svg = div.child('svg', _builder=SvgBuilder())  # Override!
svg.circle(cx=50, cy=50, r=40)  # Usa SvgBuilder
svg.rect(x=10, y=10)            # Usa SvgBuilder

# Torna al builder ereditato
div.p('Testo normale')  # Usa ancora HtmlBuilder
```

**Meccanismo**:

1. Quando si crea una child Bag, eredita `_builder` dal parent
2. Il parametro `_builder` permette di sovrascrivere per quel sottoalbero
3. Ogni Bag conosce il proprio builder tramite `self._builder`
4. Il rendering può attraversare builder diversi

**Casi d'uso**:

| Scenario | Builder Parent | Builder Child |
|----------|----------------|---------------|
| HTML con SVG embedded | HtmlBuilder | SvgBuilder |
| HTML con MathML | HtmlBuilder | MathMLBuilder |
| Config con schema | ConfigBuilder | JsonSchemaBuilder |
| XML con namespace | XmlBuilder | CustomNsBuilder |

### Implicazioni per genro-bag

Il Builder in genro-bag dovrà supportare:

1. **Ereditarietà**: Child bag eredita builder dal parent
2. **Override**: Parametro `_builder` in `child()` e `set_item()`
3. **`BuilderBase.render(bag)`** - metodo astratto/generico
4. **Rendering multi-builder**: `render()` deve rispettare i builder ai vari livelli
5. **Accesso al builder**: `bag.builder` property

---

## Cos'è il Builder Pattern in TreeStore

Il Builder è un sistema che permette di creare nodi in modo fluido e type-safe:

```python
from genro_treestore import TreeStore
from genro_treestore.builders import HtmlBuilder

store = TreeStore(builder=HtmlBuilder())
body = store.body()              # Crea nodo con tag='body'
div = body.div(id='main')        # Crea nodo con tag='div', attr={'id': 'main'}
div.h1(value='Hello World')      # Crea leaf node con tag='h1'
```

**Meccanismo**:
1. `store.body()` → `TreeStore.__getattr__('body')`
2. Delegato a `HtmlBuilder.__getattr__('body')`
3. HtmlBuilder crea handler che chiama `BuilderBase.child()`
4. `child()` crea `TreeStoreNode` con `tag='body'`
5. Ritorna child store (per aggiungere figli)

---

## Architettura in TreeStore

### Struttura Directory

```
genro-treestore/src/genro_treestore/builders/
├── __init__.py          # Export BuilderBase, element
├── base.py              # BuilderBase (533 linee)
├── decorators.py        # @element decorator (349 linee)
├── html.py              # HtmlBuilder (150 linee)
└── xsd/                 # XsdBuilder per XML Schema
```

### Componenti Principali

#### 1. `decorators.py` - Completamente Generico

Funzioni per validazione e parsing:

| Funzione | Scopo |
|----------|-------|
| `_parse_tag_spec(spec)` | Parser cardinality: `tag[1:]`, `tag[:3]`, `tag[1:3]` |
| `_parse_tags(tags)` | Comma-separated string → lista |
| `_annotation_to_attr_spec()` | Type hint → spec dict |
| `_extract_attrs_from_signature()` | Estrae attrs dalla signature |
| `_validate_attrs_from_spec()` | Valida kwargs runtime |
| `element(children=, tags=)` | Decorator principale |

**Dipendenze**: Solo stdlib (`inspect`, `functools`, `typing`)

#### 2. `base.py` - BuilderBase

Classe astratta con:

| Metodo/Attributo | Scopo | Generico? |
|------------------|-------|-----------|
| `_element_tags: dict` | Mapping tag → metodo | ✅ |
| `_schema: dict` | Schema elementi | ✅ |
| `__init_subclass__()` | Scansiona metodi decorati | ✅ |
| `__getattr__(name)` | Lookup in _element_tags e _schema | ✅ |
| `_validate_attrs()` | Validazione attributi | ✅ |
| `_resolve_ref()` | Risoluzione `=ref` | ✅ |
| `_parse_children_spec()` | Parser children spec | ✅ |
| `check(store)` | Validazione struttura | ✅ (usa store.nodes()) |
| `child(target, tag, ...)` | Crea nodi | ⚠️ ADATTARE |

#### 3. `html.py` - HtmlBuilder (Specifico)

- Carica schema HTML5 da MessagePack
- Non portabile direttamente (specifico per HTML)

---

## Stato Attuale in genro-bag

### Già Presente

| Componente | File | Note |
|------------|------|------|
| `BagNode.tag` | `bag_node.py:96` | Già negli `__slots__`, inizializzato in `__init__` |
| `Bag.get_nodes()` | `bag.py` | Per iterare sui nodi |
| `BagNode._invalid_reasons` | `bag_node.py` | Per tracking errori validazione |

### Da Implementare

| Componente | File | Note |
|------------|------|------|
| `Bag._builder` | `bag.py` | Slot + init parameter |
| `Bag.__getattr__()` | `bag.py` | Delegazione al builder |
| `Bag.builder` property | `bag.py` | Accesso al builder |
| `builders/` directory | Nuova | BuilderBase, decorators |

---

## Differenze TreeStore vs Bag

| Aspetto | TreeStore | Bag |
|---------|-----------|-----|
| Classe container | `TreeStore` | `Bag` |
| Classe nodo | `TreeStoreNode` | `BagNode` |
| Parent reference | `node.parent` (TreeStore) | `node.parent` (Bag) |
| Tag support | `TreeStoreNode.tag` | `BagNode.tag` ✅ |
| Subscriptions | `_upd/_ins/_del` | `_upd/_ins/_del` ✅ |
| Builder param | `TreeStore(builder=...)` | Da aggiungere |
| `__getattr__` | Delega al builder | Da aggiungere |

---

## Cosa Portare in genro-bag

### Copiare As-Is (Zero Modifiche)

1. **`decorators.py`** - Completamente indipendente
   - Nessuna dipendenza da TreeStore
   - 349 linee, tutte generiche

### Adattare

1. **`BuilderBase`** da `base.py`:
   - Cambiare type hints: `TreeStore` → `Bag`, `TreeStoreNode` → `BagNode`
   - Metodo `child()`: creare `Bag` e `BagNode` invece di TreeStore/TreeStoreNode

### Non Portare

1. **`HtmlBuilder`** - Specifico per HTML
2. **`XsdBuilder`** - Specifico per XSD

---

## Esempio Uso Futuro

```python
from genro_bag import Bag
from genro_bag.builders import BuilderBase, element

class ConfigBuilder(BuilderBase):
    @element(children='section, setting')
    def config(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(children='setting')
    def section(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(leaf=True)
    def setting(self, target, tag, value=None, **attr):
        return self.child(target, tag, value=value, **attr)

# Uso
bag = Bag(builder=ConfigBuilder())
cfg = bag.config(name='app')
db = cfg.section(name='database')
db.setting(value='localhost', key='host')
db.setting(value=5432, key='port')
```

---

## Riferimenti

- TreeStore builder: `/Users/gporcari/Sviluppo/genro_ng/meta-genro-modules/sub-projects/genro-treestore/src/genro_treestore/builders/`
- BagNode con tag: `src/genro_bag/bag_node.py:96`
