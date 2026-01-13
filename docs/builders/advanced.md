# Advanced Patterns

This guide covers advanced builder patterns for complex use cases.

## Reference Resolution

Builders support `=ref` syntax to reference reusable element groups.

### Defining References

Define `_ref_<name>` properties on your builder:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class HtmlLikeBuilder(BagBuilderBase):
...     """Builder with content category references."""
...
...     @property
...     def _ref_inline(self):
...         """Inline elements: text formatting."""
...         return 'span, strong, em, a, code'
...
...     @property
...     def _ref_block(self):
...         """Block elements: structural."""
...         return 'div, p, ul, ol'
...
...     @property
...     def _ref_flow(self):
...         """Flow content: both inline and block."""
...         return '=inline, =block'  # Combine other refs!
...
...     @element(sub_tags='=flow')  # Use reference
...     def div(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element(sub_tags='=inline')
...     def p(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)
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
...     def a(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def code(self, target, tag, value=None, **attr):
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
...     @element(sub_tags='=flow')
...     def li(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=HtmlLikeBuilder)
>>> div = bag.div()
>>> div.p(value='Paragraph text')  # block in flow ✓
BagNode : ... at ...
>>> div.span(value='Inline text')  # inline in flow ✓
BagNode : ... at ...
>>> ul = div.ul()  # block in flow ✓
>>> ul.li(value='Item')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Reference Resolution Chain

References can reference other references:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase

>>> class ChainedRefBuilder(BagBuilderBase):
...     @property
...     def _ref_text(self):
...         return 'span, strong'
...
...     @property
...     def _ref_media(self):
...         return 'img, video'
...
...     @property
...     def _ref_all(self):
...         return '=text, =media, div'  # Combines both + div
...
...     @element(sub_tags='=all')
...     def container(self): ...
...
...     @element()
...     def div(self): ...
...
...     @element()
...     def span(self): ...
...
...     @element()
...     def strong(self): ...
...
...     @element(sub_tags='')  # void element
...     def img(self): ...
...
...     @element()
...     def video(self): ...

>>> bag = Bag(builder=ChainedRefBuilder)
>>> container = bag.container()
>>> container.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> container.img()  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Dynamic References via Properties

For dynamic reference lookup, use `_ref_*` properties:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class DynamicRefBuilder(BagBuilderBase):
...     @property
...     def _ref_controls(self):
...         return 'button,input,select'
...
...     @property
...     def _ref_display(self):
...         return 'span,div,label'
...
...     @element(sub_tags='=controls,=display')
...     def form(self): ...
...
...     @element()
...     def button(self): ...
...
...     @element(sub_tags='')
...     def input(self): ...
...
...     @element()
...     def select(self): ...
...
...     @element()
...     def span(self): ...
...
...     @element()
...     def div(self): ...
...
...     @element()
...     def label(self): ...

>>> bag = Bag(builder=DynamicRefBuilder)
>>> form = bag.form()
>>> form.button(value='Submit')  # control
BagNode : ... at ...
>>> form.label(value='Name:')   # display
BagNode : ... at ...
```

## Builder Inheritance

### Extending Existing Builders

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class BaseUIBuilder(BagBuilderBase):
...     """Base builder with common UI elements."""
...
...     @element()
...     def container(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def text(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> class ExtendedUIBuilder(BaseUIBuilder):
...     """Extended builder with additional elements."""
...
...     @element()
...     def button(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or 'Click', **attr)
...
...     @element(sub_tags='option')
...     def select(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def option(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=ExtendedUIBuilder)
>>> cont = bag.container()  # From parent
>>> cont.text(value='Label')  # From parent
BagNode : ... at ...
>>> cont.button(value='Submit')  # From child
BagNode : ... at ...
>>> sel = cont.select()  # From child
>>> sel.option(value='A')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Overriding Methods

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class BaseBuilder(BagBuilderBase):
...     @element()
...     def item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value, **attr)

>>> class StyledBuilder(BaseBuilder):
...     @element()
...     def item(self, target, tag, value=None, style='default', **attr):
...         # Add automatic styling
...         attr['class_'] = f'item-{style}'
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=StyledBuilder)
>>> item = bag.item(value='Styled', style='highlight')
>>> item.attr['class_']
'item-highlight'
```

## Nested Builders

### Different Builders for Subtrees

Use `_builder` parameter to change builder mid-tree:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class OuterBuilder(BagBuilderBase):
...     @element()
...     def outer(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def wrapper(self, target, tag, inner_builder=None, **attr):
...         # Pass different builder for this subtree
...         return self.child(target, tag, _builder=inner_builder, **attr)

>>> class InnerBuilder(BagBuilderBase):
...     @element()
...     def inner_item(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> outer_builder = OuterBuilder()
>>> inner_builder = InnerBuilder()

>>> bag = Bag(builder=outer_builder)
>>> wrapper = bag.wrapper(inner_builder=inner_builder)

>>> # Now wrapper uses InnerBuilder
>>> wrapper.inner_item(value='Inside')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## SchemaBuilder: Programmatic Schema Creation

`SchemaBuilder` allows you to define schemas programmatically instead of using decorators. This is useful for:

- Dynamic schema generation
- Schemas loaded from external sources
- Reusable schema definitions shared across builders

### Basic Usage

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import SchemaBuilder

>>> schema = Bag(builder=SchemaBuilder)

>>> # Define elements with the item() method
>>> schema.item('document', sub_tags='chapter[]')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('chapter', sub_tags='section[],paragraph[]')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('section', sub_tags='paragraph[]')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('paragraph')  # Leaf element (no children)  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### The item() Method

```python
schema.item(
    name: str,              # Element name (or '@name' for abstract)
    sub_tags: str = '',     # Valid child tags with cardinality
    inherits_from: str = None,  # Abstract element to inherit from
)
```

### Defining Abstract Elements

Use `@` prefix for abstract elements:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import SchemaBuilder

>>> schema = Bag(builder=SchemaBuilder)

>>> # Define abstract (content category)
>>> schema.item('@inline', sub_tags='span,strong,em')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Concrete element inherits from abstract
>>> schema.item('p', inherits_from='@inline')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> schema.item('span')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('strong')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('em')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Compiling to File

Save the schema for reuse:

```python
# Save to MessagePack (binary, compact)
schema.builder.compile('my_schema.msgpack')

# Or save to JSON (human-readable)
schema.builder.compile('my_schema.json', transport='json')
```

### Using Compiled Schema

Load the schema in a custom builder:

```python
from genro_bag import Bag
from genro_bag.builders import BagBuilderBase

# Method 1: Class attribute
class MyBuilder(BagBuilderBase):
    schema_path = 'my_schema.msgpack'

# Method 2: Constructor parameter
bag = Bag(builder=BagBuilderBase, builder_schema_path='my_schema.msgpack')
```

### Complete Example: Config Schema

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import SchemaBuilder, BagBuilderBase

>>> # Create schema programmatically
>>> schema = Bag(builder=SchemaBuilder)
>>> schema.item('config', sub_tags='database,cache[:1],logging[:1]')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('database')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('cache')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('logging')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Use the schema directly (without saving to file)
>>> class ConfigBuilder(BagBuilderBase):
...     pass

>>> # The schema would normally be loaded from file
>>> # For this example, we show the pattern
```

### When to Use SchemaBuilder vs @element

| Approach | Use When |
|----------|----------|
| `@element` decorator | Schema is static, defined in code |
| `SchemaBuilder` | Schema is dynamic, generated at runtime |
| `SchemaBuilder` + file | Schema is shared across multiple builders |
| XSD → SchemaBuilder | Schema comes from external XSD file |

## Loading Schema from File

Builders can load schema from a pre-compiled MessagePack file using `schema_path`:

```python
from genro_bag import Bag
from genro_bag.builders import BagBuilderBase

class MyBuilder(BagBuilderBase):
    schema_path = 'path/to/schema.msgpack'  # Load at class definition

# Or pass at instantiation
bag = Bag(builder=MyBuilder, builder_schema_path='custom_schema.msgpack')
```

## Custom Validation

### Pre-Build Validation

Validate before creating nodes:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ValidatedBuilder(BagBuilderBase):
...     @element()
...     def email_field(self, target, tag, value=None, **attr):
...         if value and '@' not in value:
...             raise ValueError(f"Invalid email: {value}")
...         return self.child(target, tag, value=value or '', **attr)
...
...     @element()
...     def positive_number(self, target, tag, value=None, **attr):
...         if value is not None:
...             num = float(value)
...             if num <= 0:
...                 raise ValueError(f"Must be positive: {value}")
...         return self.child(target, tag, value=value, **attr)

>>> bag = Bag(builder=ValidatedBuilder)
>>> bag.email_field(value='test@example.com')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> try:
...     bag.email_field(value='invalid')
... except ValueError as e:
...     'Invalid email' in str(e)
True
```

### Post-Build Validation

Validate complete structures:

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class FormBuilder(BagBuilderBase):
...     @element(sub_tags='field')
...     def form(self, target, tag, **attr):
...         return self.child(target, tag, **attr)
...
...     @element()
...     def field(self, target, tag, name=None, value=None, **attr):
...         if name:
...             attr['name'] = name
...         return self.child(target, tag, value=value or '', **attr)
...
...     def validate_form(self, form_bag):
...         """Ensure all fields have names."""
...         errors = []
...         for node in form_bag:
...             if node.tag == 'field' and 'name' not in node.attr:
...                 errors.append(f"Field '{node.label}' missing 'name' attribute")
...         return errors

>>> bag = Bag(builder=FormBuilder)
>>> form = bag.form()
>>> form.field(name='email', value='')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> form.field(value='no name')  # Missing name
BagNode : ... at ...

>>> errors = bag.builder.validate_form(form)
>>> len(errors) > 0
True
>>> 'missing' in errors[0]
True
```

## Performance Tips

### 1. Cache Schema Loading

```python
# Good: Load schema once
_cached_schema = None

def get_schema():
    global _cached_schema
    if _cached_schema is None:
        _cached_schema = load_schema_from_file()
    return _cached_schema

class MyBuilder(BagBuilderBase):
    def __init__(self):
        self._schema = get_schema()
```

### 2. Avoid Excessive Validation

Disable validation for trusted input:

```python
@element(validate=False)  # Skip attribute validation
def trusted_input(self, target, tag, **attr):
    return self.child(target, tag, **attr)
```

### 3. Use Batch Operations

```python
# Instead of validating each step:
for data in large_dataset:
    parent.item(value=data)

# Validate once at the end:
errors = builder.check(parent, parent_tag='list')
```

## Real-World Example: Config Builder

```{doctest}
>>> from genro_bag import Bag
>>> from genro_bag.builders import BagBuilderBase, element

>>> class ConfigBuilder(BagBuilderBase):
...     """Builder for application configuration."""
...
...     @element(sub_tags='database,cache[:1],logging[:1],features[]')
...     def config(self, target, tag, env='production', **attr):
...         attr['env'] = env
...         return self.child(target, tag, **attr)
...
...     @element()
...     def database(self, target, tag, host='localhost', port=5432, **attr):
...         attr['host'] = host
...         attr['port'] = port
...         return self.child(target, tag, **attr)
...
...     @element()
...     def cache(self, target, tag, enabled=True, ttl=3600, **attr):
...         attr['enabled'] = enabled
...         attr['ttl'] = ttl
...         return self.child(target, tag, **attr)
...
...     @element()
...     def logging(self, target, tag, level='INFO', **attr):
...         attr['level'] = level
...         return self.child(target, tag, **attr)
...
...     @element()
...     def features(self, target, tag, value=None, **attr):
...         return self.child(target, tag, value=value or '', **attr)

>>> bag = Bag(builder=ConfigBuilder)
>>> config = bag.config(env='development')
>>> config.database(host='db.local', port=5433)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.cache(enabled=True, ttl=7200)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.logging(level='DEBUG')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.features(value='dark_mode,beta_ui')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Validate structure
>>> errors = bag.builder.check(config, parent_tag='config')
>>> errors
[]

>>> # Access config values
>>> config['database_0?host']
'db.local'
>>> config['database_0?port']
5433
```
