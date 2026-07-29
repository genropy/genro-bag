# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Wire encoding for BagResolvers, shared by the serializers and the parsers.

A resolver travels as a marked string, ``::RSLV:<payload>``, which every
format can carry: an XML attribute, a JSON string, a TYTX value. Formats
with real structure (JSON node dicts) keep using it too, so there is one
encoding to reason about rather than four.

Signing
    Pass a ``key`` and the payload is HMAC-signed with an optional expiry.
    Required whenever the Bag leaves the process and may come back — a
    resolver handed to a browser is under the client's control, and its
    arguments (a path, a URL) are what the resolver will act on. Without a
    signature there is nothing to stop those from being rewritten.
    Reading is symmetric: a key means signatures are demanded, no key means
    payloads are taken as they come.

Trust
    Decoding never calls the resolver — it is rebuilt inert, and any I/O
    happens later, when the caller reads the value. Class instantiation is
    guarded by ``BagResolver.deserialize``, which refuses anything outside
    the BagResolver hierarchy.
"""

from __future__ import annotations

import json
from typing import Any

from genro_toolbox import safe_is_instance, sign, verify

from genro_bag.bag._exceptions import BagSerializationError
from genro_bag.resolver import BagResolver

RESOLVER_MARKER = "::RSLV:"

_IS_RESOLVER = "genro_bag.resolver.BagResolver"


def is_resolver(value: Any) -> bool:
    """True if value is a BagResolver, without importing it eagerly."""
    return safe_is_instance(value, _IS_RESOLVER)


def encode_resolver(
    resolver: BagResolver,
    key: str | None = None,
    expires_in: int | None = None,
    where: str = "",
) -> str:
    """Encode a resolver as a ``::RSLV:`` marked string.

    Args:
        resolver: The resolver to encode.
        key: Secret key. When given, the payload is signed.
        expires_in: Lifetime in seconds for the signature.
        where: Location used in error messages, e.g. "node 'a.b' attribute 'x'".

    Returns:
        The marked string.

    Raises:
        BagSerializationError: If the resolver holds values that cannot be
            written as JSON — a callback, or any non-JSON object among its
            parameters.
    """
    try:
        payload = json.dumps(resolver.serialize())
    except (TypeError, ValueError) as err:
        raise BagSerializationError(
            f"{where or type(resolver).__name__} holds a "
            f"{type(resolver).__name__} that cannot be serialized: {err}. "
            f"Callback-based resolvers and non-JSON parameters cannot travel."
        ) from err
    if key:
        payload = sign(payload, key=key, expires_in=expires_in)
    return f"{RESOLVER_MARKER}{payload}"


def decode_resolver(value: Any, key: str | None = None) -> BagResolver | None:
    """Rebuild a resolver from a marked string, inert.

    Args:
        value: The candidate value. Anything unmarked returns None.
        key: Secret key. When given, a valid signature is required.

    Returns:
        The rebuilt resolver, or None if the value carries no marker.

    Raises:
        SignatureError: Signature missing, forged or expired (SignatureExpired
            for the expiry case) when a key was given.
        ValueError: If the payload names a class outside the BagResolver
            hierarchy.
    """
    if not isinstance(value, str) or not value.startswith(RESOLVER_MARKER):
        return None
    payload = value[len(RESOLVER_MARKER) :]
    if key:
        payload = verify(payload, key=key)
    return BagResolver.deserialize(json.loads(payload))


def encode_attrs(
    attr: dict | None,
    key: str | None = None,
    expires_in: int | None = None,
    where: str = "",
) -> dict:
    """Return a copy of attr with every BagResolver encoded.

    Attributes that hold no resolver are copied untouched.
    """
    if not attr:
        return {}
    return {
        k: encode_resolver(v, key, expires_in, f"{where} attribute {k!r}".strip())
        if is_resolver(v)
        else v
        for k, v in attr.items()
    }


def decode_attrs(attr: dict | None, key: str | None = None) -> dict:
    """Return a copy of attr with every marked string rebuilt as a resolver."""
    if not attr:
        return {}
    return {k: (decode_resolver(v, key) or v) for k, v in attr.items()}
