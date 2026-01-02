
# Genro-HLRS and D-HLRS — Hierarchical Lazy Reactive Store

Genro-HLRS is the modern evolution of Giovanni Porcari’s historic **Bag** concept 
(1990s, Smalltalk roots). It defines a **Hierarchical**, **Lazy**, **Reactive** Store:

- **Hierarchical**: a tree of `Bag` and `BagNode` objects, with strict parent/child backrefs.
- **Lazy**: node values can be computed on demand by a **Resolver** (sync/async, cached).
- **Reactive**: structural and value changes emit **Triggers** that propagate up the tree.

On a single process, this model is called **Genro-HLRS**.

When the same semantics are extended across multiple processes and machines, with 
transparent addressing and event routing, we refer to the system as **D‑HLRS**:

> **D‑HLRS = Distributed Hierarchical Lazy Reactive Store**
