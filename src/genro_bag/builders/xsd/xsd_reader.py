# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD reader - Iterator over XSD elements for schema generation.

Parses XSD (XML Schema Definition) files and yields element definitions
with their children and validation constraints.

Used by XsdBuilder to generate BagBuilder schemas.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree as ET

from genro_bag.builder import Range, Regex

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
# Model dataclasses
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
    type_qname: str | None = None
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
# XsdReader
# =============================================================================


class XsdReader:
    """Read XSD and iterate over element definitions.

    Yields tuples of (element_name, sub_tags, call_args_validations) for each
    element in the schema, including both global elements and local elements
    defined within complex types.

    Usage:
        reader = XsdReader.from_file('schema.xsd')
        for name, sub_tags, validations in reader.iter_elements():
            schema.item(name, sub_tags=sub_tags, call_args_validations=validations)
    """

    def __init__(self, xsd_xml: str):
        """Initialize reader from XSD XML string.

        Args:
            xsd_xml: XSD content as string.
        """
        self.tree = ET.ElementTree(ET.fromstring(xsd_xml))
        self.root = self.tree.getroot()

        self.simple_types: dict[str, SimpleSpec] = {}
        self.complex_types: dict[str, ComplexSpec] = {}
        self.global_elements: dict[str, ET.Element] = {}

        self._index_schema()

    @classmethod
    def from_file(cls, path: str | Path) -> XsdReader:
        """Create reader from XSD file path."""
        return cls(Path(path).read_text())

    @classmethod
    def from_url(cls, url: str) -> XsdReader:
        """Create reader from URL."""
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "xsd-reader"})
        with urllib.request.urlopen(req) as response:
            data = response.read().decode("utf-8")
        return cls(data)

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _q(self, tag: str) -> str:
        """Return fully qualified tag name."""
        return f"{{{XSD_NS}}}{tag}"

    def _strip_ns(self, name: str | None) -> str:
        """Strip namespace prefix from name."""
        if not name:
            return ""
        if "}" in name:
            return name.split("}", 1)[1]
        if ":" in name:
            return name.split(":", 1)[1]
        return name

    def _xsd_builtin_to_python(self, xsd_type: str) -> str:
        """Convert XSD builtin type to Python type name."""
        return BUILTIN_MAP.get(xsd_type, "string")

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
        if min_o == 1 and max_o == 1:
            return ""
        if max_o is None:
            return f"[{min_o}:*]"
        return f"[{min_o}:{max_o}]"

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
    # Schema indexing
    # -------------------------------------------------------------------------

    def _index_schema(self) -> None:
        """Index all global types and elements."""
        for child in self.root:  # type: ignore[union-attr]
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
        return self.simple_types.get(type_name, SimpleSpec(base="string"))

    # -------------------------------------------------------------------------
    # ComplexType parsing
    # -------------------------------------------------------------------------

    def _resolve_complex(self, type_qname: str | None) -> ComplexSpec | None:
        """Resolve a complex type by name."""
        if not type_qname:
            return None
        return self.complex_types.get(self._strip_ns(type_qname))

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

            inline_st = attr.find("xs:simpleType", NS)
            if inline_st is not None:
                spec = self._parse_simple_type(inline_st)
            elif type_ref:
                spec = self._resolve_simple(type_ref)

            out.append(AttrSpec(name=name, use=use, type_spec=spec))
        return out

    def _parse_complex_type(self, node: ET.Element) -> ComplexSpec:
        """Parse xs:complexType and return ComplexSpec."""
        mixed = node.get("mixed") == "true"
        attrs = self._parse_attributes(node)

        sc = node.find("xs:simpleContent", NS)
        if sc is not None:
            ext = sc.find("xs:extension", NS)
            if ext is None:
                ext = sc.find("xs:restriction", NS)
            if ext is not None:
                base = ext.get("base")
                simple_content = self._resolve_simple(base) if base else None
                attrs = attrs + self._parse_attributes(ext)
                return ComplexSpec(
                    children_seq=[], attrs=attrs, simple_content=simple_content, mixed=mixed
                )
            return ComplexSpec(children_seq=[], attrs=attrs, simple_content=None, mixed=mixed)

        children_seq = self._parse_model_group(node)
        return ComplexSpec(children_seq=children_seq, attrs=attrs, simple_content=None, mixed=mixed)

    def _parse_model_group(self, node: ET.Element) -> list[ChildSpec | list[ChildSpec]]:
        """Parse model group (sequence/choice/all) under a node."""
        for group_tag in ("sequence", "choice", "all"):
            group = node.find(f"xs:{group_tag}", NS)
            if group is not None:
                return self._parse_group(group, mode=group_tag)
        return []

    def _parse_group(self, group: ET.Element, mode: str) -> list[ChildSpec | list[ChildSpec]]:
        """Parse a specific model group."""
        steps: list[ChildSpec | list[ChildSpec]] = []

        if mode == "sequence":
            for item in list(group):
                steps.extend(self._parse_particle(item))
            return steps

        if mode == "all":
            alts: list[ChildSpec] = []
            for item in list(group):
                parsed = self._parse_element_particle(item)
                if parsed:
                    alts.append(parsed)
            if alts:
                steps.append(alts)
            return steps

        if mode == "choice":
            min_o, max_o = self._occurs(group)
            choice_alts: list[ChildSpec] = []
            for item in list(group):
                child = self._parse_element_particle(item)
                if child:
                    child = ChildSpec(
                        name=child.name,
                        type_qname=child.type_qname,
                        min_occurs=child.min_occurs * min_o,
                        max_occurs=self._mul_max(child.max_occurs, max_o),
                    )
                    choice_alts.append(child)
            if choice_alts:
                steps.append(choice_alts)
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
        if self._strip_ns(el.tag) != "element":
            return None
        name = el.get("name") or el.get("ref")
        if not name:
            return None
        name = self._strip_ns(name)
        min_o, max_o = self._occurs(el)
        type_qname = el.get("type")
        return ChildSpec(name=name, type_qname=type_qname, min_occurs=min_o, max_occurs=max_o)

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def _render_children(self, steps: list[ChildSpec | list[ChildSpec]]) -> str:
        """Render children to sub_tags string."""
        if not steps:
            return ""

        merged: dict[str, tuple[int, int | None]] = {}
        for step in steps:
            if isinstance(step, list):
                for child in step:
                    merged[child.name] = self._merge_occ(
                        merged.get(child.name), (child.min_occurs, child.max_occurs)
                    )
            else:
                merged[step.name] = self._merge_occ(
                    merged.get(step.name), (step.min_occurs, step.max_occurs)
                )

        parts = []
        for name in sorted(merged.keys()):
            min_o, max_o = merged[name]
            parts.append(f"{name}{self._fmt_card(min_o, max_o)}")
        return ",".join(parts)

    def _render_simple_spec(
        self, spec: SimpleSpec, required: bool = False
    ) -> tuple[Any, list, Any]:
        """Render SimpleSpec to validation tuple (type, validators, default)."""
        type_map = {"string": str, "int": int, "decimal": Decimal, "bool": bool}

        base_type = (
            Literal[tuple(spec.values)]  # type: ignore[valid-type]
            if spec.values
            else type_map.get(spec.base, str)
        )

        validators: list = []
        if spec.pattern:
            validators.append(Regex(spec.pattern))
        if spec.min_inclusive is not None or spec.max_inclusive is not None:
            validators.append(
                Range(
                    ge=float(spec.min_inclusive) if spec.min_inclusive is not None else None,
                    le=float(spec.max_inclusive) if spec.max_inclusive is not None else None,
                )
            )

        default = inspect.Parameter.empty if required else None
        return (base_type, validators, default)

    def _call_args_validations_from_complex(self, ct: ComplexSpec) -> dict[str, Any]:
        """Build call_args_validations from ComplexSpec."""
        out: dict[str, Any] = {}
        if ct.simple_content:
            out["node_value"] = self._render_simple_spec(ct.simple_content, required=False)
        for a in ct.attrs:
            if a.type_spec:
                out[a.name] = self._render_simple_spec(a.type_spec, required=(a.use == "required"))
        return out

    # -------------------------------------------------------------------------
    # Public iterator
    # -------------------------------------------------------------------------

    def iter_elements(self) -> Iterator[tuple[str, str, dict[str, Any]]]:
        """Iterate over all elements in the schema.

        Yields:
            Tuples of (element_name, sub_tags, call_args_validations).
            Includes both global elements and local elements from complex types.
        """
        yielded: set[str] = set()

        # 1) Global elements
        for el_name, el_node in self.global_elements.items():
            yield from self._yield_element(el_name, el_node.get("type"))
            yielded.add(el_name)

        # 2) Local elements from complex types
        for ct in self.complex_types.values():
            for step in ct.children_seq:
                if isinstance(step, list):
                    for ch in step:
                        if ch.name not in yielded:
                            yield from self._yield_element(ch.name, ch.type_qname)
                            yielded.add(ch.name)
                else:
                    if step.name not in yielded:
                        yield from self._yield_element(step.name, step.type_qname)
                        yielded.add(step.name)

    def _yield_element(
        self, el_name: str, type_qname: str | None
    ) -> Iterator[tuple[str, str, dict[str, Any]]]:
        """Yield element definition."""
        if not type_qname:
            yield (el_name, "", {})
            return

        tname = self._strip_ns(type_qname)

        # Simple type
        if tname in self.simple_types or tname in BUILTIN_MAP:
            spec = self._resolve_simple(type_qname)
            cav = {"node_value": self._render_simple_spec(spec, required=False)}
            yield (el_name, "", cav)
            return

        # Complex type
        ct = self.complex_types.get(tname)
        if not ct:
            yield (el_name, "", {})
            return

        sub_tags = self._render_children(ct.children_seq)
        cav = self._call_args_validations_from_complex(ct)
        yield (el_name, sub_tags, cav)
