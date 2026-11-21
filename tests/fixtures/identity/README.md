# Identity Fixtures (Test Seed Catalog)

This directory contains deterministic identity seed data used across local integration tests and quality evaluation suites.

## Purpose & Architectural Role (ADR 0010 & Note 02)

1. **Local IdP & Auth Simulation:**
   - Stand-in for corporate identity providers (Microsoft Entra ID / Google Workspace / Keycloak).
   - Seeds local authentication containers and offline JWT token generators without requiring live cloud IdP connections.

2. **Zero-Trust Security Trimming:**
   - Powers deterministic security trimming tests.
   - Verifies that queries execute strictly against the intersection of the caller's `groups` and document `allowed_groups`.

3. **Why here and not in `evals/`?**
   - Identity catalogs belong to foundational test infrastructure (`tests/`), representing simulated system state.
   - Evaluation suites (`evals/suites/`) consume these identities to attribute benchmark questions to specific personas, maintaining a clean inward dependency direction (`evals/` → `tests/fixtures/`).

## Persona Catalog (`users.json`)

| Persona | `user_principal_name` | Assigned Groups | Security Profile |
| :--- | :--- | :--- | :--- |
| **Alex Morgan** | `alex.morgan@crateexpectations.example` | `all-employees` | Baseline company employee. |
| **Jordan Lee** | `jordan.lee@crateexpectations.example` | `all-employees`, `engineering-core` | Technical engineer with access to system manuals. |
| **Sam Patel** | `sam.patel@crateexpectations.example` | `all-employees`, `people-team` | HR partner with access to personnel policies. |
| **Riley Chen** | `riley.chen@crateexpectations.example` | `all-employees`, `security-oncall` | Security engineer with access to security playbooks. |
| **Taylor Brooks** | `taylor.brooks@crateexpectations.example` | `all-employees`, `leadership` | Executive leadership with access to restricted strategy. |

