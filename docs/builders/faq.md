# Builders FAQ

## Basic Questions

### What's the difference between a builder and a Bag?

- **Bag**: General-purpose hierarchical container
- **Builder**: Adds domain-specific methods and validation rules to a Bag

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> # Plain Bag - no structure rules
>>> plain = Bag()
>>> plain['anything'] = 'goes'

>>> # With builder - domain-specific methods
>>> html = Bag(builder=HtmlBuilder)
>>> html.div().p(value='Structured')  # doctest: +ELLIPSIS
BagNode : ...
```

### Why do methods like `div()` return a Bag, but `p()` returns a BagNode?

Elements with allowed children (containers) return a Bag so you can add children.
Elements without children (leaves) return the BagNode itself.

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> div = html.div()  # Container - returns Bag
>>> type(div).__name__
'Bag'

>>> meta = html.meta(charset='utf-8')  # Leaf - returns BagNode
>>> type(meta).__name__
'BagNode'
```

### How do I access the node value?

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> p = html.p(value='Hello')
>>> p.value
'Hello'
```

### How do I access node attributes?

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> div = html.div(id='main', class_='container')
>>> node = html.get_node('div_0')
>>> node.attr
{'id': 'main', 'class_': 'container'}
```

## Labels and Paths

### Why are labels like `div_0`, `div_1`?

Auto-generated labels use `tag_index` format for uniqueness:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> html.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> html.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> list(html.keys())
['div_0', 'div_1']
```

### How do I use custom labels?

Use `node_label`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> html.div(node_label='header')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> html.div(node_label='footer')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> list(html.keys())
['header', 'footer']
>>> html['header']  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
```

### How do I find elements by tag?

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> html.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> html.p(value='text')  # doctest: +ELLIPSIS
BagNode : ...
>>> html.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>

>>> divs = [n for n in html if n.tag == 'div']
>>> len(divs)
2
```

## Validation

### When does validation happen?

At build time - invalid children are rejected immediately:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class StrictBuilder(BagBuilderBase):
...     @element(sub_tags='item')
...     def list(self): ...
...     @element()
...     def item(self): ...
...     @element()
...     def other(self): ...

>>> bag = Bag(builder=StrictBuilder)
>>> l = bag.list()
>>> l.item()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>

>>> # 'other' is not allowed inside 'list'
>>> try:
...     l.other()
... except Exception as e:
...     'not allowed' in str(e).lower() or 'invalid' in str(e).lower()
True
```

### How do I check for errors after building?

Use `builder.check()`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class MyBuilder(BagBuilderBase):
...     @element(sub_tags='child')
...     def parent(self): ...
...     @element()
...     def child(self): ...

>>> bag = Bag(builder=MyBuilder)
>>> p = bag.parent()

>>> errors = bag.builder.check(p, parent_tag='parent')
>>> errors
[]
```

### Can I disable validation?

Not directly, but you can use plain Bag for unstructured content.

## Output Generation

### How do I generate HTML/XML?

Use `bag.to_xml()`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> html = Bag(builder=HtmlBuilder)
>>> html.div().p(value='Hello')  # doctest: +ELLIPSIS
BagNode : ...

>>> xml = html.to_xml(pretty=True)
>>> print(xml)  # doctest: +SKIP
<div>
  <p>Hello</p>
</div>
```

### How do I generate Markdown?

Use `builder.compile()`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import MarkdownBuilder

>>> doc = Bag(builder=MarkdownBuilder)
>>> doc.h1("Title")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.p("Content")  # doctest: +ELLIPSIS
BagNode : ...

>>> md = doc.builder.compile()
>>> print(md)
# Title
<BLANKLINE>
Content
```

## Custom Builders

### How do I create a simple builder?

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class SimpleBuilder(BagBuilderBase):
...     @element(sub_tags='item[]')
...     def container(self): ...
...
...     @element()
...     def item(self, node_value=''): ...

>>> bag = Bag(builder=SimpleBuilder)
>>> c = bag.container()
>>> c.item(node_value='First')  # doctest: +ELLIPSIS
BagNode : ...
>>> c.item(node_value='Second')  # doctest: +ELLIPSIS
BagNode : ...
```

### What does `sub_tags` mean?

Defines which child elements are allowed:

```python
# Single allowed child
@element(sub_tags='child')

# Multiple allowed children
@element(sub_tags='a,b,c')

# With cardinality
@element(sub_tags='child[]')     # Unlimited
@element(sub_tags='child[:1]')   # At most 1
@element(sub_tags='child[1:]')   # At least 1
@element(sub_tags='child[2:5]')  # Between 2 and 5
```

### How do I add custom parameters?

Add parameters to the method signature:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class MyBuilder(BagBuilderBase):
...     @element()
...     def field(self, name='', required: bool = False): ...

>>> bag = Bag(builder=MyBuilder)
>>> bag.field(name='email', required=True)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>

>>> node = bag.get_node('field_0')
>>> node.attr['required']
True
```
