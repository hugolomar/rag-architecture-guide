# ADR 0010: Identity Provider and OIDC Token Validation

- Status: Accepted
- Date: 2026-10-24

## Context

ADR 0007 defines the HTTP contract and currently uses a development identity header. ADR 0009
defines runtime trust boundaries and requires identity authority to stay in system components, not
in caller-supplied fields.

The project now needs a realistic identity flow for runtime and integration checks while keeping
deterministic suite runs fast and reproducible.

## Decision

Adopt OIDC bearer-token identity, with Keycloak as the local development identity provider.

- Runtime HTTP requests use `Authorization: Bearer <token>`.
- The API validates JWTs through OIDC discovery/JWKS and enforces `iss`, `aud`, signature, and
  expiry checks.
- Caller identity is read from token claims (`sub` as `user_id`) and group claims (`groups`).
- Missing or invalid bearer tokens fail with `401` before retrieval.
- Local and CI integration environments run Keycloak in a dedicated container.
- `tests/fixtures/identity/users.json` is the seed catalog for local identity fixtures and for
  deterministic suite integrity checks.
- Evaluation remains split:
  - deterministic suite checks do not require a live IdP container,
  - integration/E2E checks exercise full bearer-token validation against Keycloak.

## Rationale

- Signed bearer tokens prevent caller-side identity spoofing that header-only identity cannot stop.
- OIDC/JWKS validation keeps identity trust anchored in the IdP instead of repository files.
- A local IdP container is realistic without coupling all test lanes to external network services.
- Keeping deterministic suites offline preserves fast feedback and stable CI diagnostics.

## Alternatives Considered

1. **Keep `X-User-Id` as runtime identity**
   - Pros: minimal setup.
   - Cons: easy impersonation; not production-realistic.
   - Rejected.

2. **Make all suites depend on live Keycloak**
   - Pros: one identity path everywhere.
   - Cons: slower and less deterministic feedback for retrieval/security mechanics.
   - Rejected.

3. **Use production IdP directly in local development**
   - Pros: highest environment parity.
   - Cons: operational coupling, access friction, and weaker isolation for local experimentation.
   - Rejected.

## Consequences

- **Positive:** runtime identity handling becomes production-like and auditable.
- **Positive:** bearer-token validation aligns API behavior with zero-trust boundaries.
- **Negative:** local/integration setup adds IdP container and token-issuance steps.
- **Negative:** identity adapter and key rotation validation add implementation complexity.
- **Boundary:** this ADR does not choose the production IdP vendor.
- **Follow-up:** update ADR 0007 and runtime diagrams to use bearer-token identity.
