# Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Wire encoding of Bag subclasses: the ``__cls`` name, shared by to_tytx and from_tytx.

A Bag branch travels as ``"::<suffix>"`` ("::X" for every Bag subclass that
does not register a suffix of its own). Which class of that type it is travels
as a symbolic name, looked up in the TYTX subtype dictionary of the suffix
(``genro_tytx.get_subtype_dict``): name -> class, the real class name.

Where the name goes
    A branch carries it in the attributes of its row; a root (the payload of
    to_tytx, including a Bag held in an attribute or a plain container value)
    carries it at payload level, next to ``rows``.

When it is written
    Only when the class differs from the inherited one. A branch inherits the
    class of its parent Bag when both share the suffix, otherwise the class
    registered for the suffix; a root inherits the class registered for the
    suffix. A tree of plain Bags is therefore unchanged on the wire.

Registration
    Every class that travels this way is in the subtype dictionary, the base
    class included (genro-bag adds ``"Bag"``). Whoever adds a subclass reads the
    dictionary, adds its entry and sets it again. ``__cls`` is reserved: a user
    attribute with that name is an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_tytx import SUFFIX_TO_TYPE, get_subtype_dict

from genro_bag.bag._exceptions import BagSerializationError

if TYPE_CHECKING:
    from genro_bag.bag._core import Bag

CLS_ATTRIBUTE = "__cls"


def get_inherited_class(parent_class: type[Bag] | None, suffix: str) -> Any:
    """Return the class a branch (or, with parent_class None, a root) has without ``__cls``."""
    if parent_class is not None and parent_class.__tytx_suffix__ == suffix:
        return parent_class
    return SUFFIX_TO_TYPE[suffix][0]


def get_subtype_name(cls: type[Bag]) -> str:
    """Return the symbolic name of a Bag class in the subtype dictionary of its suffix."""
    suffix = cls.__tytx_suffix__
    names = [name for name, subtype in get_subtype_dict(suffix).items() if subtype is cls]
    if not names:
        raise BagSerializationError(
            f"{cls.__name__} is not in the TYTX subtype dictionary of {suffix!r}"
        )
    if len(names) > 1:
        raise BagSerializationError(
            f"{cls.__name__} is in the TYTX subtype dictionary of {suffix!r} "
            f"under several names: {sorted(names)}"
        )
    return names[0]


def get_subtype_class(suffix: str, name: str) -> Any:
    """Return the Bag class registered under a symbolic name for a suffix."""
    subtypes = get_subtype_dict(suffix)
    if name not in subtypes:
        raise BagSerializationError(f"Unknown Bag class {name!r} for TYTX type {suffix!r}")
    return subtypes[name]


def get_cls_marker(cls: type[Bag], inherited: type[Bag]) -> str | None:
    """Return the ``__cls`` value to write for cls, or None when it is the inherited class."""
    return None if cls is inherited else get_subtype_name(cls)
