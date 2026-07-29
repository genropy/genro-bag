"""Spec test: i BagResolver sopravvivono alla serializzazione, come valore
del nodo e come attributo, in tutti i formati.

Dipende da test_serialization.py (to_xml/to_json/to_tytx) e
test_resolvers.py (EnvResolver, UuidResolver).

Contratto:
- Un resolver viaggia come stringa marcata ``::RSLV:<payload>``. Come
  valore del nodo: attributo ``_resolver`` in XML, chiave ``"resolver"``
  in JSON, slot valore in TYTX. Come attributo: al posto del valore.
- Il giro completo restituisce un resolver equivalente ma **distinto**:
  stessa classe, stessi parametri, altra istanza.
- ``sign_key`` firma i payload; rileggendo con una chiave si pretende una
  firma valida. Serve quando la Bag esce dal processo e puo' tornare: gli
  argomenti di un resolver dicono su cosa agira'.
- La rilettura e' **inerte**: il resolver viene ricostruito, mai chiamato.
  L'effetto avviene alla prima lettura del valore.
- Un resolver che non sta in JSON (callback) solleva
  ``BagSerializationError`` nominando nodo e attributo.
- ``deepcopy`` ricostruisce i resolver invece di condividerli.

## Scala

### Round-trip, 3 formati x 2 posizioni
1. XML   valore / attributo
2. JSON  valore / attributo
3. TYTX  valore / attributo (anche compact)
4. Bag annidata                        resolver ricorsivo
5. valore + attributo sullo stesso nodo

### Firma
6. giro firmato nei 3 formati          resolver ricostruito
7. chiave diversa al ritorno           SignatureError
8. payload non firmato, chiave attesa  SignatureError
9. firma scaduta                       SignatureExpired
10. payload con il separatore          round-trip integro

### Inerzia
11. serializzare non chiama load()
12. rileggere non chiama load()
13. la prima lettura chiama load()

### Errori
14. resolver callback                  BagSerializationError con nodo e attr

### deepcopy
15. resolver del valore preservato
16. istanze distinte, non condivise
"""

from __future__ import annotations

import json

import pytest
from genro_toolbox import SignatureError, SignatureExpired

from genro_bag import Bag, BagSerializationError
from genro_bag.resolver import BagSyncResolver
from genro_bag.resolvers import BagCbResolver, EnvResolver, UuidResolver

KEY = "server-side-secret"


class CountingResolver(BagSyncResolver):
    """Resolver che conta le proprie esecuzioni, per provare l'inerzia.

    Il contatore vive di classe perche' il round-trip ricostruisce
    l'istanza: contare sull'istanza non direbbe nulla.
    """

    class_kwargs = {"cache_time": 0, "read_only": False, "tag": None}
    calls = 0

    def load(self):
        type(self).calls += 1
        return f"loaded-{self.kw['tag']}"


# =============================================================================
# 1-3. Round-trip nei tre formati
# =============================================================================


