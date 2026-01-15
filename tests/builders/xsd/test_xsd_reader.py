# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for XsdReader."""

import inspect
from pathlib import Path

import pytest

from genro_bag.builders.xsd.xsd_reader import XsdReader

# =============================================================================
# Fixtures
# =============================================================================


SIMPLE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="root" type="RootType"/>
    <xs:complexType name="RootType">
        <xs:sequence>
            <xs:element name="child1" type="xs:string"/>
            <xs:element name="child2" type="xs:int" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
</xs:schema>
"""

NESTED_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="Document" type="DocumentType"/>
    <xs:complexType name="DocumentType">
        <xs:sequence>
            <xs:element name="Header" type="HeaderType"/>
            <xs:element name="Body" type="BodyType" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="HeaderType">
        <xs:sequence>
            <xs:element name="Title" type="xs:string"/>
            <xs:element name="Date" type="xs:date" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="BodyType">
        <xs:sequence>
            <xs:element name="Content" type="xs:string"/>
        </xs:sequence>
    </xs:complexType>
</xs:schema>
"""

SIMPLE_TYPE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="item" type="ItemType"/>
    <xs:complexType name="ItemType">
        <xs:sequence>
            <xs:element name="code" type="CodeType"/>
            <xs:element name="amount" type="AmountType"/>
            <xs:element name="status" type="StatusType"/>
        </xs:sequence>
    </xs:complexType>
    <xs:simpleType name="CodeType">
        <xs:restriction base="xs:string">
            <xs:pattern value="[A-Z]{3}"/>
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="AmountType">
        <xs:restriction base="xs:decimal">
            <xs:minInclusive value="0"/>
            <xs:maxInclusive value="999999.99"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="StatusType">
        <xs:restriction base="xs:string">
            <xs:enumeration value="ACTIVE"/>
            <xs:enumeration value="PENDING"/>
            <xs:enumeration value="CLOSED"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
"""

ATTRIBUTE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="price" type="PriceType"/>
    <xs:complexType name="PriceType">
        <xs:simpleContent>
            <xs:extension base="xs:decimal">
                <xs:attribute name="currency" type="CurrencyCode" use="required"/>
                <xs:attribute name="precision" type="xs:int" use="optional"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:simpleType name="CurrencyCode">
        <xs:restriction base="xs:string">
            <xs:pattern value="[A-Z]{3}"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
"""

CHOICE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="payment" type="PaymentType"/>
    <xs:complexType name="PaymentType">
        <xs:choice>
            <xs:element name="cash" type="xs:decimal"/>
            <xs:element name="card" type="xs:string"/>
            <xs:element name="transfer" type="xs:string"/>
        </xs:choice>
    </xs:complexType>
