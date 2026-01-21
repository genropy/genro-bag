# Creating Custom Builders

This guide shows how to create your own domain-specific builders.

## Overview

Builders use three decorators to define their schema:

| Decorator | Purpose | Body Required |
|-----------|---------|---------------|
| `@element` | Simple elements with optional adapter | No (can use `...`) |
| `@abstract` | Define sub_tags for inheritance | No (can use `...`) |
| `@component` | Composite structures with code logic | **Yes** (must have body) |

## Basic Structure

Every builder extends `BagBuilderBase` and defines elements using decorators.

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

### Restricting Parent Elements (parent_tags)

Use `parent_tags` to specify where an element can be placed:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ListBuilder(BagBuilderBase):
...     @element(sub_tags='li[]')
...     def ul(self): ...
...
...     @element(sub_tags='li[]')
...     def ol(self): ...
...
...     @element(parent_tags='ul,ol')  # li can ONLY be inside ul or ol
...     def li(self): ...
...
...     @element()
...     def div(self): ...

>>> bag = Bag(builder=ListBuilder)
>>> ul = bag.ul()
>>> ul.li('Item 1')  # OK - li inside ul  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> div = bag.div()
>>> div.li('Invalid')  # Adds node but marks as invalid  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Check for validation errors
>>> errors = bag.builder.check()
>>> len(errors) > 0
True
>>> 'parent_tags' in str(errors[0])
True
```

**Key points about parent_tags:**

- Comma-separated list of valid parent tags
- Element is **marked invalid** if placed elsewhere (not rejected)
- Use `builder.check()` to find validation errors
- Works with both `@element` and `@component`

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

### Multiple Inheritance

Elements can inherit from multiple abstracts using a comma-separated list.
The **first parent wins** when there are conflicting attributes (closest to the element):

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, abstract

>>> class UIBuilder(BagBuilderBase):
...     @abstract(sub_tags='span,em', parent_tags='body')
...     def inline(self): ...
...
...     @abstract(sub_tags='div,p', parent_tags='section')
...     def block(self): ...
...
...     @element(inherits_from='@inline,@block')  # @inline wins
...     def mixed(self): ...
...
...     @element()
...     def span(self): ...
...
...     @element()
...     def em(self): ...

>>> bag = Bag(builder=UIBuilder)
>>> info = bag.builder.get_schema_info('mixed')
>>> info['sub_tags']  # From @inline (first parent)
'span,em'
>>> info['parent_tags']  # From @inline (first parent)
'body'
```

**Inheritance priority:**

1. Element's own attributes (always win)
2. First parent in `inherits_from` list
3. Second parent, third, etc. (only for attributes not defined by earlier parents)

## The @component Decorator

Use `@component` for composite structures that need code logic to build their content.
Unlike `@element`, components **must have a method body** - ellipsis (`...`) is not allowed.

### When to Use @component

- When you need to **programmatically create child elements**
- When the element's structure is **always the same** (e.g., a form with fixed fields)
- When you want to **encapsulate complex structures** as reusable units

### Basic Component

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, component

>>> class PageBuilder(BagBuilderBase):
...     @element()
...     def input(self): ...
...
...     @element()
...     def button(self): ...
...
...     @component(sub_tags='')  # Closed component
...     def login_form(self, component: Bag, **kwargs):
...         component.input(name='username', placeholder='Username')
...         component.input(name='password', type='password')
...         component.button('Login', type='submit')
...         return component

>>> page = Bag(builder=PageBuilder)
>>> page.login_form()  # Creates the form structure  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> len(page)  # One node: login_form_0
1
>>> form_node = page.get_node('login_form_0')
>>> len(form_node.value)  # Three children: 2 inputs + 1 button
3
```

### Component Return Behavior (sub_tags)

The `sub_tags` parameter controls what the component call returns:

| sub_tags | Return Value | Use Case |
|----------|--------------|----------|
| `''` (empty) | Parent bag | Closed/leaf component, for chaining |
| defined/None | Internal bag | Open container, for adding children |

**Closed component** (`sub_tags=''`): Returns the parent bag for chaining.

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, component

>>> class Builder(BagBuilderBase):
...     @element()
...     def text(self): ...
...
...     @component(sub_tags='')
...     def separator(self, component: Bag, **kwargs):
...         component.text('---')
...         return component

>>> doc = Bag(builder=Builder)
>>> doc.text('Above')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> doc.separator()  # Returns doc, not the separator's bag  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> doc.text('Below')  # Continues at doc level  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> len(doc)  # text, separator, text
3
```

**Open component** (`sub_tags` defined): Returns the internal bag for adding children.

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, component

>>> class Builder(BagBuilderBase):
...     @element()
...     def header(self): ...
...
...     @element()
...     def item(self): ...
...
...     @component(sub_tags='item')  # Allows 'item' children after creation
...     def mylist(self, component: Bag, title='', **kwargs):
...         component.header(title)
...         return component

>>> doc = Bag(builder=Builder)
>>> lst = doc.mylist(title='Shopping')  # Returns internal bag
>>> lst.item('Milk')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item('Bread')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> len(lst)  # header + 2 items
3
```

### Component with Different Builder

Use `builder` parameter to use a different builder inside the component:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element, component

>>> class InnerBuilder(BagBuilderBase):
...     @element()
...     def field(self): ...

>>> class OuterBuilder(BagBuilderBase):
...     @element()
...     def section(self): ...
...
...     @component(sub_tags='', builder=InnerBuilder)
...     def form(self, component: Bag, **kwargs):
...         # component uses InnerBuilder, not OuterBuilder
...         component.field(name='email')
...         component.field(name='name')
...         return component

>>> page = Bag(builder=OuterBuilder)
>>> page.section()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> page.form()  # Uses InnerBuilder internally  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
```

### Key Differences: @element vs @component

| Feature | @element | @component |
|---------|----------|------------|
| Body | Optional (`...` allowed) | **Required** |
| Receives | kwargs only | `Bag` + kwargs |
| Creates | Single node | Node with pre-populated children |
| Use case | Simple elements | Composite structures |

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

### 2. Use @component for Reusable Structures

When you have a fixed structure that repeats, use `@component`:

```python
@component(sub_tags='')
def card(self, component: Bag, title='', **kwargs):
    component.header(title)
    component.body()
    component.footer()
    return component
```

### 3. Consistent Naming

Follow conventions from your domain:

- HTML: use HTML tag names (`div`, `span`, `ul`)
- Config: use config terminology (`section`, `option`, `value`)
- Data: use data terminology (`record`, `field`, `value`)

### 4. Validate Structure Early

Use `sub_tags` and `parent_tags` to catch structural errors early:

```python
@element(sub_tags='head[:1],body[:1]')  # Exactly one of each
def html(self): ...

@element(parent_tags='ul,ol')  # Only inside lists
def li(self): ...
```

See [Validation](validation.md) for more details.
