
# RHB Specification — 02 Path Syntax

Supported segments:
- label: aaa.bbb.ccc
- index: #N (0-based)
- parent: /parent
- attribute: ?attr

Rules:
- getitem never raises
- setItem requires final segment = label
