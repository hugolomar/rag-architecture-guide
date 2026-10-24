# Note 02: How governance metadata is shaped

**Date:** 2026-10-15 · **Status:** decided

Note 01 decides that governance lives in the manifest and not in the files. This note decides the shape of that manifest: which fields exist, what each one means, and which closed list of values it may use. The same section compares each field with the object a connector would receive from Microsoft 365, Google Workspace or a data catalog.

## 1. The record

`data/manifest.json` is a JSON array, one object per file under `data/raw/`. JSON is the payload a REST catalog or Microsoft Graph would return, and a Pydantic model can validate the whole array in one step. The pipeline joins a parsed file to its record by `relative_path`.

```json
{
  "doc_id": "DOC-HR-001",
  "relative_path": "synthetic/remote-work-policy-v2-2025.md",
  "department": "HR",
  "allowed_groups": ["all-employees"],
  "classification": "internal",
  "status": "current"
}
```

`title`, `description` and `keywords` stay with the parser. Freshness pairs (`pair_id`, `superseded_by`) and `expected_docs` / `forbidden_docs` stay in `eval/`. User groups are resolved from the identity provider at runtime and come from `tests/fixtures/identity/users.json` in deterministic test runs.

## 2. Three fields with three jobs

These three travel together on every record, and none of them may stand in for another.

| Field | Question it answers | Used at query time? |
|---|---|---|
| `department` | Who owns the document | No. It is an attribute for citations, filters by area and the `doc_id` series. |
| `allowed_groups` | Who may read it | Yes. A document is visible when the user's groups and this list intersect. |
| `classification` | How sensitive the content is | No, not as an access check. It is the sensitivity label carried on each chunk. |

A document can be owned by HR and readable by every employee. Another can be owned by Security and readable only by the on-call group. The department does not grant access, and the classification does not either. Two documents can share `all-employees` and still differ in classification (`public` against `internal`): the label says whether the content may leave the company, the group list says who inside the company can retrieve it.

## 3. Closed catalogs

**Departments.** `HR`, `Engineering`, `Security`, `Finance`, `Legal`.

**Groups.** `all-employees`, `people-team`, `engineering-core`, `security-oncall`, `leadership`.

**Classification.** `public`, `internal`, `restricted`.

**Status.** `current`, `deprecated`, `archived`.

`deprecated` stays in the index, so a test can show that the current version wins. `archived` must disappear from the results after the next ingestion. The only archived document is the 2023 travel policy. The 2022 remote-work policy and the 2022 SLA are `deprecated`. Everything else is `current`.

There is no separate legal-team group. Legal documents are owned by `Legal` and read by `leadership`, with one exception: the data processing agreement is also readable by `security-oncall`, because that group executes the breach notification the agreement requires.

## 4. How the corpus is assigned

**Docker, ordinary pages (15 files).** Department `Engineering`, group `engineering-core`, classification `internal`. They stand in for the internal engineering wiki. An employee who is not in that group does not retrieve them.

**Docker, engine hardening (2 files).** `seccomp.md` and `userns-remap.md` come from `content/manuals/engine/security/`. Department `Security`, groups `engineering-core` and `security-oncall`, classification `internal`. They are the guide for configuring the daemon, so the people who run the platform still read them, and so does the security on-call. They are not incident-response material.

**Docker, organization identity (3 files).** `core-roles.md`, `permissions-reference.md` and `group-mapping.md` come from `content/manuals/security/`. Department `Security`, groups `security-oncall` and `leadership`, classification `restricted`. They describe who can do what in the organization and how identity-provider groups are mapped. `engineering-core` does not see them. A question about roles must not be answered from these pages for an ordinary engineer.

**Synthetic documents.**

| Documents | Department | Groups | Classification | Status |
|---|---|---|---|---|
| Remote work v1 and v2, leave policy | HR | `all-employees` | internal | v1 `deprecated`, the others `current` |
| Travel policy v2 and v3 | Finance | `all-employees` | internal | v2 `archived`, v3 `current` |
| Salary bands, bonus plan, disciplinary procedure | HR | `people-team`, `leadership` | restricted | `current` |
| Employee security guidelines | Security | `all-employees` | public | `current` |
| Incident response runbook | Security | `security-oncall` | restricted | `current` |
| Privacy policy, supplier code of conduct | Legal | `all-employees` | public | `current` |
| Master services agreement, SLA v1 and v2 | Legal | `leadership` | restricted | SLA v1 `deprecated`, the others `current` |
| Data processing agreement | Legal | `leadership`, `security-oncall` | restricted | `current` |

