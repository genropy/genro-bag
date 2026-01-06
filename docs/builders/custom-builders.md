# Creating Custom Builders

This guide shows how to create your own domain-specific builders.

## Basic Structure

Every builder extends `BagBuilderBase` and defines elements using either:

1. The `@element` decorator (recommended for complex logic)
2. The `_schema` dictionary (simpler, declarative)

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class RecipeBuilder(BagBuilderBase):
...     """Builder for cooking recipes."""
...
...     @element(children='ingredient, step')
...     def recipe(self, target, tag, title=None, **attr):
...         """Create a recipe container."""
...         if title:
...             attr['title'] = title
...         return self.child(target, tag, **attr)
...
...     @element()
...     def ingredient(self, target, tag, value=None, amount=None, unit=None, **attr):
...         """Add an ingredient."""
...         if amount:
...             attr['amount'] = amount
...         if unit:
...             attr['unit'] = unit
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def step(self, target, tag, value=None, **attr):
...         """Add a cooking step."""
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=RecipeBuilder())
>>> recipe = bag.recipe(title='Pasta Carbonara')
>>> recipe.ingredient(value='Spaghetti', amount='400', unit='g')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> recipe.ingredient(value='Eggs', amount='4', unit='units')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> recipe.step(value='Boil the pasta')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> recipe['ingredient_0?amount']
'400'
```

## The @element Decorator

### Basic Usage

The simplest form just marks a method as an element handler:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class SimpleBuilder(BagBuilderBase):
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=SimpleBuilder())
>>> bag.item(value='test')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Multiple Tags for One Method

Use `tags` to handle multiple tag names with one method:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class KitchenBuilder(BagBuilderBase):
...     @element(tags='fridge, oven, dishwasher, microwave')
...     def appliance(self, target, tag, brand=None, **attr):
...         """Any kitchen appliance."""
...         if brand:
...             attr['brand'] = brand
...         return self.child(target, tag, value='', **attr)

>>> bag = Bag(builder=KitchenBuilder())
>>> bag.fridge(brand='Samsung')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.oven(brand='Bosch')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.microwave()  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> fridge = bag['fridge_0']  # Returns None (empty branch)
>>> bag['oven_0?brand']
'Bosch'
```

### Specifying Valid Children

