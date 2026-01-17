# Builders

Domain-specific fluent APIs: HTML, Markdown, XML Schema, custom DSLs.

## When Do You Need Builders?

- **Structure has rules**: HTML, XML, configuration schemas
- **Validation at build time**: Catch errors early, not at runtime
- **Domain vocabulary**: Methods like `div()`, `p()` instead of `set_item()`
- **Output generation**: Compile to HTML, Markdown, XML

## Quick Start

```python
from genro_bag import Bag
from genro_bag.builders import HtmlBuilder

html = Bag(builder=HtmlBuilder)
div = html.div(id='main')
div.p(value='Hello World')

print(html.to_xml(pretty=True))
# <div id="main">
#   <p>Hello World</p>
# </div>
```

## The Key Insight

Without a builder:
```python
bag = Bag()
bag.set_item('div', Bag())
bag['div'].set_item('p', 'Hello')  # No validation, no structure
```

With a builder:
```python
html = Bag(builder=HtmlBuilder)
div = html.div()       # Returns Bag for children
div.p(value='Hello')   # Validated, returns BagNode
div.invalid()          # Error! 'invalid' not in HTML schema
```

## Built-in Builders

| Builder | Purpose |
|---------|---------|
| `HtmlBuilder` | HTML5 with 112 tags |
| `MarkdownBuilder` | Markdown generation |
| `XsdBuilder` | From XML Schema files |

## Return Types

- **Container elements** (can have children) → return `Bag`
- **Leaf elements** (no children) → return `BagNode`

```python
div = html.div()     # Bag - can add children
meta = html.meta()   # BagNode - leaf element
```

## Labels and Tags

Every node has both:
- **Label**: Unique identifier (`div_0`, `div_1`) for path access
- **Tag**: Semantic type (`div`, `p`) for validation

```python
html.div()
html.div()
list(html.keys())  # ['div_0', 'div_1']

# Use node_label for explicit labels
html.div(node_label='header')
html['header']  # Access by label
```

## Custom Builders

```python
from genro_bag.builders import BagBuilderBase, element

class MenuBuilder(BagBuilderBase):
    @element(sub_tags='item,separator')
    def menu(self): ...

    @element()
    def item(self, label='', action=''): ...

    @element()
    def separator(self): ...

menu = Bag(builder=MenuBuilder)
m = menu.menu()
m.item(label='Open', action='open_file')
m.separator()
m.item(label='Exit', action='quit')
```

## Output Generation

### HTML/XML

```python
html.to_xml(pretty=True)
```

### Markdown

```python
doc = Bag(builder=MarkdownBuilder)
doc.h1("Title")
doc.p("Content")
doc.builder.compile()  # Returns markdown string
```

## Documentation

- [Quick Start](quickstart.md) — Get started in 5 minutes
- [Custom Builders](custom-builders.md) — Create your own
- [HTML Builder](html-builder.md) — Full HTML5 support
- [Markdown Builder](markdown-builder.md) — Document generation
- [XSD Builder](xsd-builder.md) — XML Schema support
- [Examples](examples.md) — Practical patterns
- [FAQ](faq.md) — Common questions

## Related

- **Need dynamic values?** → [Resolvers](../resolvers/)
- **Need change reactions?** → [Subscriptions](../subscriptions/)
