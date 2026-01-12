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
>>> # Access by label path
>>> list(bag.keys())
['div_0', 'div_1']
>>> # Add content to distinguish them
>>> div1.span(value='First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div2.span(value='Second')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag['div_0.span_0']
'First'
>>> bag['div_1.span_0']
'Second'
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

## Built-in Builders

### HtmlBuilder

Complete HTML5 support with 112 tags loaded from W3C schema:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder
>>> builder = HtmlBuilder()
>>> len(builder.ALL_TAGS) > 100
True
>>> 'div' in builder.ALL_TAGS
True
>>> 'br' in builder.VOID_ELEMENTS  # Self-closing
True
```

### HtmlPage

Complete HTML document structure with head and body:

```{doctest}
>>> from genro_bag.builders import HtmlPage
>>> page = HtmlPage()
>>> page.head.title(value='My Page')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.div().p(value='Hello')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> html = page.to_html()
>>> '<!DOCTYPE html>' in html
True
>>> '<title>My Page</title>' in html
True
```

### XsdBuilder

Dynamic builder from XML Schema (XSD) files - automatically generates methods for all elements defined in the schema:

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Load any XSD schema
xsd_content = open('invoice.xsd').read()
schema = Bag.from_xml(xsd_content)
builder = XsdBuilder(schema)

# Use with Bag - methods generated from XSD
invoice = Bag(builder=builder)
invoice.Invoice().Header().Date(value='2025-01-01')
```

See [XSD Builder](xsd-builder.md) for complete documentation.

## Documentation

```{toctree}
:maxdepth: 2

quickstart
custom-builders
html-builder
xsd-builder
validation
advanced
```
