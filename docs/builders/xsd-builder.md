# XsdBuilder

XsdBuilder automatically generates a typed builder from any XML Schema Definition (XSD) file. Instead of manually defining builder methods for each XML element, you simply load the XSD and the builder creates methods dynamically based on the schema.

## Why XsdBuilder?

Creating builders manually for complex XML formats like invoices, financial reports, or API specifications is tedious and error-prone. XsdBuilder solves this by:

- **Automatic method generation** - All elements from the XSD become callable methods
- **No manual coding** - Just load the schema, builder is ready
- **Standards compliance** - Follows the official XSD structure exactly
- **Industry formats** - Works with FatturaPA, UBL, XBRL, and any XSD-based format

## Basic Usage

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Use with Bag - pass XSD file path via builder_xsd_source
doc = Bag(builder=XsdBuilder, builder_xsd_source='schema.xsd')

# Methods are generated from XSD elements
root = doc.RootElement(attr1='value')
child = root.ChildElement()
child.GrandChild(value='text content')

# Can also use URL
doc = Bag(builder=XsdBuilder, builder_xsd_source='https://example.com/schema.xsd')
```

## How It Works

1. **Parse XSD**: Load the XSD file and parse it into a Bag using `from_xml()`

2. **Extract Schema Structure**:
   - Collects all `xs:complexType` and `xs:simpleType` definitions
   - Collects all `xs:element` definitions
   - Resolves type references to determine allowed children

3. **Generate Methods**: For each element in the schema:
   - Creates a dynamic method accessible via `builder.ElementName`
   - Tracks which child elements are allowed (from complexType definitions)
   - Distinguishes leaf elements (simpleType) from branch elements (complexType)

4. **Runtime Validation**: The builder knows valid children for each element,
   enabling validation during tree construction.

## API Reference

### XsdBuilder

```python
class XsdBuilder(BagBuilderBase):
    def __init__(self, schema_store: Bag):
        """Create builder from XSD schema Bag."""

    @property
    def elements(self) -> frozenset[str]:
        """All valid element names in the schema."""

    def get_children(self, element: str) -> frozenset[str] | None:
        """Get allowed children for an element."""
```

### Dynamic Methods

For each element `Foo` in the schema, the builder provides:

```python
builder.Foo(target, value=None, **attributes) -> Bag | BagNode
```

- `target`: The parent Bag to add this element to
- `value`: Text content for leaf elements
- `**attributes`: XML attributes for the element

## Example: SEPA Credit Transfer (ISO 20022 pain.001)

SEPA Credit Transfer is the European standard for bank transfers. The pain.001 schema
defines the Customer Credit Transfer Initiation message.

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Create Credit Transfer document from ISO 20022 pain.001 schema
doc = Bag(builder=XsdBuilder, builder_xsd_source='pain.001.001.12.xsd')
root = doc.Document()
cstmr = root.CstmrCdtTrfInitn()

# Group Header - message identification
grp_hdr = cstmr.GrpHdr()
grp_hdr.MsgId(value='MSGID-2025-001')
grp_hdr.CreDtTm(value='2025-01-07T10:30:00')
grp_hdr.NbOfTxs(value='1')
grp_hdr.CtrlSum(value='1500.00')

# Initiating Party
initg_pty = grp_hdr.InitgPty()
initg_pty.Nm(value='Acme Corporation S.r.l.')

# Payment Information
pmt_inf = cstmr.PmtInf()
pmt_inf.PmtInfId(value='PMTINF-001')
pmt_inf.PmtMtd(value='TRF')  # Transfer
pmt_inf.NbOfTxs(value='1')
pmt_inf.CtrlSum(value='1500.00')

# Requested Execution Date
pmt_inf.ReqdExctnDt().Dt(value='2025-01-10')

# Debtor (who pays)
dbtr = pmt_inf.Dbtr()
dbtr.Nm(value='Acme Corporation S.r.l.')
dbtr_addr = dbtr.PstlAdr()
dbtr_addr.Ctry(value='IT')
dbtr_addr.AdrLine(value='Via Roma 123, 00100 Roma')

# Debtor Account
dbtr_acct = pmt_inf.DbtrAcct()
dbtr_acct.Id().IBAN(value='IT60X0542811101000000123456')

# Debtor Agent (bank)
dbtr_agt = pmt_inf.DbtrAgt()
dbtr_agt.FinInstnId().BICFI(value='BABOROMA1XXX')

# Credit Transfer Transaction
cdt_trf = pmt_inf.CdtTrfTxInf()

# Payment ID
pmt_id = cdt_trf.PmtId()
pmt_id.InstrId(value='INSTR-001')
pmt_id.EndToEndId(value='E2E-INV-2025-001')

# Amount
amt = cdt_trf.Amt()
amt.InstdAmt(value='1500.00', Ccy='EUR')

# Creditor Agent (beneficiary's bank)
cdtr_agt = cdt_trf.CdtrAgt()
cdtr_agt.FinInstnId().BICFI(value='DEUTDEFF')

# Creditor (who receives)
cdtr = cdt_trf.Cdtr()
cdtr.Nm(value='Supplier GmbH')
cdtr_addr = cdtr.PstlAdr()
cdtr_addr.Ctry(value='DE')
cdtr_addr.AdrLine(value='Hauptstrasse 1, 60311 Frankfurt')

# Creditor Account
cdtr_acct = cdt_trf.CdtrAcct()
cdtr_acct.Id().IBAN(value='DE89370400440532013000')

# Remittance Information (payment reference)
rmt_inf = cdt_trf.RmtInf()
rmt_inf.Ustrd(value='Invoice INV-2025-001 - Consulting services')

# Generate XML
print(doc.to_xml(pretty=True))
```

