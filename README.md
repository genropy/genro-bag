# genro-bag

[![PyPI version](https://img.shields.io/pypi/v/genro-bag)](https://pypi.org/project/genro-bag/)
[![Tests](https://github.com/genropy/genro-bag/actions/workflows/tests.yml/badge.svg)](https://github.com/genropy/genro-bag/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/genropy/genro-bag/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-bag)
[![Documentation](https://readthedocs.org/projects/genro-bag/badge/?version=latest)](https://genro-bag.readthedocs.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Introduction

Most software systems deal with structured things.

Web pages, configuration files, APIs, database schemas, cloud infrastructures, documents: we usually treat these as separate worlds, each with its own language, tools, and conventions.

Yet they all share something very simple: **they are organized hierarchically**, and humans reason about them by location rather than by mechanism.

We say "the third book on the first shelf in the bedroom", not "object #42".

This project starts from that observation.

## A hierarchy as a first-class concept

A Bag is, at its core, a **hierarchical dictionary**: a tree of named nodes.

This may sound trivial, but it is a deliberate choice. Instead of translating hierarchical thinking into tables, messages, callbacks, or ad-hoc APIs, the hierarchy is kept explicit and central.

Even without any additional feature, this already provides value:

- related things live together
- names are stable
- navigation is uniform
- structure is visible

Nothing clever is required to get started.

## When values are not just values

In real systems, not everything can be stored.

Some values must be *obtained*: by calling a service, reading hardware, querying a database, or computing something on demand.

In a Bag, this does not require a different mental model.

You still navigate to a place in the hierarchy. The only difference is that some places know how to **obtain** a value instead of containing one.

From the outside, access looks the same. You don't switch from "data mode" to "API mode".

You navigate first. Resolution happens later.

## Reacting to meaning, not plumbing

Change is inevitable in any non-trivial system.

Usually, change is handled through events, callbacks, queues, or polling loops. These mechanisms tend to leak into application code and force developers to think about infrastructure details.

A Bag takes a different approach.

Instead of subscribing to events, you express interest in a **place** in the hierarchy: you care about *what* changed, not *how* the change was transported.

This keeps reactivity tied to meaning rather than to implementation details.

## Writing structure the same way you read it

The same hierarchy that can be navigated and observed can also be built.

**Builders** allow structures to be written fluently, in a way that mirrors how they are described mentally: containers contain tables, tables contain headers, and so on.

This is not about inventing a new language. It is about making construction consistent with navigation.

Builders can also enforce rules about what is allowed or required, so structures are **valid as they are built**, not validated afterwards.

## One way of thinking, many domains

Once this model is in place, something interesting happens.

The same way of reasoning can be applied to:

- web pages
- XML documents
- API descriptions
- database structures
- cloud architectures
- shared real-time state

The structure stays the same. Only the vocabulary changes.

Developers do not have to relearn how to think for each domain — only what names and constraints apply.

## A structural IR, not a framework

This project is best understood as a **structural intermediate representation**.

It sits between how humans reason about structured systems and how specific technologies require them to be expressed.

It does not replace HTML, Terraform, APIs, or databases. It can compile into them, connect them, or synchronize them — and then disappear.

Nothing depends on it at runtime unless you choose so.

That is why it is more accurate to see this as a **mental model made concrete**, rather than as a framework to adopt wholesale.

## Why this exists

Over time, we noticed that much of the accidental complexity in software comes from constantly translating the same hierarchical ideas into different forms.

This project exists to stop doing that.

Not by simplifying domains, but by **unifying how they are described**.

## Install

```bash
pip install genro-bag
```

## Documentation

Full documentation: [genro-bag.readthedocs.io](https://genro-bag.readthedocs.io/)

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

Copyright 2025 Softwell S.r.l. - Genropy Team
