# GenroPy Wrapper — Analysis and Development Work

This directory contains the analysis, benchmarks, and prototype code
produced during the development of `genro-bag` as a replacement for
the original `gnr.core.gnrbag` module in GenroPy.

## Contents

- **docs/** — Analysis documents and API comparison with the legacy Bag
- **replacement/** — Drop-in wrapper module (`gnrbag.py`) providing backward
  compatibility with the original GenroPy Bag API
- **tests/** — Test suite covering all phases of the analysis
  (access, query, serialization, events, resolvers, integration)
- **benchmarks/** — Profiling scripts for `get_item` and general Bag operations