Output:

```xml
<Document>
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSGID-2025-001</MsgId>
      <CreDtTm>2025-01-07T10:30:00</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>1500.00</CtrlSum>
      <InitgPty>
        <Nm>Acme Corporation S.r.l.</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMTINF-001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      ...
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
```

## Example: Italian Electronic Invoice (FatturaPA)

The FatturaPA is Italy's mandatory electronic invoice format with a complex XSD schema.

```python
from genro_bag import Bag
from genro_bag.builders import XsdBuilder

# Create invoice from official FatturaPA schema - all methods generated from XSD
invoice = Bag(builder=XsdBuilder, builder_xsd_source='Schema_VFPA12.xsd')
fe = invoice.FatturaElettronica(versione='FPR12')

# Header
header = fe.FatturaElettronicaHeader()

# Transmission data
dati_trasm = header.DatiTrasmissione()
id_trasm = dati_trasm.IdTrasmittente()
id_trasm.IdPaese(value='IT')
id_trasm.IdCodice(value='01234567890')
dati_trasm.ProgressivoInvio(value='00001')
dati_trasm.FormatoTrasmissione(value='FPR12')
dati_trasm.CodiceDestinatario(value='0000000')

# Seller
seller = header.CedentePrestatore()
seller_data = seller.DatiAnagrafici()
seller_vat = seller_data.IdFiscaleIVA()
seller_vat.IdPaese(value='IT')
seller_vat.IdCodice(value='01234567890')
seller_name = seller_data.Anagrafica()
seller_name.Denominazione(value='Acme S.r.l.')
seller_data.RegimeFiscale(value='RF01')

seller_addr = seller.Sede()
seller_addr.Indirizzo(value='Via Roma 1')
seller_addr.CAP(value='00100')
seller_addr.Comune(value='Roma')
seller_addr.Provincia(value='RM')
seller_addr.Nazione(value='IT')

# ... continue with buyer, body, line items, etc.
```

## Introspection

You can inspect the parsed schema:

```python
# List all elements
print(f"Schema has {len(builder.elements)} elements")
print(f"Sample: {sorted(builder.elements)[:10]}")

# Get allowed children for an element
children = builder.get_children('FatturaElettronicaHeader')
print(f"Header can contain: {children}")
```

## Supported Formats

XsdBuilder works with any XSD-based format:

| Format | Description |
|--------|-------------|
| **FatturaPA** | Italian Electronic Invoice |
| **UBL** | Universal Business Language |
| **XBRL** | Financial Reporting |
| **SVG** | Scalable Vector Graphics |
| **KML** | Keyhole Markup Language |
| **WSDL** | Web Services Description |
| Custom | Any valid XSD schema |

## Limitations

- Namespace handling is basic (prefixes are stripped)
- Cardinality constraints (minOccurs/maxOccurs) are not fully enforced
- Some advanced XSD features (substitutionGroup, abstract types) may not be supported

## See Also

- [W3C XML Schema](https://www.w3.org/XML/Schema)
- [FatturaPA Schema](https://www.fatturapa.gov.it/it/norme-e-regole/documentazione-fattura-elettronica/formato-fatturapa/)
- [Custom Builders](custom-builders.md) - Creating builders manually
- [HTML Builder](html-builder.md) - Schema-based HTML builder
