# Design Specifications

This directory contains the **source of truth** for the genro-bag project design.

Each subdirectory represents a specific topic area, numbered for logical ordering.

## Structure

```
design_specifications/
├── README.md                 # This file
├── 01-overview/              # Project overview and architecture
├── 02-array_dict/            # Array and dictionary behaviors
└── ...                       # Additional topics as needed
```

## Guidelines

1. **Source of Truth**: Documents here define the expected behavior
2. **Numbered Ordering**: Topics are prefixed with numbers for logical sequence
3. **One Topic Per Directory**: Each directory covers a single coherent topic
4. **Markdown Format**: All specifications should be in Markdown
5. **Test Alignment**: Tests should verify behavior described here

## Adding New Topics

To add a new topic:
1. Create a new directory with the next available number prefix
2. Use lowercase with hyphens for the topic name (e.g., `03-xml_serialization`)
3. Add a README.md in the directory explaining the topic
4. Add detailed specification files as needed
