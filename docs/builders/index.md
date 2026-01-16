# Builders System

The Builders system provides **domain-specific fluent APIs** for constructing Bag structures with validation support. Instead of manually calling `set_item()`, builders let you use intuitive method calls that match your domain vocabulary.

## Why Builders?

Without a builder, constructing a nested structure requires explicit paths:

```python
from genro_bag import Bag

bag = Bag()
bag.set_item('div', Bag())
div_bag = bag['div']
div_bag.set_item('p', 'Hello World')
```

With a builder, the same structure becomes natural and readable:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder
>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(id='main')
>>> p = div.p(value='Hello World')
>>> p.tag
'p'
```

## Key Concepts

### Fluent API Pattern

Builders use the **fluent API pattern**: each method returns something you can chain or continue building from:

- **Branch nodes** (containers) return a new `Bag` for adding children
- **Leaf nodes** (values) return the `BagNode` itself

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder
>>> bag = Bag(builder=HtmlBuilder)
>>> # div() returns a Bag (branch) - you can add children
>>> container = bag.div()
>>> type(container).__name__
'Bag'
>>> # meta() returns a BagNode (leaf) - it has a value
>>> meta = container.meta(charset='utf-8')
>>> type(meta).__name__
'BagNode'
```

### Tags vs Labels

Every node has both a **label** (unique identifier) and a **tag** (semantic type):

- **Label**: Auto-generated as `tag_N` (e.g., `div_0`, `div_1`) - used for path access
- **Tag**: The semantic type (e.g., `div`, `p`, `meta`) - used for validation

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder
>>> bag = Bag(builder=HtmlBuilder)
>>> div1 = bag.div()
>>> div2 = bag.div()
>>> list(bag.keys())
['div_0', 'div_1']
```

```{warning}
**Avoid relying on auto-generated labels** like `div_0`, `div_1` in production code.
They depend on insertion order and are fragile. Instead:

1. **Save references** returned by builder methods (e.g., `div1 = bag.div()`)
2. **Use `node_label`** for explicit labels: `bag.div(node_label='main')`
3. **Iterate by tag**: `[n for n in bag if n.tag == 'div']`
```

```{doctest}
>>> # Preferred: use saved references
>>> div1.span(value='First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div2.span(value='Second')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> # Or use explicit node_label
>>> nav = bag.nav(node_label='main_nav')
>>> bag['main_nav']  # Stable path
<genro_bag.bag.Bag object at ...>
```

### Two Ways to Define Elements

Builders support two complementary approaches:

1. **Decorated Methods** - Using `@element` decorator for full control:

   ```python
   from genro_bag.builders import BagBuilderBase, element

   class MenuBuilder(BagBuilderBase):
       @element(sub_tags='item,separator')
       def menu(self, target, tag, **attr):
           return self.child(target, tag, **attr)
   ```

2. **Simple Elements** - Using empty method bodies for elements without custom logic:

   ```python
   class TableBuilder(BagBuilderBase):
       @element(sub_tags='tr[]')
       def table(self): ...

       @element(sub_tags='td[],th[]')
       def tr(self): ...

       @element()
       def td(self): ...
   ```

Both approaches can be combined in the same builder.

```{important}
**Schemas are never created manually.** If you need to load a schema from a file,
use `builder_schema_path` with a `.bag.mp` file created by the schema builder tools.
Do not create JSON or dictionary schemas by hand - always use `@element` decorators
or schema builder utilities.
```

## Built-in Builders

### HtmlBuilder

Complete HTML5 support with 112 tags loaded from W3C schema:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder
>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(id='main')
>>> div.p(value='Hello World')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### MarkdownBuilder

Build Markdown documents programmatically with `compile()` to generate the final output:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import MarkdownBuilder
>>> doc = Bag(builder=MarkdownBuilder)
>>> doc.h1("My Document")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.p("Introduction paragraph.")  # doctest: +ELLIPSIS
BagNode : ...
>>> md = doc.builder.compile()
>>> "# My Document" in md
True
```

See [Markdown Builder](markdown-builder.md) for complete documentation.

### XsdBuilder

Dynamic builder from XML Schema (XSD) files - automatically generates methods for all elements defined in the schema:

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Use with Bag - pass XSD file path via builder_xsd_source
invoice = Bag(builder=XsdBuilder, builder_xsd_source='invoice.xsd')
invoice.Invoice().Header().Date(value='2025-01-01')
```

See [XSD Builder](xsd-builder.md) for complete documentation.

## Documentation

```{toctree}
:maxdepth: 2

quickstart
custom-builders
html-builder
markdown-builder
xsd-builder
validation
advanced
```