class TestRoundTripValueSide:
    """Il resolver del nodo sopravvive al giro."""

    def test_xml(self):
        b = Bag()
        b["root"] = Bag()
        b["root.id"] = UuidResolver("uuid4")
        back = Bag.from_xml(b.to_xml())
        assert isinstance(back.get_resolver("root.id"), UuidResolver)

    def test_json(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_json(b.to_json())
        assert isinstance(back.get_resolver("id"), UuidResolver)

    def test_tytx(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_tytx(b.to_tytx())
        assert isinstance(back.get_resolver("id"), UuidResolver)

    def test_tytx_compact(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_tytx(b.to_tytx(compact=True))
        assert isinstance(back.get_resolver("id"), UuidResolver)

    def test_resolved_value_still_works(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_json(b.to_json())
        assert isinstance(back["id"], str)
        assert len(back["id"]) == 36


class TestRoundTripAttributeSide:
    """Il resolver tenuto in un attributo sopravvive al giro."""

    def test_xml(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b["root"] = Bag()
        b.set_item("root.n", "v", who=EnvResolver("X_SECRET"))
        back = Bag.from_xml(b.to_xml())
        assert back["root.n?who"] == "secret"

    def test_json(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("X_SECRET"))
        back = Bag.from_json(b.to_json())
        assert back["n?who"] == "secret"

    def test_tytx(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("X_SECRET"))
        back = Bag.from_tytx(b.to_tytx())
        assert back["n?who"] == "secret"

    def test_plain_attributes_untouched(self):
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("HOME"), plain="x", num=3)
        back = Bag.from_json(b.to_json())
        assert back["n?plain"] == "x"
        assert back["n?num"] == 3

    def test_no_memory_address_in_xml(self):
        """La vecchia str() scriveva '<... object at 0x...>' nell'attributo."""
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("HOME"))
        assert "object at 0x" not in b.to_xml()


# =============================================================================
# 4-5. Casi composti
# =============================================================================


class TestNestedAndCombined:
    def test_resolver_in_nested_bag(self):
        b = Bag()
        b["a"] = Bag()
        b["a.b"] = Bag()
        b["a.b.id"] = UuidResolver("uuid4")
        back = Bag.from_json(b.to_json())
        assert isinstance(back.get_resolver("a.b.id"), UuidResolver)

    def test_value_and_attribute_on_same_node(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", UuidResolver("uuid4"), who=EnvResolver("X_SECRET"))
        back = Bag.from_json(b.to_json())
        assert isinstance(back.get_resolver("n"), UuidResolver)
        assert back["n?who"] == "secret"

    def test_node_tag_survives(self):
        b = Bag()
        b.set_item("n", UuidResolver("uuid4"), node_tag="item")
        back = Bag.from_json(b.to_json())
        assert back.get_node("n").node_tag == "item"


# =============================================================================
# 6-10. Firma
# =============================================================================


class TestSignedRoundTrip:
    """Con una chiave il payload e' firmato e va verificato al ritorno."""

    def test_xml(self):
        b = Bag()
        b["root"] = Bag()
        b["root.id"] = UuidResolver("uuid4")
        back = Bag.from_xml(b.to_xml(sign_key=KEY), sign_key=KEY)
        assert isinstance(back.get_resolver("root.id"), UuidResolver)

    def test_json(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_json(b.to_json(sign_key=KEY), sign_key=KEY)
        assert isinstance(back.get_resolver("id"), UuidResolver)

    def test_tytx(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        back = Bag.from_tytx(b.to_tytx(sign_key=KEY), sign_key=KEY)
        assert isinstance(back.get_resolver("id"), UuidResolver)

    def test_attribute_side_signed(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("X_SECRET"))
        back = Bag.from_json(b.to_json(sign_key=KEY), sign_key=KEY)
        assert back["n?who"] == "secret"


class TestSignatureRejection:
    """Quello che torna dal client non e' piu' quello che e' partito."""

    def test_wrong_key(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        with pytest.raises(SignatureError):
            Bag.from_json(b.to_json(sign_key=KEY), sign_key="another-secret")

    def test_unsigned_payload_when_key_expected(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        with pytest.raises(SignatureError):
            Bag.from_json(b.to_json(), sign_key=KEY)

    def test_expired_signature(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        data = b.to_json(sign_key=KEY, expires_in=1)
        import time

        time.sleep(1.1)
        with pytest.raises(SignatureExpired):
            Bag.from_json(data, sign_key=KEY)

    def test_tampered_argument_is_refused(self):
        """Il caso vero: il client riscrive un parametro e rimanda.

        Il payload firmato e' base64, quindi il client non puo' editarlo in
        chiaro: puo' solo sostituirlo con uno costruito da se'. Che e'
        esattamente cio' che la firma respinge.
        """
        legit = Bag()
        legit.set_item("n", "v", who=EnvResolver("HOME"))
        signed = json.loads(legit.to_json(typed=False, sign_key=KEY))

        attacker = Bag()
        attacker.set_item("n", "v", who=EnvResolver("PATH"))
        theirs = json.loads(attacker.to_json(typed=False, sign_key="attacker-key"))

        signed[0]["attr"]["who"] = theirs[0]["attr"]["who"]
        with pytest.raises(SignatureError):
            Bag.from_json(json.dumps(signed), sign_key=KEY)

    def test_unsigned_substitution_is_refused(self):
        """Rimandare il payload senza firma non basta a farlo passare."""
        legit = Bag()
        legit.set_item("n", "v", who=EnvResolver("HOME"))
        signed = json.loads(legit.to_json(typed=False, sign_key=KEY))

        attacker = Bag()
        attacker.set_item("n", "v", who=EnvResolver("PATH"))
        bare = json.loads(attacker.to_json(typed=False))

        signed[0]["attr"]["who"] = bare[0]["attr"]["who"]
        with pytest.raises(SignatureError):
            Bag.from_json(json.dumps(signed), sign_key=KEY)

    def test_attribute_side_rejection(self):
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("HOME"))
        with pytest.raises(SignatureError):
            Bag.from_json(b.to_json(sign_key=KEY), sign_key="another-secret")


class TestPayloadWithSeparator:
    """Un payload che contiene il separatore della firma resta integro."""

    def test_json_roundtrip(self, monkeypatch):
        monkeypatch.setenv("X.SECRET.DOTTED", "ok")
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("X.SECRET.DOTTED"))
        back = Bag.from_json(b.to_json(sign_key=KEY), sign_key=KEY)
        assert back["n?who"] == "ok"


# =============================================================================
# 11-13. Inerzia
# =============================================================================


class TestInertness:
    """Serializzare e rileggere non eseguono nulla: solo la lettura lo fa."""

    def test_serializing_does_not_call_load(self):
        CountingResolver.calls = 0
        b = Bag()
        b["x"] = CountingResolver(tag="a")
        b.to_json()
        b.to_xml()
        b.to_tytx()
        assert CountingResolver.calls == 0

    def test_parsing_does_not_call_load(self):
        b = Bag()
        b["x"] = CountingResolver(tag="a")
        data = b.to_json()
        CountingResolver.calls = 0
        Bag.from_json(data)
        assert CountingResolver.calls == 0

    def test_first_read_calls_load(self):
        b = Bag()
        b["x"] = CountingResolver(tag="a")
        back = Bag.from_json(b.to_json())
        CountingResolver.calls = 0
        assert back["x"] == "loaded-a"
        assert CountingResolver.calls == 1


# =============================================================================
# 14. Resolver non serializzabili
# =============================================================================


class TestNonSerializableResolver:
    """Un callback non sta in JSON: errore esplicito, non silenzio."""

    def test_value_side_raises(self):
        b = Bag()
        b["cb"] = BagCbResolver(lambda: 42)
        with pytest.raises(BagSerializationError):
            b.to_json()

    def test_attribute_side_raises(self):
        b = Bag()
        b.set_item("n", "v", cb=BagCbResolver(lambda: 42))
        with pytest.raises(BagSerializationError):
            b.to_json()

    def test_message_names_node_and_attribute(self):
        b = Bag()
        b.set_item("mynode", "v", mykey=BagCbResolver(lambda: 42))
        with pytest.raises(BagSerializationError) as exc:
            b.to_json()
        assert "mynode" in str(exc.value)
        assert "mykey" in str(exc.value)

    def test_all_formats_agree(self):
        b = Bag()
        b["cb"] = BagCbResolver(lambda: 42)
        for dump in (b.to_json, b.to_xml, b.to_tytx):
            with pytest.raises(BagSerializationError):
                dump()


# =============================================================================
# 15-16. deepcopy
# =============================================================================


class TestDeepcopyResolvers:
    """La copia ricostruisce i resolver: nessuna istanza condivisa."""

    def test_value_side_preserved(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        assert isinstance(b.deepcopy().get_resolver("id"), UuidResolver)

    def test_value_side_distinct_instance(self):
        b = Bag()
        b["id"] = UuidResolver("uuid4")
        assert b.deepcopy().get_resolver("id") is not b.get_resolver("id")

    def test_attribute_side_distinct_instance(self):
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("HOME"))
        copy = b.deepcopy()
        assert copy.get_node("n").attr["who"] is not b.get_node("n").attr["who"]

    def test_both_copies_still_resolve(self, monkeypatch):
        monkeypatch.setenv("X_SECRET", "secret")
        b = Bag()
        b.set_item("n", "v", who=EnvResolver("X_SECRET"))
        copy = b.deepcopy()
        assert b["n?who"] == copy["n?who"] == "secret"

    def test_nested_bag_resolver_copied(self):
        b = Bag()
        b["inner"] = Bag()
        b["inner.id"] = UuidResolver("uuid4")
        assert isinstance(b.deepcopy().get_resolver("inner.id"), UuidResolver)


# =============================================================================
# Sicurezza: la classe nominata dal payload
# =============================================================================


class TestClassGuard:
    """Il payload sceglie il nome della classe, non la sua gerarchia."""

    def test_class_outside_hierarchy_is_refused(self):
        forged = json.dumps(
            [
                {
                    "label": "x",
                    "value": None,
                    "attr": {},
                    "resolver": "::RSLV:"
                    + json.dumps(
                        {
                            "resolver_module": "subprocess",
                            "resolver_class": "Popen",
                            "args": [["echo", "pwned"]],
                            "kwargs": {},
                        }
                    ),
                }
            ]
        )
        with pytest.raises(ValueError, match="not a BagResolver subclass"):
            Bag.from_json(forged)

    def test_module_level_function_is_refused(self):
        forged = json.dumps(
            [
                {
                    "label": "x",
                    "value": None,
                    "attr": {},
                    "resolver": "::RSLV:"
                    + json.dumps(
                        {
                            "resolver_module": "os",
                            "resolver_class": "system",
                            "args": ["echo pwned"],
                            "kwargs": {},
                        }
                    ),
                }
            ]
        )
        with pytest.raises(ValueError, match="not a BagResolver subclass"):
            Bag.from_json(forged)
