
# Browser HLRS Nodes via WebSocket

Each browser page acts as a temporary HLRS participant.

Identification:
    <server_node>@<page_id>

The browser:
- opens WS to gateway
- sends join message with page_id
- receives D-HLRS events via gateway
- applies them to its local HLRS
- emits its own events to NATS via gateway
