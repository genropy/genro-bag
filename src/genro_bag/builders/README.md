# Builders

Ready-to-use builders based on pre-compiled schemas.

## Concept

A builder provides domain-specific element creation with validation.
The base class `BagBuilderBase` (in `genro_bag.builder`) handles:

- Schema loading from `.bag.mp` files
- Element dispatch via `__getattr__`
- Sub-tags validation
- Attribute type validation

Concrete builders only need to:

1. Set `schema_path` to point to the pre-compiled schema
2. Override `compile()` to produce domain-specific output

## HtmlBuilder

HTML5 document builder using W3C Validator schema.

```python
from genro_bag import Bag
from genro_bag.builders import HtmlBuilder

doc = Bag(builder=HtmlBuilder)
body = doc.body()
div = body.div(id='main')
div.h1(value='Hello')
div.p(value='World')

html = doc.builder.compile()
```

### Schema

The schema file `html/html5_schema.bag.mp` is pre-compiled from
W3C Validator RELAX NG files.

To regenerate (from project root):

```bash
python tools/html5_schema_builder.py \
    --url https://github.com/nickhutchinson/html5-validator/tree/master/schema \
    -o src/genro_bag/builders/html/html5_schema.bag.mp
```

## File Structure

```text
builders/
├── __init__.py          # Public exports
├── html/
│   ├── __init__.py
│   ├── html_builder.py  # HtmlBuilder
│   └── html5_schema.bag.mp  # Pre-compiled schema
└── README.md

tools/
└── html5_schema_builder.py  # Schema generator script (requires lxml)
```
