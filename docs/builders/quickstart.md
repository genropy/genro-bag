# Quickstart

This guide gets you building with Bag builders in 5 minutes.

## Installation

```bash
pip install genro-bag
```

## Your First Builder

Let's create a simple menu structure:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class MenuBuilder(BagBuilderBase):
...     """Builder for navigation menus."""
...
...     @element(sub_tags='item,separator')
...     def menu(self): ...
...
...     @element()
...     def item(self): ...
...
...     @element()
...     def separator(self): ...

>>> # Use the builder
>>> bag = Bag(builder=MenuBuilder)
>>> menu = bag.menu(id='main-nav')
>>> menu.item('Home', href='/')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> menu.item('Products', href='/products')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> menu.separator()  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> menu.item('Contact', href='/contact')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Check the structure
>>> len(list(menu))
4
>>> menu['item_0']
'Home'
>>> menu['item_0?href']
'/'
```

## Using HtmlBuilder

For HTML, use the built-in `HtmlBuilder`:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> div = bag.div(id='content', class_='container')
>>> div.h1(value='Welcome')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> div.p(value='This is a paragraph.')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Create a list
>>> ul = div.ul()
>>> ul.li(value='First item')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> ul.li(value='Second item')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> ul.li(value='Third item')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Check what we built
>>> len(list(div))  # h1, p, ul
3
>>> len(list(ul))   # 3 li elements
3
```

## Attributes

Pass attributes as keyword arguments. Use `class_` for the `class` attribute (since `class` is a Python reserved word):

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)
>>> a = bag.a(value='Click here', href='https://example.com', target='_blank')
>>> a.attr['href']  # Access via saved reference
'https://example.com'

>>> div = bag.div(id='main', class_='container highlight')
>>> div.parent_node.attr['class_']  # Access via reference
'container highlight'
```

```{tip}
Use saved references (like `a` and `div` above) to access attributes instead of
auto-generated paths like `bag['a_0?href']`. References are stable and don't depend
on insertion order.
```

## Branch vs Leaf Nodes

Understanding when you get a `Bag` vs a `BagNode` is key:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import HtmlBuilder

>>> bag = Bag(builder=HtmlBuilder)

>>> # Branch: returns Bag, can add children
>>> div = bag.div()
>>> type(div).__name__
'Bag'
>>> div.span(value='inside div')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Leaf with value: returns BagNode
>>> p = bag.p(value='text')
>>> type(p).__name__
'BagNode'

>>> # Void elements (br, hr, img, meta) are always leaves
>>> br = bag.br()
>>> type(br).__name__
'BagNode'
>>> br.value
''
```

## Next Steps

- Learn to [create custom builders](custom-builders.md)
- Explore [HtmlBuilder features](html-builder.md)
- Understand [validation](validation.md)
- Master [advanced patterns](advanced.md)
