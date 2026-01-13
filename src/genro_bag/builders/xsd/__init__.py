# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""XSD (XML Schema Definition) builders for Bag.

This module provides:
- XsdBuilder: Dynamic builder that parses XSD at runtime
- XsdSchemaBuilder: Tool for pre-compiling XSD to schema files

Example (runtime parsing):
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.xsd import XsdBuilder
    >>>
    >>> bag = Bag(builder=XsdBuilder, builder_xsd_source='pain.001.001.12.xsd')
    >>> doc = bag.Document()

Example (pre-compiled schema):
    >>> from genro_bag.builders.xsd import XsdSchemaBuilder
    >>>
    >>> # Generate schema file from XSD
    >>> XsdSchemaBuilder.compile('pain.001.001.12.xsd', 'pain_schema.mp')
"""

from .xsd_builder import XsdBuilder
from .xsd_schema_builder import XsdSchemaBuilder

__all__ = ["XsdBuilder", "XsdSchemaBuilder"]
