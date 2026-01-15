# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Test per bug: XSD usa 'value' invece di 'node_value' in call_args_validations."""

from genro_bag.builders.xsd import XsdReader


class TestXsdValueKeyBug:
    """Verifica che XSD reader usi 'node_value' invece di 'value'."""

    def test_xsd_simple_content_uses_wrong_key(self):
        """BUG: XSD reader usa 'value' invece di 'node_value'.

        Il builder cerca 'node_value' in all_args ma XSD produce 'value'.
        Quindi la validazione del contenuto non viene mai applicata.
        """
        # XSD con simpleContent - il contenuto dell'elemento deve essere validato
        xsd = """<?xml version="1.0" encoding="UTF-8"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:element name="price" type="PriceType"/>
            <xs:complexType name="PriceType">
                <xs:simpleContent>
                    <xs:extension base="xs:decimal">
                        <xs:attribute name="currency" type="xs:string"/>
                    </xs:extension>
                </xs:simpleContent>
            </xs:complexType>
        </xs:schema>
        """

        reader = XsdReader(xsd)
        elements = list(reader.iter_elements())

        # Trova l'elemento 'price'
        price_elem = next((e for e in elements if e[0] == "price"), None)
        assert price_elem is not None, "Elemento 'price' non trovato"

        name, sub_tags, call_args_validations = price_elem

        # BUG: call_args_validations contiene 'value' invece di 'node_value'
        assert "node_value" in call_args_validations, (
            f"BUG: XSD usa 'value' invece di 'node_value'. "
            f"Chiavi presenti: {list(call_args_validations.keys())}"
        )

    def test_xsd_simple_type_element_uses_wrong_key(self):
        """BUG: Elementi con tipo semplice usano 'value' invece di 'node_value'."""
        xsd = """<?xml version="1.0" encoding="UTF-8"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:element name="quantity" type="xs:integer"/>
        </xs:schema>
        """

        reader = XsdReader(xsd)
        elements = list(reader.iter_elements())

        quantity_elem = next((e for e in elements if e[0] == "quantity"), None)
        assert quantity_elem is not None

        name, sub_tags, call_args_validations = quantity_elem

        # BUG: 'value' invece di 'node_value'
        assert "node_value" in call_args_validations, (
            f"BUG: XSD usa 'value' invece di 'node_value'. "
            f"Chiavi: {list(call_args_validations.keys())}"
        )
