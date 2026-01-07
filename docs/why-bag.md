# Why Bag?

Most software systems deal with structured things: web pages, configuration files, APIs, database schemas. We usually treat these as separate worlds, each with its own language and tools.

Yet they all share something very simple: **they are organized hierarchically**, and humans reason about them by location rather than by mechanism.

## The typical toolbox problem

A typical Python project dealing with hierarchical data ends up using:

- `omegaconf` or `hydra` for hierarchical configuration
- `pydantic` for validation and nested models
- `munch`/`addict` or `dotmap` for dot notation access
- `rxpy` or `reactivex` for reactivity
- `lxml` or `xmltodict` for XML handling
- `jsonpointer` or manual dict walking for path resolution
- Custom decorators for lazy loading from DB or API
- Plenty of glue code (wrappers, adapters, utility functions) to make these tools talk to each other

The result:

- 10+ dependencies in `requirements.txt`
- 5-6 different styles to access the same data (`.`, `[]`, `/`, `get()` with defaults, etc.)
- Time spent chasing incompatible updates
- Fragmented code, hard to reason about and explain to newcomers
- Low real productivity, despite the impression of "using the most modern stack"

## One model, one way of thinking

Bag proposes a different approach: **one structure, one mental model, one access point**.

With Bag you get, in the same object:

| Need | Typical solution(s) | With Bag |
|------|---------------------|----------|
| Hierarchical data | dict + manual nesting | Native path-based access |
| Dot notation | munch/addict | Built-in |
| Configuration | omegaconf, hydra | Bag + builders |
| Structural validation | Custom code | Builders with rules |
| Lazy/computed values | @property, custom decorators | Transparent resolvers (sync/async) |
| Reactivity | rxpy, signals, custom events | Location-based subscriptions |
| XML/JSON handling | lxml, xmltodict, json | Unified serialization |
| Glue code / adapters | Many custom utils | Almost none |

## What about pydantic?

A common question: "Why not just use pydantic?"

Pydantic is excellent for **schema validation**: you define a model with type hints, and pydantic validates and coerces incoming data. It's the right tool when you know the exact shape of your data upfront and want strict type checking.

Bag solves a **different problem**:

| Aspect | Pydantic | Bag |
|--------|----------|-----|
| Primary purpose | Schema validation | Hierarchical data manipulation |
| Schema | Required upfront | Optional (builders) |
| Structure | Fixed at definition | Dynamic, can grow |
| Access pattern | Attribute access on models | Path-based access anywhere |
| Reactivity | None built-in | Subscriptions on any node |
| Lazy loading | Not built-in | Resolvers (sync/async) |
| Serialization | JSON primarily | XML, JSON, MessagePack |
| Type preservation | Yes, via schema | Yes, via TYTX format |

**When to use pydantic**: API request/response validation, configuration with known schema, data transfer objects.

**When to use Bag**: Dynamic hierarchical structures, document manipulation, reactive state, lazy-loaded trees, multi-format serialization.

They can coexist: use pydantic at system boundaries (API input validation), Bag for internal hierarchical state management.

## The real benefit

The developer writes less glue code, always reasons about the same mental model, and spends more time solving the domain problem instead of being a systems integrator.

This is a huge advantage especially in contexts where:

- Data structure is complex and long-lived (configurations, DB schemas, UI trees, business documents)
- There are multiple sources/sinks (frontend, backend, files, APIs, databases)
- The team is heterogeneous or has turnover
- The project must live for years

In practice, it's the "less is more" approach applied to data structures: one well-designed library covering 80-90% of common use cases, instead of 10 specialized libraries covering 100% but with a very high operational cost.

## Summary

*One coherent model. Less glue. More domain logic. Higher velocity.*

```{doctest}
>>> from genro_bag import Bag

>>> # One structure for everything
>>> config = Bag()
>>> config['database.host'] = 'localhost'
>>> config['database.port'] = 5432
>>> config['database.host']
'localhost'

>>> # With metadata
>>> config.set_item('database.pool_size', 10, min=1, max=100)
>>> config['database.pool_size?max']
100

>>> # Reactive
>>> changes = []
>>> config.subscribe('watcher', any=lambda node, evt, **kw: changes.append(evt))
>>> config['database.timeout'] = 30
>>> 'ins' in changes
True
```

See the [Benchmarks](benchmarks.md) for performance characteristics and comparisons with other approaches.
