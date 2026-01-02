
# NATS Transport Layer for D-HLRS

D-HLRS uses NATS as its event fabric.

Key elements:
- each HLRS publishes local events to NATS
- each HLRS subscribes to events targeting its identity
- browser sessions use a WebSocket gateway bridging WS <-> NATS

D-HLRS messages include:
- msg_id
- source (hlrs identity)
- target (optional)
- op: setItem, setValue, setAttr, invalidate
- path
- payload
- reason
- timestamp
