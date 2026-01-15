# Creating Custom Builders

This guide shows how to create your own domain-specific builders.

## Basic Structure

Every builder extends `BagBuilderBase` and defines elements using the `@element` decorator.

```{important}
**Schemas are never created manually.** If you need to load a schema from a file, use
`builder_schema_path` with a `.bag.mp` file created by the schema builder tools.
Do not create JSON or dictionary schemas by hand.
```

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class RecipeBuilder(BagBuilderBase):
...     """Builder for cooking recipes."""
...
...     @element(sub_tags='ingredient,step')
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

>>> bag = Bag(builder=RecipeBuilder)
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

>>> bag = Bag(builder=SimpleBuilder)
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

>>> bag = Bag(builder=KitchenBuilder)
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

Use `sub_tags` to define what child elements are allowed:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(sub_tags='section,paragraph')
...     def document(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(sub_tags='paragraph,list')
...     def section(self, target, tag, title=None, **attr):
...         if title:
...             attr['title'] = title
...         return self.child(target, tag, **attr)
...
...     @element()
...     def paragraph(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element(sub_tags='item')
...     def list(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=DocumentBuilder)
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

## The @abstract Decorator

Use `@abstract` to define element groups that can be inherited but not instantiated directly. Abstract elements are stored with an `@` prefix in the schema.

### Defining Content Categories

Abstract elements are useful for defining content categories (like HTML5 content categories):

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, abstract

>>> class HtmlLikeBuilder(BagBuilderBase):
...     """Builder with HTML-like content categories."""
...
...     @abstract(sub_tags='span,strong,em,a')
...     def phrasing(self):
...         """Phrasing content: inline text-level elements."""
...         ...
...
...     @abstract(sub_tags='div,p,ul,ol')
...     def flow(self):
...         """Flow content: block-level elements."""
...         ...
...
...     @element(inherits_from='@phrasing')
...     def p(self, target, tag, value=None, **attr):
...         """Paragraph inherits phrasing content as children."""
...         return self.child(target, tag, value=value, **attr)
...
...     @element(inherits_from='@flow')
...     def div(self, target, tag, **attr):
...         """Div inherits flow content as children."""
...         return self.child(target, tag, **attr)
...
...     @element()
...     def span(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def strong(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def em(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def a(self, target, tag, value=None, href=None, **attr):
...         if href:
...             attr['href'] = href
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element(sub_tags='li')
...     def ul(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(sub_tags='li')
...     def ol(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def li(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=HtmlLikeBuilder)
>>> p = bag.p()
>>> p.strong(value='Bold')  # phrasing content allowed in p
BagNode : ... at ...
>>> p.em(value='Italic')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> div = bag.div()
>>> div.p(value='Paragraph in div')  # flow content allowed in div
BagNode : ... at ...
```

### Key Points

1. **Cannot be instantiated**: `bag.phrasing()` would raise an error
2. **Prefix with @**: When using `inherits_from`, reference as `'@phrasing'`
3. **Defines sub_tags**: Child elements inherit the `sub_tags` specification
4. **Combinable**: Abstract elements can reference other abstracts

### Combining Abstracts

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, abstract

>>> class ContentBuilder(BagBuilderBase):
...     @abstract(sub_tags='text,code')
...     def inline(self): ...
...
...     @abstract(sub_tags='block,section')
...     def structural(self): ...
...
...     @abstract(sub_tags='=inline,=structural')  # Combine both!
...     def all_content(self): ...
...
...     @element(inherits_from='@all_content')
...     def container(self): ...
...
...     @element()
...     def text(self): ...
...
...     @element()
...     def code(self): ...
...
...     @element()
...     def block(self): ...
...
...     @element()
...     def section(self): ...

>>> bag = Bag(builder=ContentBuilder)
>>> c = bag.container()
>>> c.text(value='Hello')  # from @inline
BagNode : ... at ...
>>> c.block()  # from @structural
<genro_bag.bag.Bag object at ...>
```

## Defining Multiple Elements Simply

For elements without custom logic, use empty method bodies:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class TableBuilder(BagBuilderBase):
...     @element(sub_tags='thead[:1],tbody,tfoot[:1],tr[]')
...     def table(self): ...
...
...     @element(sub_tags='tr[]')
...     def thead(self): ...
...
...     @element(sub_tags='tr[]')
...     def tbody(self): ...
...
...     @element(sub_tags='tr[]')
...     def tfoot(self): ...
...
...     @element(sub_tags='th[],td[]')
...     def tr(self): ...
...
...     @element()
...     def th(self): ...
...
...     @element()
...     def td(self): ...

>>> bag = Bag(builder=TableBuilder)
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

### Void Elements (No Children)

Use `sub_tags=''` to define void elements that cannot have children:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class FormBuilder(BagBuilderBase):
...     @element(sub_tags='input[],button[],label[]')
...     def form(self): ...
...
...     @element(sub_tags='')  # Void element - no children allowed
...     def input(self): ...
...
...     @element()
...     def button(self): ...
...
...     @element()
...     def label(self): ...

>>> bag = Bag(builder=FormBuilder)
>>> form = bag.form()
>>> form.input(type='text', name='email')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> form.button(value='Submit', type='submit')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Combining Simple and Custom Elements

Mix simple elements (empty body) with custom logic elements:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class HybridBuilder(BagBuilderBase):
...     # Simple elements with empty body (uses default handler)
...     @element(sub_tags='header,content,footer')
...     def container(self): ...
...
...     @element()
...     def header(self): ...
...
...     @element()
...     def footer(self): ...
...
...     # Custom element with logic
...     @element(sub_tags='section,aside')
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

>>> bag = Bag(builder=HybridBuilder)
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
    node_position: str = None, # Position specifier
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

>>> bag = Bag(builder=TestBuilder)
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
@element(sub_tags='item,divider')
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

Use `sub_tags` to catch structural errors early (see [Validation](validation.md)):

```python
@element(sub_tags='head,body')  # Exactly one of each
def html(self, target, tag, **attr):
    return self.child(target, tag, **attr)
```
