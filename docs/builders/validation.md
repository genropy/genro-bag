# Validation

Builders support two types of validation:

1. **Structure Validation** - Which children are allowed under which parents
2. **Attribute Validation** - Type checking, enums, required fields

## Structure Validation

### Defining Valid Children

Use the `children` parameter in `@element` to specify allowed child tags:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(children='chapter')
...     def book(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(children='section, paragraph')
...     def chapter(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(children='paragraph')
...     def section(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def paragraph(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=DocumentBuilder())
>>> book = bag.book()
>>> ch1 = book.chapter()
>>> ch1.paragraph(value='Introduction')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> sec = ch1.section()
>>> sec.paragraph(value='Detail')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Cardinality Constraints

Specify minimum and maximum occurrences with bracket syntax:

| Syntax | Meaning |
|--------|---------|
| `tag` | 0 to unlimited |
| `tag[1]` | Exactly 1 |
| `tag[1:]` | At least 1 |
| `tag[:3]` | At most 3 |
| `tag[2:5]` | Between 2 and 5 |

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class PageBuilder(BagBuilderBase):
...     @element(children='header[1], content[1], footer[:1]')
...     def page(self, target, tag, **attr):
...         """Page must have exactly 1 header, 1 content, at most 1 footer."""
...         return self.child(target, tag, **attr)
...
...     @element()
...     def header(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def content(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def footer(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
```

### The check() Method

Use `check()` to validate structure after building:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ListBuilder(BagBuilderBase):
...     @element(children='item[1:]')  # At least 1 item required
...     def list(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=ListBuilder())
>>> lst = bag.list()

>>> # Empty list - validation fails
>>> errors = bag.builder.check(lst, parent_tag='list')
>>> len(errors) > 0
True
>>> 'at least 1' in errors[0]
True

>>> # Add items - now valid
>>> lst.item(value='First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item(value='Second')  # doctest: +ELLIPSIS
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
...     @element(children='allowed')
...     def container(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def allowed(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def forbidden(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=StrictBuilder())
>>> cont = bag.container()
>>> cont.allowed(value='OK')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> cont.forbidden(value='Oops')  # Structurally added, but invalid
BagNode : ... at ...

>>> errors = bag.builder.check(cont, parent_tag='container')
>>> len(errors) > 0
True
>>> 'forbidden' in errors[0] and 'not a valid child' in errors[0]
True
```

## Attribute Validation

### Schema-Based Validation

Define attribute specs in `_schema`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase

>>> class FormBuilder(BagBuilderBase):
...     _schema = {
...         'input': {
...             'leaf': True,
...             'attrs': {
...                 'type': {
...                     'type': 'enum',
...                     'values': ['text', 'email', 'password', 'number'],
...                     'required': True
...                 },
...                 'maxlength': {
...                     'type': 'int',
...                     'min': 1,
...                     'max': 1000
...                 },
...                 'required': {
...                     'type': 'bool'
...                 }
...             }
...         }
...     }

>>> bag = Bag(builder=FormBuilder())
>>> bag.input(type='email', maxlength=100)  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Attribute Spec Options

| Key | Type | Description |
|-----|------|-------------|
| `type` | str | `'string'`, `'int'`, `'bool'`, `'enum'` |
| `required` | bool | If `True`, attribute must be provided |
| `default` | Any | Default value if not provided |
| `min` | int | Minimum value (for `int` type) |
| `max` | int | Maximum value (for `int` type) |
| `values` | list | Allowed values (for `enum` type) |

### Type-Based Validation with Decorators

Use type hints in method signatures for automatic validation:

```{doctest}
>>> from typing import Literal, Optional
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ButtonBuilder(BagBuilderBase):
...     @element()
...     def button(
...         self,
...         target,
...         tag,
...         value: str = 'Click',
...         variant: Literal['primary', 'secondary', 'danger'] = 'primary',
...         disabled: Optional[bool] = None,
...         **attr
...     ):
...         attr['variant'] = variant
...         if disabled is not None:
...             attr['disabled'] = disabled
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=ButtonBuilder())
>>> bag.button(value='Submit', variant='primary')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.button(value='Delete', variant='danger')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Manual Validation

Call `_validate_attrs()` explicitly:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase

>>> class TableBuilder(BagBuilderBase):
...     _schema = {
...         'td': {
...             'attrs': {
...                 'colspan': {'type': 'int', 'min': 1, 'max': 100},
...                 'rowspan': {'type': 'int', 'min': 1, 'max': 100},
...             }
...         }
...     }

>>> builder = TableBuilder()

>>> # Valid attributes
>>> errors = builder._validate_attrs('td', {'colspan': 2}, raise_on_error=False)
>>> errors
[]

>>> # Invalid: colspan too small
>>> errors = builder._validate_attrs('td', {'colspan': 0}, raise_on_error=False)
>>> len(errors) > 0
True
>>> 'must be >= 1' in errors[0]
True
```

### Validation Errors

With `raise_on_error=True` (default), invalid attributes raise `ValueError`:

```{doctest}
>>> from genro_bag.builders import BagBuilderBase

>>> class StrictBuilder(BagBuilderBase):
...     _schema = {
...         'input': {
...             'attrs': {
...                 'min': {'type': 'int', 'min': 0},
...             }
...         }
...     }

>>> builder = StrictBuilder()
>>> try:
...     builder._validate_attrs('input', {'min': -5}, raise_on_error=True)
... except ValueError as e:
...     'must be >= 0' in str(e)
True
```

## Combining Structure and Attribute Validation

A complete example with both types:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class TableBuilder(BagBuilderBase):
...     _schema = {
...         'table': {'children': 'thead[:1], tbody[1], tfoot[:1]'},
...         'thead': {'children': 'tr'},
...         'tbody': {'children': 'tr[1:]'},  # At least 1 row
...         'tfoot': {'children': 'tr'},
...         'tr': {'children': 'th, td'},
...         'th': {
...             'attrs': {
...                 'colspan': {'type': 'int', 'min': 1, 'default': 1},
...                 'scope': {'type': 'enum', 'values': ['row', 'col', 'rowgroup', 'colgroup']}
...             }
...         },
...         'td': {
...             'attrs': {
...                 'colspan': {'type': 'int', 'min': 1, 'default': 1},
...                 'rowspan': {'type': 'int', 'min': 1, 'default': 1}
...             }
...         }
...     }

>>> bag = Bag(builder=TableBuilder())
>>> table = bag.table()
>>> tbody = table.tbody()
>>> row = tbody.tr()
>>> row.td(value='Cell 1', colspan=2)  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> row.td(value='Cell 2')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Validate structure
>>> errors = bag.builder.check(table, parent_tag='table')
>>> errors  # Valid: has tbody with at least 1 tr
[]
```

## Best Practices

### 1. Define Constraints Early

Document your schema constraints clearly:

```python
class ConfigBuilder(BagBuilderBase):
    """Builder for application config.

    Structure:
        config
        ├── database[1]     # Required, exactly one
        ├── cache[:1]       # Optional, at most one
        └── logging[:1]     # Optional, at most one
    """
    _schema = {
        'config': {'children': 'database[1], cache[:1], logging[:1]'},
        # ...
    }
```

### 2. Validate After Building

Always validate complete structures before use:

```python
bag = Bag(builder=MyBuilder())
# ... build the structure ...

errors = bag.builder.check(bag, parent_tag='root')
if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise ValueError("Invalid structure")
```

### 3. Use Type Hints for Self-Documentation

Type hints in method signatures serve as documentation and enable IDE support:

```python
@element()
def input(
    self,
    target,
    tag,
    type: Literal['text', 'email', 'password'] = 'text',
    maxlength: Optional[int] = None,
    required: bool = False,
    **attr
):
    """Create an input element.

    Args:
        type: Input type (text, email, password)
        maxlength: Maximum character length
        required: Whether field is required
    """
    ...
```
