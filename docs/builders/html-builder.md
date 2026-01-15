# HtmlBuilder

The `HtmlBuilder` provides complete HTML5 support with 112 tags loaded from the W3C schema.

## Basic Usage

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(id='main', class_='container')
>>> div.h1(value='Hello World')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.p(value='Welcome to our site.')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Common Patterns

### Navigation Menu

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> nav = bag.nav(class_='main-nav')
>>> ul = nav.ul()
>>> for text, href in [('Home', '/'), ('About', '/about'), ('Contact', '/contact')]:
...     li = ul.li()
...     _ = li.a(value=text, href=href)

>>> len(list(ul))  # 3 li elements
3
```

### Form Elements

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> form = bag.form(action='/submit', method='post')
>>> div = form.div(class_='form-group')
>>> div.label(value='Email:', for_='email')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.input(type='email', id='email', name='email', required='required')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> form.button(value='Submit', type='submit')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Tables

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> table = bag.table(class_='data-table')
>>> thead = table.thead()
>>> tr = thead.tr()
>>> for header in ['Name', 'Age', 'City']:
...     _ = tr.th(value=header)

>>> tbody = table.tbody()
>>> for name, age, city in [('Alice', '30', 'NYC'), ('Bob', '25', 'LA')]:
...     row = tbody.tr()
...     _ = row.td(value=name)
...     _ = row.td(value=age)
...     _ = row.td(value=city)

>>> len(list(thead['tr_0']))  # 3 headers
3
>>> len(list(tbody))  # 2 rows
2
```

## Tips and Tricks

### Reserved Word Attributes

Use trailing underscore for Python reserved words:

| HTML Attribute | Python Parameter |
|---------------|------------------|
| `class` | `class_` |
| `for` | `for_` |
| `type` | `type` (not reserved) |

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> bag.div(class_='container')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> bag.label(for_='input-id', value='Label')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Data Attributes

Use `data_` prefix (converted to `data-` in HTML):

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(data_id='123', data_action='toggle')
>>> bag['div_0?data_id']
'123'
```

### Accessing Built Structure

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(id='main')
>>> div.p(value='First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.p(value='Second')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Access by path
>>> div['p_0']
'First'
>>> div['p_1']
'Second'
>>> bag['div_0.p_0']  # Full path from root
'First'

>>> # Iterate over children
>>> [node.value for node in div]
['First', 'Second']
```