The runbook does not include `engineering-core`. If it did, an engineer would see both the runbook and the employee security guidelines, and the neighbor test would not separate them. An `all-employees` user who asks about a breach sees the 72-hour deadline in the privacy policy and the 48-hour deadline in the supplier code. The 24-hour deadline in the data processing agreement is visible to `leadership` and `security-oncall`.

## 5. Identifiers

`doc_id` follows `DOC-{DEPT}-{SEQ}`: `DOC-HR-001`, `DOC-ENG-001`, `DOC-SEC-001`, `DOC-FIN-001`, `DOC-LEG-001`. The sequence is per department, in filename order. The five Security-owned Docker pages take `DOC-SEC` identifiers together with the employee guidelines and the runbook; they do not stay in the Engineering series.

The identifier is what evaluation questions point at. `relative_path` is only the join to the file, so a rename of the file does not have to rename every question, as long as the manifest row is updated and the `doc_id` stays.

## 6. What the same fields are in a real project

The manifest is a stand-in for the JSON a connector would already have collected. We name the fields ourselves; a production payload would use the vendor's names and identifiers.

| Field here | Microsoft 365 / Entra ID | Google Workspace | What we simplified |
|---|---|---|---|
| `department` | Owning site, or a column in Purview / the catalog. It is the steward, not the ACL. | Drive folder or a shared drive, plus a catalog attribute. | Five stable names. A real catalog has a hierarchy and more than one owner. |
| `allowed_groups` | Group object ids in the token's `groups` claim, matched against the principals in the Graph `permissions` collection of the drive item. | `permissions[]` entries with `type: group`. | Five readable names instead of object ids. The check is the same: intersection between the caller's groups and the item's readers. |
| `classification` | A Purview sensitivity label (identifier plus a display name such as General, Confidential, Highly confidential). | A Drive classification label. | Three values. Documents that call themselves Confidential in the body are `restricted` here, which is the closest of the three. |
| `status` | A lifecycle column, a retention label, or the item simply no longer being returned by the delta query. | The file trashed, or a label the catalog treats as withdrawn. | `deprecated` is kept on purpose so freshness can be tested. `archived` is the case the delta query must delete from the index. |
| `doc_id` | `driveItem.id`, stable when the file is renamed. | The Drive file id. | A human-readable id. The stability requirement is the same. |
| `relative_path` | `parentReference.path` plus the name, used for display. The join key in production is the source id. | The file path inside the shared drive. | We join on the path because the files on disk are the source system. |

`tests/fixtures/identity/users.json` is the deterministic identity fixture. It seeds local IdP realms for integration tests and keeps suite users stable offline. Every test user carries `all-employees` plus the groups of their function, the way Entra ID would put those groups in the access token. A user with only a function group would miss the policies limited to `all-employees`. `user_id` is an object id, in the style of Entra ID, and does not name the person's function. The five users are an employee (`all-employees`), an engineer (plus `engineering-core`), a people partner (plus `people-team`), a security on-call (plus `security-oncall`) and a leader (plus `leadership`). The evaluation questions that name one of these users come later. The ingestion service itself would run as its own application identity, with rights to read the sources and their ACLs, including HR and legal content that the developers of the pipeline do not personally open.

Changing `allowed_groups` or moving a document to `archived` is the test equivalent of an ACL change or a deletion in SharePoint. The next ingestion has to update the index. Until it does, the previous chunks are what the query filter still sees.

## 7. Decisions made

- The manifest is `data/manifest.json`, validated at ingestion.
- Access is an intersection of `allowed_groups`. Department and classification are attributes, not a second access rule.
- The catalogs in section 3 are closed. A record that uses any other value fails validation.
- Evaluation links between versions live in `eval/`, not in the manifest. The manifest only carries `status`.
- Docker pages under `content/manuals/security/` are restricted organization-identity material. The two pages under `content/manuals/engine/security/` stay internal and readable by `engineering-core`.
- `raw/legal/` and `raw/hr/` are not part of the corpus.

## 8. Limitations

- The field names are ours. A Graph payload says `grantedToV2`, not `allowed_groups`.
- `public` does not mean anonymous. Those documents are still limited to `all-employees`; the label means the content is approved to be shared outside.
- Collapsing Confidential into `restricted` loses a distinction the synthetic documents draw in their own headings. The headings are body text. The filter reads the manifest.
- With no legal-team group, every restricted legal document is visible to the whole of `leadership`.
- A hand-written manifest does not scale. In a real project the connector fills the same fields from the source.

## 9. Still open

How to store `keywords` in the vector index, and whether they also go into the BM25 text. That decision depends on the database, and it is independent of this record.
