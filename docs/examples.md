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

## Italian Electronic Invoice (FatturaPA)

Build validated Italian electronic invoices using a custom builder.

```python
from genro_bag import Bag
from genro_bag.builders import BagBuilderBase, element

class FatturaElettronicaBuilder(BagBuilderBase):
    """Builder for Italian Electronic Invoice (FatturaPA) format."""

    @element(sub_tags='header, body')
    def fattura(self, target, tag, versione='FPR12', **attr):
        """Root element for electronic invoice."""
        return self.child(target, tag, versione=versione, **attr)

    # === Header Section ===

    @element(sub_tags='trasmissione, cedente, cessionario')
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
        if progressivo:
            attr['progressivo'] = progressivo
        attr['formato'] = formato
        if codice_destinatario:
            attr['codice_destinatario'] = codice_destinatario
        if pec:
            attr['pec'] = pec
        return self.child(target, tag, **attr)

    @element(sub_tags='anagrafica, sede')
    def cedente(self, target, tag,
                partita_iva=None,
                codice_fiscale=None,
                **attr):
        """Seller (cedente/prestatore) information."""
        if partita_iva:
            attr['partita_iva'] = partita_iva
        if codice_fiscale:
            attr['codice_fiscale'] = codice_fiscale
        return self.child(target, tag, **attr)

    @element(sub_tags='anagrafica, sede')
    def cessionario(self, target, tag,
                    partita_iva=None,
                    codice_fiscale=None,
                    **attr):
        """Buyer (cessionario/committente) information."""
        if partita_iva:
            attr['partita_iva'] = partita_iva
        if codice_fiscale:
            attr['codice_fiscale'] = codice_fiscale
        return self.child(target, tag, **attr)

    @element()
    def anagrafica(self, target, tag,
                   denominazione=None,
                   nome=None,
                   cognome=None,
                   **attr):
        """Company or person name."""
        if denominazione:
            attr['denominazione'] = denominazione
        if nome:
            attr['nome'] = nome
        if cognome:
            attr['cognome'] = cognome
        return self.child(target, tag, **attr)

    @element()
    def sede(self, target, tag,
             indirizzo=None,
             cap=None,
             comune=None,
             provincia=None,
             nazione='IT',
             **attr):
        """Address information."""
        if indirizzo:
            attr['indirizzo'] = indirizzo
        if cap:
            attr['cap'] = cap
        if comune:
            attr['comune'] = comune
        if provincia:
            attr['provincia'] = provincia
        attr['nazione'] = nazione
        return self.child(target, tag, **attr)

    # === Body Section ===

    @element(sub_tags='dati_generali, dati_beni, dati_pagamento')
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
        attr['tipo_documento'] = tipo_documento
        attr['divisa'] = divisa
        if data:
            attr['data'] = data
        if numero:
            attr['numero'] = numero
        return self.child(target, tag, **attr)

    @element(sub_tags='linea')
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
        if numero:
            attr['numero'] = numero
        if descrizione:
            attr['descrizione'] = descrizione
        if quantita is not None:
            attr['quantita'] = quantita
        if prezzo_unitario is not None:
            attr['prezzo_unitario'] = prezzo_unitario
        if prezzo_totale is not None:
            attr['prezzo_totale'] = prezzo_totale
        if aliquota_iva is not None:
            attr['aliquota_iva'] = aliquota_iva
        return self.child(target, tag, **attr)

    @element()
    def dati_pagamento(self, target, tag,
                       condizioni='TP02',
                       modalita='MP05',
                       importo=None,
                       scadenza=None,
                       iban=None,
                       **attr):
        """Payment information."""
        attr['condizioni'] = condizioni
        attr['modalita'] = modalita
        if importo is not None:
            attr['importo'] = importo
        if scadenza:
            attr['scadenza'] = scadenza
        if iban:
            attr['iban'] = iban
        return self.child(target, tag, **attr)


# === Usage Example ===

# Create invoice
bag = Bag(builder=FatturaElettronicaBuilder)

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

# === Accessing Data ===
# IMPORTANT: Avoid using auto-generated labels like 'fattura_0', 'header_0' etc.
# They depend on insertion order and are fragile. Use these alternatives instead:

# Option 1: Use saved references (preferred - most stable)
print(fattura.parent_node.attr.get('versione'))  # FPR12

# Option 2: Use node_label for explicit, stable labels
# When building, pass node_label to create predictable paths:
# cedente = header.cedente(partita_iva='IT01234567890', node_label='seller')
# Then access as: header['seller?partita_iva']

# Option 3: Use node_position for positional access
cedente_node = header.get_node_at(1)  # cedente is second child in header
print(cedente_node.attr.get('partita_iva'))  # IT01234567890

# Option 4: Iterate and filter by tag
for node in body:
    if node.tag == 'dati_generali':
        print(node.attr.get('numero'))  # 2025/001
        break

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
def compute_invoice_totals(beni_bag):
    """Compute invoice totals from line items.

    Args:
        beni_bag: The dati_beni Bag (pass reference, not path with auto-labels)
    """
    imponibile = 0
    iva = 0

    for node in beni_bag:
        if node.tag == 'linea':  # Filter by tag, not label
            totale = node.attr.get('prezzo_totale', 0)
            aliquota = node.attr.get('aliquota_iva', 0)

            imponibile += totale
            iva += totale * aliquota / 100

    return {
        'imponibile': imponibile,
        'iva': iva,
        'totale': imponibile + iva
    }

# Use saved reference 'beni' from when we built the invoice
totals = compute_invoice_totals(beni)
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
