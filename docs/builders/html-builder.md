# HtmlBuilder and HtmlPage

The `HtmlBuilder` provides complete HTML5 support with 112 tags loaded from the W3C schema. `HtmlPage` offers a convenient wrapper for building complete HTML documents.

## HtmlBuilder

### Basic Usage

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

### Available Tags

HtmlBuilder supports all 112 HTML5 tags:

```{doctest}
>>> from genro_bag.builders import HtmlBuilder
>>> builder = HtmlBuilder()
>>> len(builder.ALL_TAGS)
112
>>> sorted(list(builder.ALL_TAGS))[:10]
['a', 'abbr', 'address', 'area', 'article', 'aside', 'audio', 'b', 'base', 'bdi']
```

### Void Elements

Void elements (self-closing tags like `<br>`, `<img>`, `<meta>`) automatically get an empty value:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> builder = HtmlBuilder()
>>> sorted(builder.VOID_ELEMENTS)
['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']

>>> bag = Bag(builder=HtmlBuilder)
>>> br = bag.br()
>>> br.value  # Empty string, not None
''

>>> img = bag.img(src='/logo.png', alt='Logo')
>>> img.value
''
>>> bag['img_0?src']
'/logo.png'

>>> meta = bag.meta(charset='utf-8')
>>> meta.value
''
```

### Common Patterns

#### Navigation Menu

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

#### Form Elements

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

#### Tables

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

## HtmlPage

`HtmlPage` provides a complete HTML document structure with separate `head` and `body` sections.

### Basic Usage

```{doctest}
>>> from genro_bag.builders import HtmlPage

>>> page = HtmlPage()

>>> # Configure <head>
>>> page.head.meta(charset='utf-8')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.head.title(value='My Website')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.head.meta(name='viewport', content='width=device-width, initial-scale=1')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Build <body>
>>> page.body.header().h1(value='Welcome')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.main().p(value='Content here')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.footer().p(value='Footer')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Generating HTML

```{doctest}
>>> from genro_bag.builders import HtmlPage

>>> page = HtmlPage()
>>> page.head.title(value='Test')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.p(value='Hello')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> html = page.to_html()
>>> '<!DOCTYPE html>' in html
True
>>> '<html>' in html
True
>>> '<head>' in html
True
>>> '<title>Test</title>' in html
True
>>> '<body>' in html
True
>>> '<p>Hello</p>' in html
True
```

### Saving to File

```python
>>> from genro_bag.builders import HtmlPage
>>> import tempfile
>>> import os

>>> page = HtmlPage()
>>> page.head.title(value='Saved Page')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.body.h1(value='Hello')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Save to file
>>> with tempfile.TemporaryDirectory() as tmpdir:
...     path = page.to_html('index.html', output_dir=tmpdir)
...     os.path.basename(path)
'index.html'
```

### Debug with print_tree()

```python
>>> from genro_bag.builders import HtmlPage

>>> page = HtmlPage()
>>> page.head.title(value='Debug Example')  # doctest: +SKIP
>>> page.body.div(id='main').p(value='Hello')  # doctest: +SKIP
>>> page.print_tree()  # doctest: +SKIP
============================================================
HEAD
============================================================
<title>: "Debug Example"

============================================================
BODY
============================================================
<div [id="main"]>
  <p>: "Hello"
```

### Complete Example

```{doctest}
>>> from genro_bag.builders import HtmlPage

>>> page = HtmlPage()

>>> # Head section
>>> page.head.meta(charset='utf-8')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.head.title(value='Product Page')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> page.head.link(rel='stylesheet', href='/css/style.css')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Navigation
>>> nav = page.body.nav(class_='navbar')
>>> ul = nav.ul()
>>> for text, href in [('Home', '/'), ('Products', '/products')]:
...     li = ul.li()
...     _ = li.a(value=text, href=href)

>>> # Main content
>>> main = page.body.main()
>>> main.h1(value='Our Products')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Product cards
>>> grid = main.div(class_='product-grid')
>>> for name, price in [('Widget', '$10'), ('Gadget', '$25')]:
...     card = grid.div(class_='product-card')
...     _ = card.h2(value=name)
...     _ = card.p(value=price, class_='price')
...     _ = card.button(value='Buy Now')

>>> # Footer
>>> footer = page.body.footer()
>>> footer.p(value='Copyright 2025')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> html = page.to_html()
>>> '<nav class_="navbar">' in html
True
>>> '<div class_="product-grid">' in html
True
>>> 'Widget' in html and 'Gadget' in html
True
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
