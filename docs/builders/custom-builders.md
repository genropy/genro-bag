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
...     def recipe(self): ...
...
...     @element()
...     def ingredient(self): ...
...
...     @element()
...     def step(self): ...

>>> bag = Bag(builder=RecipeBuilder)
>>> recipe = bag.recipe(title='Pasta Carbonara')
>>> recipe.ingredient('Spaghetti', amount='400', unit='g')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> recipe.ingredient('Eggs', amount='4', unit='units')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> recipe.step('Boil the pasta')  # doctest: +ELLIPSIS
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
...     def item(self): ...

>>> bag = Bag(builder=SimpleBuilder)
>>> bag.item('test')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Multiple Tags for One Method

Use `tags` to handle multiple tag names with one method:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class KitchenBuilder(BagBuilderBase):
...     @element(tags='fridge, oven, dishwasher, microwave')
...     def appliance(self): ...

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
...     def document(self): ...
...
...     @element(sub_tags='paragraph,list')
...     def section(self): ...
...
...     @element()
...     def paragraph(self): ...
...
...     @element(sub_tags='item')
...     def list(self): ...
...
...     @element()
...     def item(self): ...

>>> bag = Bag(builder=DocumentBuilder)
>>> doc = bag.document()
>>> sec = doc.section(title='Introduction')
>>> sec.paragraph('Welcome!')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst = sec.list()
>>> lst.item('Point 1')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item('Point 2')  # doctest: +ELLIPSIS
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
...     def p(self): ...
...
...     @element(inherits_from='@flow')
...     def div(self): ...
...
...     @element()
...     def span(self): ...
...
...     @element()
...     def strong(self): ...
...
...     @element()
...     def em(self): ...
...
...     @element()
...     def a(self): ...
...
...     @element(sub_tags='li')
...     def ul(self): ...
...
...     @element(sub_tags='li')
...     def ol(self): ...
...
...     @element()
...     def li(self): ...

>>> bag = Bag(builder=HtmlLikeBuilder)
>>> p = bag.p()
>>> p.strong('Bold')  # phrasing content allowed in p
BagNode : ... at ...
>>> p.em('Italic')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> div = bag.div()
>>> div.p('Paragraph in div')  # flow content allowed in div
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
>>> c.text('Hello')  # from @inline
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
>>> tr.th('Name')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> tr.th('Age')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> tbody = table.tbody()
>>> row = tbody.tr()
>>> row.td('Alice')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> row.td('30')  # doctest: +ELLIPSIS
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
>>> form.button('Submit', type='submit')  # doctest: +ELLIPSIS
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
...     @element(sub_tags='section,aside')
...     def content(self): ...
...
...     @element()
...     def section(self): ...
...
...     @element()
...     def aside(self): ...

>>> bag = Bag(builder=HybridBuilder)
>>> container = bag.container()
>>> container.header()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> content = container.content()
>>> content.section('Main content')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> content.aside('Sidebar')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Return Value Logic

- No value passed → Returns `Bag` (branch, can add children)
- Value passed → Returns `BagNode` (leaf)

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class TestBuilder(BagBuilderBase):
...     @element()
...     def branch(self): ...
...
...     @element()
...     def leaf(self): ...

>>> bag = Bag(builder=TestBuilder)
>>> b = bag.branch()
>>> type(b).__name__
'Bag'
>>> l = bag.leaf('text')
>>> type(l).__name__
'BagNode'
```

## Best Practices

### 1. Keep Elements Simple

Most elements need no custom logic - use empty body with `...`:

```python
@element(sub_tags='item,divider')
def menu(self): ...

@element()
def item(self): ...

@element()
def divider(self): ...
```

### 2. Consistent Naming

Follow conventions from your domain:

- HTML: use HTML tag names (`div`, `span`, `ul`)
- Config: use config terminology (`section`, `option`, `value`)
- Data: use data terminology (`record`, `field`, `value`)

### 3. Validate at Build Time

Use `sub_tags` to catch structural errors early (see [Validation](validation.md)):

```python
@element(sub_tags='head[:1],body[:1]')  # Exactly one of each
def html(self): ...
```
