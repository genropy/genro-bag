# Validation

Builders support two types of validation:

1. **Structure Validation** - Which children are allowed under which parents
2. **Attribute Validation** - Type checking, enums, required fields

## Structure Validation

### Defining Valid Children

Use the `sub_tags` parameter in `@element` to specify allowed child tags:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(sub_tags='chapter')
...     def book(self): ...
...
...     @element(sub_tags='section,paragraph')
...     def chapter(self): ...
...
...     @element(sub_tags='paragraph')
...     def section(self): ...
...
...     @element()
...     def paragraph(self): ...

>>> bag = Bag(builder=DocumentBuilder)
>>> book = bag.book()
>>> ch1 = book.chapter()
>>> ch1.paragraph('Introduction')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> sec = ch1.section()
>>> sec.paragraph('Detail')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Cardinality Constraints

Specify minimum and maximum occurrences with bracket syntax:

| Syntax | Meaning |
|--------|---------|
| `tag` | Exactly 1 |
| `tag[3]` | Exactly 3 |
| `tag[]` | Any number (0..N) |
| `tag[0:]` | 0 or more (same as `[]`) |
| `tag[1:]` | At least 1 |
| `tag[:3]` | 0 to 3 |
| `tag[2:5]` | Between 2 and 5 |

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class PageBuilder(BagBuilderBase):
...     @element(sub_tags='header,content,footer[:1]')
...     def page(self):
...         """Page must have exactly 1 header, 1 content, at most 1 footer."""
...         ...
...
...     @element()
...     def header(self): ...
...
...     @element()
...     def content(self): ...
...
...     @element()
...     def footer(self): ...
```

### Ordering Constraints (sub_tags_order)

Use `sub_tags_order` to enforce the order of child elements. Two formats are supported:

#### String Format (Grouped Ordering)

The legacy string format uses `>` to define groups that must appear in order:

```python
@element(sub_tags='a,b,c,d', sub_tags_order='a,b>c,d')
def container(self): ...
# a and b must come before c and d
```

#### List Format (Pattern Matching)

The list format uses regex patterns and `*` wildcards for flexible ordering:

| Pattern | Meaning |
|---------|---------|
| `'^tag$'` | Exactly this tag (regex fullmatch) |
| `'.*'` | Any single tag (regex matches one) |
| `'*'` | Wildcard: 0 or more tags |

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(sub_tags='header,content[],footer', sub_tags_order=['^header$', '*', '^footer$'])
...     def page(self): ...
...
...     @element()
...     def header(self): ...
...
...     @element()
...     def content(self): ...
...
...     @element()
...     def footer(self): ...

>>> bag = Bag(builder=DocumentBuilder)
>>> page = bag.page()
>>> page.header()  # Must be first
<genro_bag.bag.Bag object at ...>
>>> page.content()  # Any number in the middle
<genro_bag.bag.Bag object at ...>
>>> page.content()
<genro_bag.bag.Bag object at ...>
>>> page.footer()  # Must be last
<genro_bag.bag.Bag object at ...>
```

Common patterns:

- `['^header$', '*', '^footer$']` - header first, footer last, anything between
- `['*', '^footer$']` - anything, but footer must be last
- `['^header$', '*']` - header first, then anything
- `['^a$', '^b$', '^c$']` - exact sequence a, b, c
- `['*']` - any order (no constraint)

### The check() Method

Use `check()` to validate structure after building:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ListBuilder(BagBuilderBase):
...     @element(sub_tags='item[1:]')  # At least 1 item required
...     def list(self): ...
...
...     @element()
...     def item(self): ...

>>> bag = Bag(builder=ListBuilder)
>>> lst = bag.list()

>>> # Empty list - validation fails
>>> errors = bag.builder.check(lst, parent_tag='list')
>>> len(errors) > 0
True
>>> 'at least 1' in errors[0]
True

>>> # Add items - now valid
>>> lst.item('First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item('Second')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> errors = bag.builder.check(lst, parent_tag='list')
>>> errors
[]
```

### Invalid Children Detection

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class StrictBuilder(BagBuilderBase):
...     @element(sub_tags='allowed')
...     def container(self): ...
...
...     @element()
...     def allowed(self): ...
...
...     @element()
...     def forbidden(self): ...

>>> bag = Bag(builder=StrictBuilder)
>>> cont = bag.container()
>>> cont.allowed('OK')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> cont.forbidden('Oops')  # Structurally added, but invalid
BagNode : ... at ...

>>> errors = bag.builder.check(cont, parent_tag='container')
>>> len(errors) > 0
True
>>> 'forbidden' in errors[0] and 'not a valid child' in errors[0]
True
```

## Attribute Validation

Attribute validation is handled automatically by the builder. Pass attributes as keyword arguments when calling elements:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ButtonBuilder(BagBuilderBase):
...     @element()
...     def button(self): ...

>>> bag = Bag(builder=ButtonBuilder)
>>> bag.button('Submit', variant='primary')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.button('Delete', variant='danger')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Combining Structure and Attribute Validation

A complete example with structure constraints:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class TableBuilder(BagBuilderBase):
...     @element(sub_tags='thead[:1],tbody,tfoot[:1]')
...     def table(self): ...
...
...     @element(sub_tags='tr[]')
...     def thead(self): ...
...
...     @element(sub_tags='tr[1:]')  # At least 1 row
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
>>> tbody = table.tbody()
>>> row = tbody.tr()
>>> row.td('Cell 1', colspan=2)  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> row.td('Cell 2')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Best Practices

### 1. Define Constraints Early

Document your schema constraints clearly:

```python
class ConfigBuilder(BagBuilderBase):
    """Builder for application config.

    Structure:
        config
        ├── database     # Required, exactly one
        ├── cache[:1]    # Optional, at most one
        └── logging[:1]  # Optional, at most one
    """
    @element(sub_tags='database,cache[:1],logging[:1]')
    def config(self): ...
```

### 2. Validate After Building

Always validate complete structures before use:

```python
bag = Bag(builder=MyBuilder)
# ... build the structure ...

errors = bag.builder.check(bag, parent_tag='root')
if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise ValueError("Invalid structure")
```

### 3. Use sub_tags for Self-Documentation

The `sub_tags` parameter serves as documentation and enables validation:

```python
@element(sub_tags='input[],button[],textarea[]')
def form(self):
    """Form element that accepts inputs, buttons, and textareas."""
    ...
```
