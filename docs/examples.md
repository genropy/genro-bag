# Examples

Real-world examples showing Bag capabilities in practical scenarios.

## Multiple API Specifications

A single Bag can aggregate multiple OpenAPI specifications, providing unified access to different services.

```python
from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

# Create an API registry
apis = Bag()

# Add multiple OpenAPI specs
apis['petstore'] = OpenApiResolver(
    'https://petstore3.swagger.io/api/v3/openapi.json'
)
apis['github'] = OpenApiResolver(
    'https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json'
)

# Navigate Petstore API
apis['petstore.info.title']        # 'Swagger Petstore - OpenAPI 3.0'
apis['petstore.info.version']      # '1.0.19'

# List available paths
for path in apis['petstore.paths'].keys():
    print(path)
# /pet
# /pet/findByStatus
# /pet/findByTags
# /pet/{petId}
# ...

# Access endpoint details
pet_post = apis['petstore.paths./pet.post']
pet_post['summary']                # 'Add a new pet to the store'
pet_post['operationId']            # 'addPet'

# Access request body schema
schema = apis['petstore.paths./pet.post.requestBody.content.application/json.schema']

# Compare with GitHub API
apis['github.info.title']          # 'GitHub REST API'
apis['github.paths./repos/{owner}/{repo}.get.summary']
```

### Building an API Explorer

```python
from genro_bag import Bag
from genro_bag.resolvers import OpenApiResolver

def create_api_explorer(*specs):
    """Create a unified API explorer from multiple specs."""
    explorer = Bag()

    for name, url in specs:
        explorer[name] = OpenApiResolver(url, cache_time=3600)

    return explorer

# Usage
explorer = create_api_explorer(
    ('petstore', 'https://petstore3.swagger.io/api/v3/openapi.json'),
    ('jsonplaceholder', 'https://raw.githubusercontent.com/typicode/jsonplaceholder/master/openapi.json'),
)

# Unified access to all APIs
for api_name in explorer.keys():
    info = explorer[f'{api_name}.info']
    print(f"{api_name}: {info['title']} v{info['version']}")
```

## HTML Page Builder

Build complete HTML pages with the fluent builder API.

```python
from genro_bag.builders import HtmlPage

# Create a landing page
page = HtmlPage()

# Head section
page.head.meta(charset='utf-8')
page.head.meta(name='viewport', content='width=device-width, initial-scale=1')
page.head.title(value='My Application')
page.head.link(rel='stylesheet', href='/static/style.css')

# Body content
with page.body as body:
    # Navigation
    nav = body.nav(class_='navbar')
    nav.a(value='Home', href='/')
    nav.a(value='About', href='/about')
    nav.a(value='Contact', href='/contact')

    # Main content
    main = body.main(class_='container')

    hero = main.section(class_='hero')
    hero.h1(value='Welcome to My App')
    hero.p(value='A modern web application built with Python')
    hero.a(value='Get Started', href='/signup', class_='btn btn-primary')

    # Features grid
    features = main.section(class_='features')
    features.h2(value='Features')

    grid = features.div(class_='grid')
    for title, desc in [
        ('Fast', 'Lightning fast performance'),
        ('Secure', 'Enterprise-grade security'),
        ('Scalable', 'Grows with your needs'),
    ]:
        card = grid.div(class_='card')
        card.h3(value=title)
        card.p(value=desc)

    # Footer
    footer = body.footer()
    footer.p(value='© 2025 My Company')

# Generate HTML
html = page.to_html()
print(html)
```

Output:
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My Application</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <main class="container">
        <section class="hero">
            <h1>Welcome to My App</h1>
            <p>A modern web application built with Python</p>
            <a href="/signup" class="btn btn-primary">Get Started</a>
        </section>
        <section class="features">
            <h2>Features</h2>
            <div class="grid">
                <div class="card">
                    <h3>Fast</h3>
                    <p>Lightning fast performance</p>
                </div>
                ...
            </div>
        </section>
    </main>
    <footer>
        <p>© 2025 My Company</p>
    </footer>
</body>
</html>
```

### Dynamic Table Generation

```python
from genro_bag.builders import HtmlPage

def create_data_table(headers, rows):
    """Generate an HTML table from data."""
    page = HtmlPage()
    page.head.title(value='Data Report')

    table = page.body.table(class_='data-table')

    # Header row
    thead = table.thead()
    tr = thead.tr()
    for header in headers:
        tr.th(value=header)

    # Data rows
    tbody = table.tbody()
    for row in rows:
        tr = tbody.tr()
        for cell in row:
            tr.td(value=str(cell))

    return page.to_html()

