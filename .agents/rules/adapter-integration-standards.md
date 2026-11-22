---
description: Mandatory standards for infrastructure adapters, defensive error handling, and external dependency isolation
trigger: model_decision
---

# Infrastructure Adapter Integration Standards

All concrete infrastructure adapters residing in `src/adapters/` must strictly comply with these engineering standards to isolate external dependencies and ensure resilient operation.

## 1. Defensive Adapter Initialization & Operational Errors

Infrastructure adapters initializing third-party models, drivers, or network transports must never leak raw transport or socket exceptions:
- **Scrub Low-Level Transport Errors**: Never leak raw socket timeouts or cryptic transport traces (e.g. `urllib3.ConnectTimeoutError`, raw HTTP connection drops) to upstream caller domains.
- **Actionable Operational Exceptions**: Adapters must wrap external model/driver instantiation and remote calls in explicit, domain-meaningful exception handling. Error messages must communicate clear prerequisites (e.g., pre-cached weights in `~/.cache/`, unreachable identity providers, or down databases) to developers and operators.

## 2. Port Contract Compliance

Every adapter must nominally implement its corresponding domain port:
- Inherit explicitly from the corresponding abstract base class in `src/domain/ports/`.
- Adhere strictly to port signatures and return types without adding proprietary or provider-leaking parameters to the public contract.