Use `children` to define what child elements are allowed:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(children='section, paragraph')
...     def document(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(children='paragraph, list')
...     def section(self, target, tag, title=None, **attr):
...         if title:
...             attr['title'] = title
...         return self.child(target, tag, **attr)
...
...     @element()
...     def paragraph(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element(children='item')
...     def list(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=DocumentBuilder())
>>> doc = bag.document()
>>> sec = doc.section(title='Introduction')
>>> sec.paragraph(value='Welcome!')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst = sec.list()
>>> lst.item(value='Point 1')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item(value='Point 2')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Using _schema Dictionary

For simpler cases, use a declarative `_schema`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase

>>> class TableBuilder(BagBuilderBase):
...     _schema = {
...         'table': {'children': 'thead, tbody, tfoot, tr'},
...         'thead': {'children': 'tr'},
...         'tbody': {'children': 'tr'},
...         'tfoot': {'children': 'tr'},
...         'tr': {'children': 'th, td'},
...         'th': {},      # Branch by default
...         'td': {},
...     }

>>> bag = Bag(builder=TableBuilder())
>>> table = bag.table()
>>> thead = table.thead()
>>> tr = thead.tr()
>>> tr.th(value='Name')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> tr.th(value='Age')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> tbody = table.tbody()
>>> row = tbody.tr()
>>> row.td(value='Alice')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> row.td(value='30')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Schema Options

The `_schema` dictionary supports these keys:

| Key | Type | Description |
|-----|------|-------------|
| `children` | str | Comma-separated valid child tags |
| `leaf` | bool | If `True`, element has no children (value='') |
| `attrs` | dict | Attribute validation specs (see [Validation](validation.md)) |

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase

>>> class FormBuilder(BagBuilderBase):
...     _schema = {
...         'form': {'children': 'input, button, label'},
...         'input': {'leaf': True},   # Self-closing, no children
...         'button': {},              # Can have text content
...         'label': {},
...     }

>>> bag = Bag(builder=FormBuilder())
>>> form = bag.form()
>>> # input is a leaf (void element)
>>> inp = form.input(type='text', name='email')
>>> inp.value
''
>>> # button can have text
>>> btn = form.button(value='Submit', type='submit')
>>> btn.value
'Submit'
```

## Combining Both Approaches

You can use `@element` methods and `_schema` together:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class HybridBuilder(BagBuilderBase):
...     # Simple elements via schema
...     _schema = {
...         'container': {'children': 'header, content, footer'},
...         'header': {},
...         'footer': {},
...     }
...
...     # Complex element with custom logic via decorator
...     @element(children='section, aside')
...     def content(self, target, tag, layout='default', **attr):
...         """Content area with layout option."""
...         attr['data-layout'] = layout
...         return self.child(target, tag, **attr)
...
...     @element()
...     def section(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)
...
...     @element()
...     def aside(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=HybridBuilder())
>>> container = bag.container()
>>> container.header()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> content = container.content(layout='two-column')
>>> content.section(value='Main content')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> content.aside(value='Sidebar')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> bag['container_0.content_0?data-layout']
'two-column'
```

## The child() Method

Every element method should call `self.child()` to create nodes:

```python
def child(
    self,
    target: Bag,          # The parent Bag
    tag: str,             # Semantic tag name
    label: str = None,    # Explicit label (auto-generated if None)
    value: Any = None,    # If provided, creates leaf; otherwise branch
    _position: str = None, # Position specifier
    _builder: BagBuilderBase = None,  # Override builder for subtree
    **attr: Any           # Node attributes
) -> Bag | BagNode:
```

### Return Value Logic

- `value=None` → Returns `Bag` (branch, can add children)
- `value=<anything>` → Returns `BagNode` (leaf)

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class TestBuilder(BagBuilderBase):
...     @element()
...     def branch(self, target, tag, **attr):
...         # No value = branch
...         return self.child(target, tag, **attr)
...
...     @element()
...     def leaf(self, target, tag, value='default', **attr):
...         # With value = leaf
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=TestBuilder())
>>> b = bag.branch()
>>> type(b).__name__
'Bag'
>>> l = bag.leaf(value='text')
>>> type(l).__name__
'BagNode'
```

## Best Practices

### 1. Clear Method Signatures

Make parameters explicit for better IDE support and validation:

```python
# Good: explicit parameters
@element()
def link(self, target, tag, href: str, text: str = '', **attr):
    attr['href'] = href
    return self.child(target, tag, value=text, **attr)

# Avoid: everything in **attr
@element()
def link(self, target, tag, **attr):
    return self.child(target, tag, value=attr.pop('text', ''), **attr)
```

### 2. Document Your Elements

Use docstrings to explain purpose and usage:

```python
@element(children='item, divider')
def menu(self, target, tag, **attr):
    """Create a navigation menu.

    Children:
        item: Menu items with href and text
        divider: Visual separator

    Attributes:
        orientation: 'horizontal' or 'vertical' (default)
    """
    return self.child(target, tag, **attr)
```

### 3. Consistent Naming

Follow conventions from your domain:

- HTML: use HTML tag names (`div`, `span`, `ul`)
- Config: use config terminology (`section`, `option`, `value`)
- Data: use data terminology (`record`, `field`, `value`)

### 4. Validate at Build Time

Use `children` to catch structural errors early (see [Validation](validation.md)):

```python
@element(children='head[1], body[1]')  # Exactly one of each
def html(self, target, tag, **attr):
    return self.child(target, tag, **attr)
```
