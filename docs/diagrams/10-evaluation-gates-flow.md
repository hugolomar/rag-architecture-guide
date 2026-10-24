# Evaluation gates flow

Pipeline and feedback-loop view based on ADR 0014, ADR 0015, ADR 0016, and ADR 0017.

```mermaid
flowchart TD
  Dev["Developer change<br/>(code, prompt, config)"]
  DevSet["Development suite<br/>dev_set<br/>Phase 1 deterministic + Phase 2 RAGAS local"]
  PR["PR gate (Jenkins)<br/>val_set<br/>Phase 1 + Phase 2 (smoke)"]
  Main["Mainline gate (Jenkins)<br/>val_set full<br/>Phase 1 + Phase 2"]
  Release["Release gate (Jenkins)<br/>protected_set injected<br/>Phase 1 + Phase 2"]
  Deploy["Deploy"]
  Runtime["Runtime traffic and traces"]
  Incidents["Incidents / low-confidence / user feedback"]
  Curation["Case curation and promotion<br/>dev -> val -> protected"]

  Dev --> DevSet
  DevSet --> PR
  PR -->|pass| Main
  PR -->|fail (hard blocker)| Dev
  Main -->|pass| Release
  Main -->|fail| Dev
  Release -->|pass| Deploy
  Release -->|fail| Dev
  Deploy --> Runtime
  Runtime --> Incidents
  Incidents --> Curation
  Curation --> DevSet

  classDef gate fill:#1168bd,stroke:#0b4884,color:#ffffff,stroke-width:2px;
  classDef eval fill:#229954,stroke:#114d2a,color:#ffffff,stroke-width:2px;
  classDef data fill:#f68a1e,stroke:#c46e18,color:#ffffff,stroke-width:2px;

  class PR,Main,Release gate;
  class DevSet,Curation eval;
  class Runtime,Incidents data;
```

Hard blockers:

- `prohibited_doc_ids` in retrieval context
- `prohibited_answer_keywords` in generation output
- missing `expected_doc_ids` when required
- behavior mismatch (`ground_answer|deny_access|abstain|clarify`)

Informational signals:

- latency trends
- token/cost trends
- non-critical output style drift
