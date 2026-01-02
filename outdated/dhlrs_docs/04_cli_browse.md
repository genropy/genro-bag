
# CLI and Browser Interaction Model

A CLI HLRS client or browser HLRS client interacts through:

- D-HLRS identity
- NATS subjects
- WebSocket (browser only)

Example CLI command:
    dhlrs set         --target alfa.beta.hlrs.softwell.it         --path users.alice.age         --value 33

Example browser path:
    alfa.beta.hlrs.softwell.it@page_9fa2.ui.state.sidebar.open
