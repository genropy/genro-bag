# tests/spec — Spec-driven test suite

This is the test suite of genro-bag. It replaced the earlier monolithic one
(`test_bag.py` plus `test_coverage_extension.py`), and `testpaths` in
pyproject.toml points here alone.

## Principles

Four principles, and they are where the name "spec" comes from:

1. **From the docstrings, not from the code.** Every test starts from the public
   documentation of a `Bag` method (docstring, README, manual). You do not write
   a test to "cover an if branch" — you write one to document a documented way
   of using the thing.

2. **End-to-end, not internal primitives.** A test builds a `Bag`, exercises a
   public operation, and checks the observable behaviour. No reaching into
   `_nodes`, `_htraverse`, `_node_to_xml` or anything else underscored.

3. **One module, one domain.** `test_basic.py` covers base operations with no
   resolvers and no subscriptions. `test_query.py` covers query/walk/aggregation
   only. Domains do not mix within a file.

4. **What has no life of its own is not tested on its own.** `BagNode`,
   `BagNodeContainer` and `BagResolver` are internal structures. A user meets
   them only as a consequence of operating on a `Bag`, so that is how the tests
   reach them — never in isolation.

## Public API

Working definition: **anything not starting with `_`**.

- `set_item` is public.
- `_htraverse` is not.

The dunders (`__init__`, `__getitem__`, `__setitem__`, `__delitem__`,
`__contains__`, `__len__`, `__iter__`, `__eq__`, `__ne__`, `__str__`,
`__repr__`, `__call__`) are part of the API.

## Language

Code, comments and docstrings are in English. Much of this suite was written in
Italian and has since been translated; anything new goes in English from the
start.

## No external dependencies

Tests needing a real HTTP request use the `http_server` fixture in
`conftest.py`, a stdlib `http.server` on 127.0.0.1. No public endpoint, no extra
test library: a service we do not control must never be able to fail the suite,
and an undeclared dependency can silently disable a whole file — both of which
happened before the fixture existed.

## Process

1. Start from the most foundational methods (`set_item`, `get_item`, `[...]`).
2. Write one test per documented way of using it.
3. Measure coverage:

   ```bash
   pytest tests/spec/ --cov=genro_bag --cov-report=term-missing --cov-report=html:htmlcov-spec
   ```

4. Open `htmlcov-spec/index.html`, see which branches are still uncovered,
   decide the next test.
5. The coverage report is the to-do list: no extra test without checking it
   adds real coverage.

## What this suite does NOT contain

- Tests on `BagNode`, `BagNodeContainer` or `BagResolver` instantiated directly.
- Tests reaching underscored attributes or methods.
- Filler tests whose only purpose is to move a metric.
- Domain duplication — a feature lives in one file.