# Usage
html = create_data_table(
    headers=['ID', 'Name', 'Email', 'Status'],
    rows=[
        [1, 'Alice', 'alice@example.com', 'Active'],
        [2, 'Bob', 'bob@example.com', 'Pending'],
        [3, 'Carol', 'carol@example.com', 'Active'],
    ]
)
```

## Italian Electronic Invoice (FatturaPA)

Build validated Italian electronic invoices using a custom builder.

```python
from genro_bag import Bag
from genro_bag.builders import BagBuilderBase, element

class FatturaElettronicaBuilder(BagBuilderBase):
    """Builder for Italian Electronic Invoice (FatturaPA) format."""

    @element(children=['header', 'body'])
    def fattura(self, target, tag, versione='FPR12', **attr):
        """Root element for electronic invoice."""
        return self.child(target, tag, versione=versione, **attr)

    # === Header Section ===

    @element(children=['trasmissione', 'cedente', 'cessionario'])
    def header(self, target, tag, **attr):
        """Invoice header with parties information."""
        return self.child(target, tag, **attr)

    @element()
    def trasmissione(self, target, tag,
                     progressivo=None,
                     formato='FPR12',
                     codice_destinatario=None,
                     pec=None,
                     **attr):
        """Transmission data."""
        node = self.child(target, tag, **attr)
        if progressivo:
            node.set_attr('progressivo', progressivo)
        node.set_attr('formato', formato)
        if codice_destinatario:
            node.set_attr('codice_destinatario', codice_destinatario)
        if pec:
            node.set_attr('pec', pec)
        return node

    @element(children=['anagrafica', 'sede'])
    def cedente(self, target, tag,
                partita_iva=None,
                codice_fiscale=None,
                **attr):
        """Seller (cedente/prestatore) information."""
        node = self.child(target, tag, **attr)
        if partita_iva:
            node.set_attr('partita_iva', partita_iva)
        if codice_fiscale:
            node.set_attr('codice_fiscale', codice_fiscale)
        return node

    @element(children=['anagrafica', 'sede'])
    def cessionario(self, target, tag,
                    partita_iva=None,
                    codice_fiscale=None,
                    **attr):
        """Buyer (cessionario/committente) information."""
        node = self.child(target, tag, **attr)
        if partita_iva:
            node.set_attr('partita_iva', partita_iva)
        if codice_fiscale:
            node.set_attr('codice_fiscale', codice_fiscale)
        return node

    @element()
    def anagrafica(self, target, tag,
                   denominazione=None,
                   nome=None,
                   cognome=None,
                   **attr):
        """Company or person name."""
        node = self.child(target, tag, **attr)
        if denominazione:
            node.set_attr('denominazione', denominazione)
        if nome:
            node.set_attr('nome', nome)
        if cognome:
            node.set_attr('cognome', cognome)
        return node

    @element()
    def sede(self, target, tag,
             indirizzo=None,
             cap=None,
             comune=None,
             provincia=None,
             nazione='IT',
             **attr):
        """Address information."""
        node = self.child(target, tag, **attr)
        if indirizzo:
            node.set_attr('indirizzo', indirizzo)
        if cap:
            node.set_attr('cap', cap)
        if comune:
            node.set_attr('comune', comune)
        if provincia:
            node.set_attr('provincia', provincia)
        node.set_attr('nazione', nazione)
        return node

    # === Body Section ===

    @element(children=['dati_generali', 'dati_beni', 'dati_pagamento'])
    def body(self, target, tag, **attr):
        """Invoice body with details."""
        return self.child(target, tag, **attr)

    @element()
    def dati_generali(self, target, tag,
                      tipo_documento='TD01',
                      divisa='EUR',
                      data=None,
                      numero=None,
                      **attr):
        """General invoice data."""
        node = self.child(target, tag, **attr)
        node.set_attr('tipo_documento', tipo_documento)
        node.set_attr('divisa', divisa)
        if data:
            node.set_attr('data', data)
        if numero:
            node.set_attr('numero', numero)
        return node

    @element(children=['linea'])
    def dati_beni(self, target, tag, **attr):
        """Line items section."""
        return self.child(target, tag, **attr)

    @element()
    def linea(self, target, tag,
              numero=None,
              descrizione=None,
              quantita=None,
              prezzo_unitario=None,
              prezzo_totale=None,
              aliquota_iva=None,
              **attr):
        """Single line item."""
        node = self.child(target, tag, **attr)
        if numero:
            node.set_attr('numero', numero)
        if descrizione:
            node.set_attr('descrizione', descrizione)
        if quantita is not None:
            node.set_attr('quantita', quantita)
        if prezzo_unitario is not None:
            node.set_attr('prezzo_unitario', prezzo_unitario)
        if prezzo_totale is not None:
            node.set_attr('prezzo_totale', prezzo_totale)
        if aliquota_iva is not None:
            node.set_attr('aliquota_iva', aliquota_iva)
        return node

    @element()
    def dati_pagamento(self, target, tag,
                       condizioni='TP02',
                       modalita='MP05',
                       importo=None,
                       scadenza=None,
                       iban=None,
                       **attr):
        """Payment information."""
        node = self.child(target, tag, **attr)
        node.set_attr('condizioni', condizioni)
        node.set_attr('modalita', modalita)
        if importo is not None:
            node.set_attr('importo', importo)
        if scadenza:
            node.set_attr('scadenza', scadenza)
        if iban:
            node.set_attr('iban', iban)
        return node