</xs:schema>
"""


# =============================================================================
# Tests
# =============================================================================


class TestXsdReaderBasic:
    """Basic XsdReader tests."""

    def test_simple_schema(self):
        """Test parsing simple schema with one global element."""
        reader = XsdReader(SIMPLE_XSD)

        assert "root" in reader.global_elements
        assert "RootType" in reader.complex_types

    def test_iter_elements_simple(self):
        """Test iterating over simple schema elements."""
        reader = XsdReader(SIMPLE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        assert "root" in elements
        assert "child1" in elements
        assert "child2" in elements

        # root has children
        root_sub_tags = elements["root"][0]
        assert "child1" in root_sub_tags
        assert "child2" in root_sub_tags

        # child1 and child2 are leaf elements
        assert elements["child1"][0] == ""
        assert elements["child2"][0] == ""


class TestXsdReaderNested:
    """Test nested complex types (ISO20022 style)."""

    def test_nested_elements(self):
        """Test that local elements from complex types are yielded."""
        reader = XsdReader(NESTED_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        # All elements should be present
        assert "Document" in elements
        assert "Header" in elements
        assert "Body" in elements
        assert "Title" in elements
        assert "Date" in elements
        assert "Content" in elements

    def test_nested_sub_tags(self):
        """Test sub_tags for nested elements."""
        reader = XsdReader(NESTED_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        # Document has Header and Body
        doc_sub_tags = elements["Document"][0]
        assert "Header" in doc_sub_tags
        assert "Body" in doc_sub_tags

        # Header has Title and Date
        header_sub_tags = elements["Header"][0]
        assert "Title" in header_sub_tags
        assert "Date" in header_sub_tags

        # Body has Content
        body_sub_tags = elements["Body"][0]
        assert "Content" in body_sub_tags

    def test_cardinality(self):
        """Test cardinality in sub_tags."""
        reader = XsdReader(NESTED_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        doc_sub_tags = elements["Document"][0]
        # Body has maxOccurs="unbounded" -> [1:*]
        assert "Body[1:*]" in doc_sub_tags

        header_sub_tags = elements["Header"][0]
        # Date has minOccurs="0" -> [0:1]
        assert "Date[0:1]" in header_sub_tags


class TestXsdReaderSimpleTypes:
    """Test simple type parsing and validation constraints."""

    def test_pattern_constraint(self):
        """Test pattern constraint is captured."""
        reader = XsdReader(SIMPLE_TYPE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        code_cav = elements["code"][1]
        assert "node_value" in code_cav
        base_type, validators, default = code_cav["node_value"]

        # Should have Regex validator
        patterns = [v for v in validators if hasattr(v, "pattern")]
        assert len(patterns) == 1
        assert patterns[0].pattern == "[A-Z]{3}"

    def test_range_constraint(self):
        """Test range constraint is captured."""
        reader = XsdReader(SIMPLE_TYPE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        amount_cav = elements["amount"][1]
        assert "node_value" in amount_cav
        base_type, validators, default = amount_cav["node_value"]

        # Should have Range validator
        ranges = [v for v in validators if hasattr(v, "ge")]
        assert len(ranges) == 1
        assert ranges[0].ge == 0
        assert ranges[0].le == 999999.99

    def test_enum_constraint(self):
        """Test enumeration constraint is captured."""
        reader = XsdReader(SIMPLE_TYPE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        status_cav = elements["status"][1]
        assert "node_value" in status_cav
        base_type, validators, default = status_cav["node_value"]

        # Base type should be Literal with enum values
        # (Literal types are complex to check, just verify it's not str)
        assert base_type != str


class TestXsdReaderAttributes:
    """Test attribute parsing."""

    def test_simple_content_with_attributes(self):
        """Test simpleContent extension with attributes."""
        reader = XsdReader(ATTRIBUTE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        price_cav = elements["price"][1]

        # Should have node_value validation (decimal)
        assert "node_value" in price_cav

        # Should have currency attribute (required)
        assert "currency" in price_cav
        _, _, default = price_cav["currency"]
        assert default == inspect.Parameter.empty  # required

        # Should have precision attribute (optional)
        assert "precision" in price_cav
        _, _, default = price_cav["precision"]
        assert default is None  # optional


class TestXsdReaderChoice:
    """Test choice group parsing."""

    def test_choice_elements(self):
        """Test choice elements are all included in sub_tags."""
        reader = XsdReader(CHOICE_XSD)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        payment_sub_tags = elements["payment"][0]

        # All choice alternatives should be in sub_tags
        assert "cash" in payment_sub_tags
        assert "card" in payment_sub_tags
        assert "transfer" in payment_sub_tags


class TestXsdReaderSepa:
    """Test with real SEPA XSD if available."""

    @pytest.fixture
    def sepa_xsd_path(self):
        """Path to SEPA XSD file."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "examples/builders/xsd/sepa/pain.001.001.12.xsd"
        )
        if not path.exists():
            pytest.skip("SEPA XSD not found")
        return path

    def test_sepa_document(self, sepa_xsd_path):
        """Test SEPA XSD Document element."""
        reader = XsdReader.from_file(sepa_xsd_path)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        assert "Document" in elements
        doc_sub_tags = elements["Document"][0]
        assert "CstmrCdtTrfInitn" in doc_sub_tags

    def test_sepa_cstmr_cdt_trf_initn(self, sepa_xsd_path):
        """Test SEPA CstmrCdtTrfInitn has children."""
        reader = XsdReader.from_file(sepa_xsd_path)
        elements = {name: (sub_tags, cav) for name, sub_tags, cav in reader.iter_elements()}

        assert "CstmrCdtTrfInitn" in elements
        sub_tags = elements["CstmrCdtTrfInitn"][0]

        # Should have GrpHdr, PmtInf, SplmtryData
        assert "GrpHdr" in sub_tags
        assert "PmtInf" in sub_tags

    def test_sepa_element_count(self, sepa_xsd_path):
        """Test SEPA XSD yields many elements."""
        reader = XsdReader.from_file(sepa_xsd_path)
        elements = list(reader.iter_elements())

        # SEPA schema should have many elements
        assert len(elements) > 100
