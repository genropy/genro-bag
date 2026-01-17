# Builder Examples

Practical examples of builder usage patterns.

## HTML Generation

### Simple Page

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> page = Bag(builder=HtmlBuilder)
>>> html = page.html()
>>> head = html.head()
>>> head.title(value='My Page')  # doctest: +ELLIPSIS
BagNode : ...
>>> head.meta(charset='utf-8')  # doctest: +ELLIPSIS
BagNode : ...
>>> body = html.body()
>>> body.h1(value='Welcome')  # doctest: +ELLIPSIS
BagNode : ...
>>> body.p(value='Hello, World!')  # doctest: +ELLIPSIS
BagNode : ...

>>> xml = page.to_xml(pretty=True)
>>> '<title>My Page</title>' in xml
True
```

### Navigation Menu

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> nav = Bag(builder=HtmlBuilder)
>>> ul = nav.ul(class_='nav-menu')
>>> ul.li().a(value='Home', href='/')  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li().a(value='About', href='/about')  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li().a(value='Contact', href='/contact')  # doctest: +ELLIPSIS
BagNode : ...

>>> xml = nav.to_xml()
>>> xml.count('<li>') == 3
True
```

### Data Table

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> data = [
...     {'name': 'Alice', 'role': 'Admin'},
...     {'name': 'Bob', 'role': 'User'},
... ]

>>> table = Bag(builder=HtmlBuilder)
>>> t = table.table(class_='data-table')
>>> thead = t.thead()
>>> tr = thead.tr()
>>> tr.th(value='Name')  # doctest: +ELLIPSIS
BagNode : ...
>>> tr.th(value='Role')  # doctest: +ELLIPSIS
BagNode : ...

>>> tbody = t.tbody()
>>> for row in data:
...     r = tbody.tr()
...     _ = r.td(value=row['name'])
...     _ = r.td(value=row['role'])

>>> xml = table.to_xml()
>>> xml.count('<tr>') == 3  # 1 header + 2 data rows
True
```

## Markdown Generation

### README Template

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import MarkdownBuilder

>>> doc = Bag(builder=MarkdownBuilder)
>>> doc.h1("My Project")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.p("A brief description of the project.")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h2("Installation")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.code("pip install my-project", lang="bash")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h2("Features")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul = doc.ul()
>>> ul.li("Fast and lightweight")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li("Easy to use")  # doctest: +ELLIPSIS
BagNode : ...

>>> md = doc.builder.compile()
>>> "# My Project" in md
True
>>> "pip install" in md
True
```

### API Documentation

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import MarkdownBuilder

>>> doc = Bag(builder=MarkdownBuilder)
>>> doc.h1("API Reference")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h2("get_user()")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.p("Retrieves a user by ID.")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h3("Parameters")  # doctest: +ELLIPSIS
BagNode : ...
>>> table = doc.table()
>>> hdr = table.tr()
>>> hdr.th("Name")  # doctest: +ELLIPSIS
BagNode : ...
>>> hdr.th("Type")  # doctest: +ELLIPSIS
BagNode : ...
>>> hdr.th("Description")  # doctest: +ELLIPSIS
BagNode : ...
>>> row = table.tr()
>>> row.td("user_id")  # doctest: +ELLIPSIS
BagNode : ...
>>> row.td("str")  # doctest: +ELLIPSIS
BagNode : ...
>>> row.td("The user identifier")  # doctest: +ELLIPSIS
BagNode : ...

>>> md = doc.builder.compile()
>>> "| Name | Type |" in md
True
```

## Custom Builder

### Configuration Builder

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ConfigBuilder(BagBuilderBase):
...     @element(sub_tags='database,cache,logging')
...     def config(self, env='production'): ...
...
...     @element()
...     def database(self, host='localhost', port: int = 5432): ...
...
...     @element()
...     def cache(self, enabled: bool = True, ttl: int = 3600): ...
...
...     @element()
...     def logging(self, level='INFO'): ...

>>> cfg = Bag(builder=ConfigBuilder)
>>> config = cfg.config(env='development')
>>> config.database(host='db.local', port=5433)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> config.cache(enabled=True, ttl=7200)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> config.logging(level='DEBUG')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>

>>> cfg['config_0?env']
'development'
>>> cfg['config_0.database_0?host']
'db.local'
```

### Form Builder

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class FormBuilder(BagBuilderBase):
...     @element(sub_tags='text,email,password,submit')
...     def form(self, action='', method='post'): ...
...
...     @element()
...     def text(self, name='', placeholder=''): ...
...
...     @element()
...     def email(self, name='', placeholder=''): ...
...
...     @element()
...     def password(self, name='', placeholder=''): ...
...
...     @element()
...     def submit(self, node_value='Submit'): ...

>>> form = Bag(builder=FormBuilder)
>>> f = form.form(action='/login')
>>> f.text(name='username', placeholder='Username')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> f.password(name='password', placeholder='Password')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> f.submit(node_value='Login')  # doctest: +ELLIPSIS
BagNode : ...
```

## XML Schema Generation

### Invoice Builder

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Create from XSD schema
invoice = Bag(builder=XsdBuilder, builder_xsd_source='invoice.xsd')

doc = invoice.Invoice()
header = doc.Header()
header.InvoiceNumber(value='INV-2025-001')
header.Date(value='2025-01-15')
header.DueDate(value='2025-02-15')

seller = doc.Seller()
seller.Name(value='Acme Corp')
seller.Address(value='123 Main St')

buyer = doc.Buyer()
buyer.Name(value='Customer Inc')
buyer.Address(value='456 Oak Ave')

items = doc.Items()
item = items.Item()
item.Description(value='Widget')
item.Quantity(value='10')
item.UnitPrice(value='9.99')
item.Total(value='99.90')

xml = invoice.to_xml(pretty=True)
```

## Builder Composition

### Reusable Components

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> def create_card(parent, title, content):
...     card = parent.div(class_='card')
...     card.div(class_='card-header').h3(value=title)
...     card.div(class_='card-body').p(value=content)
...     return card

>>> page = Bag(builder=HtmlBuilder)
>>> container = page.div(class_='container')
>>> create_card(container, 'Card 1', 'First card content')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>
>>> create_card(container, 'Card 2', 'Second card content')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag ...>

>>> xml = page.to_xml()
>>> xml.count('class="card"') == 2
True
```

### Dynamic Structure from Data

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import MarkdownBuilder

>>> def generate_doc(data):
...     doc = Bag(builder=MarkdownBuilder)
...     doc.h1(data['title'])
...     doc.p(data['description'])
...
...     if 'sections' in data:
...         for section in data['sections']:
...             doc.h2(section['title'])
...             doc.p(section['content'])
...
...     return doc

>>> content = {
...     'title': 'User Guide',
...     'description': 'How to use the system.',
...     'sections': [
...         {'title': 'Getting Started', 'content': 'First steps...'},
...         {'title': 'Advanced Usage', 'content': 'Power features...'},
...     ]
... }

>>> doc = generate_doc(content)
>>> md = doc.builder.compile()
>>> "# User Guide" in md
True
>>> "## Getting Started" in md
True
```
