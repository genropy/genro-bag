# Claude Code Instructions - genro-bag

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Pre-Alpha
- Has Implementation: No (only structure)

### Project Description
Modernized bag system for the Genropy framework - hierarchical data container with XML serialization.

---

## Special Commands

### "mostra righe" / "mostra le righe" / "rimetti qui le righe" (show lines)

When the user asks to show code lines:

1. Show **only** the requested code snippet with some context lines
2. Number the lines
3. **DO NOT** add considerations, evaluations, or explanations
4. Copy the code directly into the chat

---

## Exceptions to Parent Rules

### @classmethod allowed for alternative constructors

The parent CLAUDE.md forbids `@classmethod`. In genro-bag, `@classmethod` is allowed
exclusively for **alternative constructors** (factory methods that create instances):

- `Bag.from_xml()`, `Bag.from_json()`, `Bag.from_tytx()`, `Bag.from_url()`
- `BagResolver.deserialize()`
- Internal helpers of the above (e.g. `_from_json_recursive`)

These use `cls()` for polymorphic instance creation and follow the standard Python
alternative constructor pattern. No other use of `@classmethod` is permitted.

### @staticmethod allowed for pure helpers in serialization

`_sanitize_tag` and `_extract_namespaces` in `_serialize.py` are `@staticmethod`
because they are pure functions used by both the core and the wrapper (via inheritance).

---

**All general policies are inherited from the parent document.**
