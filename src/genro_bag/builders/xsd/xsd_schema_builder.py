# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0
"""Generate BagBuilder schema from XSD files.

This module parses XSD (XML Schema Definition) files and generates a schema
compatible with BagBuilderBase. It extracts:
- Element definitions with children (sub_tags)
- Cardinality constraints ([min:max])
- Attribute definitions with validations
- SimpleType restrictions (pattern, enum, length, range)

Prerequisites:
    No external dependencies - uses xml.etree.ElementTree (stdlib)

Usage:
    # From local XSD file
    python -m genro_bag.builders.xsd.xsd_schema_builder schema.xsd -o schema.bag.mp

    # From URL
    python -m genro_bag.builders.xsd.xsd_schema_builder --url https://example.com/schema.xsd -o schema.bag.mp

    # With JSON output for inspection
    python -m genro_bag.builders.xsd.xsd_schema_builder schema.xsd -o schema.bag.mp --json

    # Specify root elements to include
    python -m genro_bag.builders.xsd.xsd_schema_builder schema.xsd -o schema.bag.mp --roots Document,Header

Output format:
    The schema contains elements with:
    - sub_tags: allowed children with cardinality, e.g., 'Nm[1:1],Id[0:1],Tp[0:*]'
    - call_args_validations: type/pattern/enum constraints for value and attributes
"""

from __future__ import annotations

import argparse
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from genro_bag import Bag
from genro_bag.builders import SchemaBuilder

XSD_NS = "http://www.w3.org/2001/XMLSchema"
NS = {"xs": XSD_NS}

BUILTIN_MAP = {
    "string": "string",
    "normalizedString": "string",
    "token": "string",
    "integer": "int",
    "int": "int",
    "long": "int",
    "short": "int",
    "decimal": "decimal",
    "boolean": "bool",
    "date": "string",
    "dateTime": "string",
    "time": "string",
    "anyURI": "string",
}


# =============================================================================
# Type model (dataclasses)
# =============================================================================


@dataclass
class SimpleSpec:
    """Specification for a simple type (string, int, enum, etc.)."""

    base: str = "string"
    pattern: str | None = None
    values: list[str] | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_inclusive: Decimal | None = None
    max_inclusive: Decimal | None = None
    total_digits: int | None = None
    fraction_digits: int | None = None


@dataclass
class AttrSpec:
    """Specification for an attribute."""

    name: str
    use: str = "optional"  # optional|required|prohibited
    type_spec: SimpleSpec | None = None


@dataclass
class ChildSpec:
    """Specification for a child element."""

    name: str
    min_occurs: int = 1
    max_occurs: int | None = 1  # None means unbounded


@dataclass
class ComplexSpec:
    """Specification for a complex type."""

    children_seq: list[ChildSpec | list[ChildSpec]] = field(default_factory=list)
    attrs: list[AttrSpec] = field(default_factory=list)
    simple_content: SimpleSpec | None = None
    mixed: bool = False


# =============================================================================
# XsdSchemaBuilder class
# =============================================================================