# === Usage Example ===

# Create invoice
bag = Bag(builder=FatturaElettronicaBuilder())

fattura = bag.fattura(versione='FPR12')

# Header
header = fattura.header()

header.trasmissione(
    progressivo='00001',
    formato='FPR12',
    codice_destinatario='0000000'
)

cedente = header.cedente(
    partita_iva='IT01234567890',
    codice_fiscale='01234567890'
)
cedente.anagrafica(denominazione='Acme S.r.l.')
cedente.sede(
    indirizzo='Via Roma 1',
    cap='00100',
    comune='Roma',
    provincia='RM'
)

cessionario = header.cessionario(
    partita_iva='IT09876543210',
    codice_fiscale='09876543210'
)
cessionario.anagrafica(denominazione='Cliente S.p.A.')
cessionario.sede(
    indirizzo='Via Milano 50',
    cap='20100',
    comune='Milano',
    provincia='MI'
)

# Body
body = fattura.body()

body.dati_generali(
    tipo_documento='TD01',  # Fattura
    divisa='EUR',
    data='2025-01-07',
    numero='2025/001'
)

beni = body.dati_beni()
beni.linea(
    numero=1,
    descrizione='Consulenza informatica',
    quantita=10,
    prezzo_unitario=100.00,
    prezzo_totale=1000.00,
    aliquota_iva=22.00
)
beni.linea(
    numero=2,
    descrizione='Sviluppo software',
    quantita=5,
    prezzo_unitario=200.00,
    prezzo_totale=1000.00,
    aliquota_iva=22.00
)

body.dati_pagamento(
    condizioni='TP02',  # Pagamento completo
    modalita='MP05',    # Bonifico
    importo=2440.00,
    scadenza='2025-02-07',
    iban='IT60X0542811101000000123456'
)

# Access data
print(bag['fattura_0?versione'])  # FPR12
print(bag['fattura_0.header_0.cedente_0?partita_iva'])  # IT01234567890
print(bag['fattura_0.body_0.dati_generali_0?numero'])  # 2025/001

# Serialize to XML for transmission
xml = bag.to_xml()
```

### Invoice Validation

The builder ensures structure validity:

```python
# This works - linea is allowed inside dati_beni
beni = body.dati_beni()
beni.linea(descrizione='Valid item')

# This raises BuilderChildError - linea not allowed at root
try:
    fattura.linea(descrizione='Invalid')
except Exception as e:
    print(f"Validation error: {e}")
```

### Computing Totals

```python
from genro_bag import Bag

def compute_invoice_totals(invoice_bag):
    """Compute invoice totals from line items."""
    beni = invoice_bag['fattura_0.body_0.dati_beni_0']

    imponibile = 0
    iva = 0

    for node in beni:
        totale = node.attr.get('prezzo_totale', 0)
        aliquota = node.attr.get('aliquota_iva', 0)

        imponibile += totale
        iva += totale * aliquota / 100

    return {
        'imponibile': imponibile,
        'iva': iva,
        'totale': imponibile + iva
    }

totals = compute_invoice_totals(bag)
print(f"Imponibile: €{totals['imponibile']:.2f}")
print(f"IVA: €{totals['iva']:.2f}")
print(f"Totale: €{totals['totale']:.2f}")
# Imponibile: €2000.00
# IVA: €440.00
# Totale: €2440.00
```

## Configuration Management

Use Bag with DirectoryResolver for hierarchical configuration.

```python
from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver

# Load configuration from directory structure
# /etc/myapp/
#   database.xml
#   cache.xml
#   logging.xml
#   services/
#     api.xml
#     worker.xml

config = Bag()
config['settings'] = DirectoryResolver('/etc/myapp/')

# Access configuration
db_host = config['settings.database.host']
cache_ttl = config['settings.cache.ttl']
api_port = config['settings.services.api.port']

# With subscriptions for live reload
def on_config_change(node, evt, **kw):
    print(f"Configuration changed: {node.label}")
    # Trigger application reconfiguration

config.subscribe('config_watcher', update=on_config_change)
```

## Next Steps

- Explore the [Builders documentation](builders/index.md) for custom builders
- Learn about [Resolvers](resolvers.md) for lazy loading
- Understand [Subscriptions](subscriptions.md) for reactivity