class XsdSchemaBuilder:
    """Build BagBuilder schema from XSD using xml.etree.ElementTree.

    Extracts:
    - Children with min/max occurs and order
    - Attributes with restrictions
    - SimpleType restrictions for element value

    Usage:
        builder = XsdSchemaBuilder('schema.xsd')
        schema = builder.build_bag_schema()
        schema.builder.compile('schema.bag.mp')
    """

    def __init__(self, xsd_source: str | Path):
        """Initialize the builder with an XSD source.

        Args:
            xsd_source: Path to XSD file or URL
        """
        self.xsd_source = xsd_source
        self.tree = self._load_tree(xsd_source)
        root = self.tree.getroot()
        if root is None:
            raise ValueError(f"Invalid XSD: no root element in {xsd_source}")
        self.root: ET.Element = root
        self.tns = self.root.get("targetNamespace")

        # Registries
        self.simple_types: dict[str, SimpleSpec] = {}
        self.complex_types: dict[str, ComplexSpec] = {}
        self.global_elements: dict[str, ET.Element] = {}

        self._index_schema()

    # -------------------------------------------------------------------------
    # Loading and indexing
    # -------------------------------------------------------------------------

    def _load_tree(self, src: str | Path) -> ET.ElementTree[ET.Element]:
        """Load XSD from file path or URL."""
        path_str = str(src)
        if path_str.startswith(("http://", "https://")):
            req = urllib.request.Request(path_str, headers={"User-Agent": "xsd-schema-builder"})
            with urllib.request.urlopen(req) as response:
                data = response.read()
            return ET.ElementTree(ET.fromstring(data))
        return ET.parse(path_str)  # type: ignore[return-value]

    def _index_schema(self) -> None:
        """Index all global types and elements."""
        for child in self.root:
            if child.tag == self._q("simpleType"):
                name = child.get("name")
                if name:
                    self.simple_types[name] = self._parse_simple_type(child)
            elif child.tag == self._q("complexType"):
                name = child.get("name")
                if name:
                    self.complex_types[name] = self._parse_complex_type(child)
            elif child.tag == self._q("element"):
                name = child.get("name")
                if name:
                    self.global_elements[name] = child

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _q(self, tag: str) -> str:
        """Return fully qualified tag name."""
        return f"{{{XSD_NS}}}{tag}"

    def _strip_ns(self, name: str | None) -> str:
        """Strip namespace prefix from name."""
        if name is None:
            return ""
        if "}" in name:
            return name.split("}", 1)[1]
        if ":" in name:
            return name.split(":", 1)[1]
        return name

    def _occurs(self, node: ET.Element) -> tuple[int, int | None]:
        """Return (min, max) where max=None means unbounded."""
        min_str = node.get("minOccurs")
        max_str = node.get("maxOccurs")
        min_o = int(min_str) if min_str is not None else 1
        if max_str is None:
            max_o: int | None = 1
        elif max_str == "unbounded":
            max_o = None
        else:
            max_o = int(max_str)
        return min_o, max_o

    def _fmt_card(self, min_o: int, max_o: int | None) -> str:
        """Format cardinality as [min:max]."""
        if min_o == 0 and max_o is None:
            return "[0:*]"
        if min_o == 1 and max_o == 1:
            return ""  # Default, no need to show
        if max_o is None:
            return f"[{min_o}:*]"
        return f"[{min_o}:{max_o}]"

    def _xsd_builtin_to_python(self, xsd_type: str) -> str:
        """Convert XSD builtin type to Python type name."""
        return BUILTIN_MAP.get(xsd_type, "string")

    def _mul_max(self, a: int | None, b: int | None) -> int | None:
        """Multiply max values (None means unbounded)."""
        if a is None or b is None:
            return None
        return a * b

    def _merge_occ(
        self, prev: tuple[int, int | None] | None, cur: tuple[int, int | None]
    ) -> tuple[int, int | None]:
        """Merge occurrences (conservative union)."""
        if prev is None:
            return cur
        pmin, pmax = prev
        cmin, cmax = cur
        min_o = min(pmin, cmin)
        max_o = None if pmax is None or cmax is None else max(pmax, cmax)
        return (min_o, max_o)

    # -------------------------------------------------------------------------
    # SimpleType parsing
    # -------------------------------------------------------------------------

    def _parse_simple_type(self, node: ET.Element) -> SimpleSpec:
        """Parse xs:simpleType and return SimpleSpec."""
        spec = SimpleSpec()
        restriction = node.find("xs:restriction", NS)
        if restriction is None:
            return spec

        base = restriction.get("base")
        if base:
            base = self._strip_ns(base)
            spec.base = self._xsd_builtin_to_python(base)

        # Parse facets
        for facet in list(restriction):
            tag = self._strip_ns(facet.tag)
            val = facet.get("value")
            if tag == "pattern" and val:
                spec.pattern = val
            elif tag == "enumeration" and val:
                if spec.values is None:
                    spec.values = []
                    spec.base = "enum"
                spec.values.append(val)
            elif tag == "minLength" and val:
                spec.min_length = int(val)
            elif tag == "maxLength" and val:
                spec.max_length = int(val)
            elif tag == "minInclusive" and val:
                spec.min_inclusive = Decimal(val)
            elif tag == "maxInclusive" and val:
                spec.max_inclusive = Decimal(val)
            elif tag == "totalDigits" and val:
                spec.total_digits = int(val)
            elif tag == "fractionDigits" and val:
                spec.fraction_digits = int(val)

        return spec

    def _resolve_simple(self, type_qname: str) -> SimpleSpec:
        """Resolve a simple type by name."""
        type_name = self._strip_ns(type_qname)
        if type_name in BUILTIN_MAP:
            return SimpleSpec(base=self._xsd_builtin_to_python(type_name))
        if type_name in self.simple_types:
            return self.simple_types[type_name]
        return SimpleSpec(base="string")

    # -------------------------------------------------------------------------
    # ComplexType parsing
    # -------------------------------------------------------------------------

    def _parse_complex_type(self, node: ET.Element) -> ComplexSpec:
        """Parse xs:complexType and return ComplexSpec."""
        mixed = node.get("mixed") == "true"
        attrs: list[AttrSpec] = []
        children_seq: list[ChildSpec | list[ChildSpec]] = []
        simple_content: SimpleSpec | None = None

        # Collect attributes
        attrs.extend(self._parse_attributes(node))

        # Check for simpleContent
        sc = node.find("xs:simpleContent", NS)
        if sc is not None:
            ext = sc.find("xs:extension", NS) or sc.find("xs:restriction", NS)
            if ext is not None:
                base = ext.get("base")
                if base:
                    simple_content = self._resolve_simple(base)
                attrs.extend(self._parse_attributes(ext))
            return ComplexSpec(
                children_seq=[], attrs=attrs, simple_content=simple_content, mixed=mixed
            )

        # Check for complexContent
        cc = node.find("xs:complexContent", NS)
        if cc is not None:
            ext = cc.find("xs:extension", NS) or cc.find("xs:restriction", NS)
            if ext is not None:
                base = ext.get("base")
                base_spec = self._resolve_complex(base) if base else None
                if base_spec:
                    children_seq.extend(base_spec.children_seq)
                    attrs = base_spec.attrs + attrs
                children_seq.extend(self._parse_model_group(ext))
                attrs.extend(self._parse_attributes(ext))
            return ComplexSpec(
                children_seq=children_seq, attrs=attrs, simple_content=None, mixed=mixed
            )

        # Normal model group
        children_seq.extend(self._parse_model_group(node))

        return ComplexSpec(
            children_seq=children_seq, attrs=attrs, simple_content=None, mixed=mixed
        )

    def _resolve_complex(self, type_qname: str | None) -> ComplexSpec | None:
        """Resolve a complex type by name."""
        if not type_qname:
            return None
        type_name = self._strip_ns(type_qname)
        return self.complex_types.get(type_name)

    def _parse_attributes(self, node: ET.Element) -> list[AttrSpec]:
        """Parse xs:attribute elements."""
        out: list[AttrSpec] = []
        for attr in node.findall("xs:attribute", NS):
            name = attr.get("name") or attr.get("ref")
            if not name:
                continue
            name = self._strip_ns(name)
            use = attr.get("use", "optional")
            type_ref = attr.get("type")
            spec: SimpleSpec | None = None

            # Check for inline simpleType
            inline_st = attr.find("xs:simpleType", NS)
            if inline_st is not None:
                spec = self._parse_simple_type(inline_st)
            elif type_ref:
                spec = self._resolve_simple(type_ref)

            out.append(AttrSpec(name=name, use=use, type_spec=spec))
        return out

    def _parse_model_group(self, node: ET.Element) -> list[ChildSpec | list[ChildSpec]]:
        """Parse model group (sequence/choice/all) under a node."""
        for group_tag in ("sequence", "choice", "all"):
            group = node.find(f"xs:{group_tag}", NS)
            if group is not None:
                return self._parse_group(group, mode=group_tag)
        return []

    def _parse_group(
        self, group: ET.Element, mode: str
    ) -> list[ChildSpec | list[ChildSpec]]:
        """Parse a specific model group."""
        steps: list[ChildSpec | list[ChildSpec]] = []

        if mode == "sequence":
            for item in list(group):
                steps.extend(self._parse_particle(item))
            return steps

        if mode == "all":
            # 'all' means order-insensitive; represent as single group
            alts: list[ChildSpec] = []
            for item in list(group):
                parsed = self._parse_element_particle(item)
                if parsed:
                    alts.append(parsed)
            if alts:
                steps.append(alts)
            return steps

        if mode == "choice":
            # Choice is a single position with alternatives
            min_o, max_o = self._occurs(group)
            alts = []
            for item in list(group):
                child = self._parse_element_particle(item)
                if child:
                    # Distribute occurrence to each alternative
                    child = ChildSpec(
                        name=child.name,
                        min_occurs=child.min_occurs * min_o,
                        max_occurs=self._mul_max(child.max_occurs, max_o),
                    )
                    alts.append(child)
            if alts:
                steps.append(alts)
            return steps

        return steps

    def _parse_particle(self, node: ET.Element) -> list[ChildSpec | list[ChildSpec]]:
        """Parse a particle (element, sequence, choice, all)."""
        tag = self._strip_ns(node.tag)
        if tag == "element":
            child = self._parse_element_particle(node)
            return [child] if child else []
        if tag in ("sequence", "choice", "all"):
            return self._parse_group(node, mode=tag)
        return []

    def _parse_element_particle(self, el: ET.Element) -> ChildSpec | None:
        """Parse an xs:element particle."""
        tag = self._strip_ns(el.tag)
        if tag != "element":
            return None

        name = el.get("name") or el.get("ref")
        if not name:
            return None
        name = self._strip_ns(name)
        min_o, max_o = self._occurs(el)
        return ChildSpec(name=name, min_occurs=min_o, max_occurs=max_o)

    # -------------------------------------------------------------------------
    # Schema generation
    # -------------------------------------------------------------------------

    def build_bag_schema(self, root_elements: list[str] | None = None) -> Bag:
        """Build Bag schema from parsed XSD.

        Args:
            root_elements: Optional list of element names to include.
                          If None, includes all global elements.

        Returns:
            Schema Bag ready for serialization
        """
        schema = Bag(builder=SchemaBuilder)

        if root_elements is None:
            root_elements = sorted(self.global_elements.keys())

        for el_name in root_elements:
            self._emit_element_schema(schema, el_name)

        return schema

    def _emit_element_schema(self, schema: Bag, el_name: str) -> None:
        """Emit schema item for an element."""
        if schema.get_node(el_name) is not None:
            return

        node = self.global_elements.get(el_name)
        if node is None:
            # Referenced but not global: create empty stub
            schema.item(el_name, sub_tags="")
            return

        # Determine element type
        type_ref = node.get("type")
        inline_ct = node.find("xs:complexType", NS)
        inline_st = node.find("xs:simpleType", NS)

        children_steps: list[ChildSpec | list[ChildSpec]] = []
        attrs: list[AttrSpec] = []
        value_spec: SimpleSpec | None = None

        if type_ref:
            ct = self._resolve_complex(type_ref)
            if ct:
                children_steps = ct.children_seq
                attrs = ct.attrs
                value_spec = ct.simple_content
            else:
                value_spec = self._resolve_simple(type_ref)

        if inline_ct is not None:
            ct = self._parse_complex_type(inline_ct)
            children_steps = ct.children_seq
            attrs = ct.attrs
            value_spec = ct.simple_content

        if inline_st is not None:
            value_spec = self._parse_simple_type(inline_st)

        # Build sub_tags
        sub_tags = self._render_children(children_steps)

        # Build validations
        call_args_validations: dict[str, Any] = {}
        if value_spec:
            call_args_validations["value"] = self._render_simple_spec(value_spec)
        for attr in attrs:
            attr_validation = self._render_attr_spec(attr)
            if attr_validation:
                call_args_validations[attr.name] = attr_validation

        # Build output attributes
        attrs_out: dict[str, Any] = {"sub_tags": sub_tags}
        if call_args_validations:
            attrs_out["call_args_validations"] = call_args_validations

        schema.item(el_name, **attrs_out)

        # Ensure children exist
        for child_name in self._collect_child_names(children_steps):
            if schema.get_node(child_name) is None:
                if child_name in self.global_elements:
                    self._emit_element_schema(schema, child_name)
                else:
                    schema.item(child_name, sub_tags="")

    def _collect_child_names(
        self, steps: list[ChildSpec | list[ChildSpec]]
    ) -> set[str]:
        """Collect all child names from steps."""
        out: set[str] = set()
        for step in steps:
            if isinstance(step, list):
                for child in step:
                    out.add(child.name)
            else:
                out.add(step.name)
        return out

    def _render_children(
        self, steps: list[ChildSpec | list[ChildSpec]]
    ) -> str:
        """Render children to sub_tags string."""
        if not steps:
            return ""

        merged: dict[str, tuple[int, int | None]] = {}

        for step in steps:
            if isinstance(step, list):
                # Choice or 'all' group
                for child in step:
                    merged[child.name] = self._merge_occ(
                        merged.get(child.name), (child.min_occurs, child.max_occurs)
                    )
            else:
                merged[step.name] = self._merge_occ(
                    merged.get(step.name), (step.min_occurs, step.max_occurs)
                )

        # Build sub_tags with cardinality
        sub_tags_parts = []
        for name in sorted(merged.keys()):
            min_o, max_o = merged[name]
            card = self._fmt_card(min_o, max_o)
            sub_tags_parts.append(f"{name}{card}")

        return ",".join(sub_tags_parts)

    def _render_simple_spec(self, spec: SimpleSpec) -> dict[str, Any]:
        """Render SimpleSpec to validation dict."""
        out: dict[str, Any] = {"type": spec.base}
        if spec.pattern:
            out["pattern"] = spec.pattern
        if spec.values:
            out["values"] = list(spec.values)
        if spec.min_length is not None:
            out["minLength"] = spec.min_length
        if spec.max_length is not None:
            out["maxLength"] = spec.max_length
        if spec.min_inclusive is not None:
            out["min"] = spec.min_inclusive
        if spec.max_inclusive is not None:
            out["max"] = spec.max_inclusive
        if spec.total_digits is not None:
            out["totalDigits"] = spec.total_digits
        if spec.fraction_digits is not None:
            out["fractionDigits"] = spec.fraction_digits
        return out

    def _render_attr_spec(self, attr: AttrSpec) -> dict[str, Any]:
        """Render AttrSpec to validation dict."""
        out: dict[str, Any] = {"use": attr.use}
        if attr.type_spec:
            out.update(self._render_simple_spec(attr.type_spec))
        return out


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """Command-line interface for XSD schema builder."""
    parser = argparse.ArgumentParser(
        description="Convert XSD schemas to BagBuilder schema format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Input XSD file path",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL to download XSD from",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output schema file (.bag.mp)",
    )
    parser.add_argument(
        "--roots",
        type=str,
        help="Comma-separated list of root elements to include (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON file for inspection",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print diagnostic info",
    )

    args = parser.parse_args()

    if not args.input and not args.url:
        parser.error("Either input file or --url is required")

    # Determine source
    if args.url:
        source = args.url
        print(f"Downloading from {args.url}...")
    else:
        source = args.input
        if not args.input.exists():
            print(f"ERROR: Input file not found: {args.input}")
            return

    # Parse root elements
    root_elements = None
    if args.roots:
        root_elements = [r.strip() for r in args.roots.split(",")]

    # Build schema
    print(f"Building schema from {source}...")
    builder = XsdSchemaBuilder(source)

    if args.verbose:
        print(f"  Found {len(builder.global_elements)} global elements")
        print(f"  Found {len(builder.simple_types)} simple types")
        print(f"  Found {len(builder.complex_types)} complex types")

    schema = builder.build_bag_schema(root_elements)

    # Count elements
    n_elements = len(schema)
    print(f"  Generated {n_elements} schema items")

    # Save output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    schema.builder.compile(args.output)
    print(f"Saved schema to {args.output}")

    # Optional JSON output
    if args.json:
        import json

        json_path = args.output.with_suffix(".json")
        json_content = schema.to_json()
        # Pretty print the JSON
        parsed = json.loads(json_content)
        json_path.write_text(json.dumps(parsed, indent=2))
        print(f"Saved JSON to {json_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
