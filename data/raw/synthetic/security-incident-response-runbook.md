# Security Incident Response Runbook

**Version:** 4.0 · **Effective:** 2026-03-01 · **Owner:** Security Team · **Classification:** Restricted. Engineering on-call and Security Team only

## 1. Purpose and scope

This runbook describes how Crate Expectations S.L. detects, contains, investigates and reports security incidents affecting production systems or customer data. It complements the Employee Security Guidelines, which tell all staff how to report a suspected incident.

## 2. Severity levels

| Level | Definition | Examples | Incident Commander | First response | Updates |
|---|---|---|---|---|---|
| SEV1 | Confirmed compromise of customer data or production, or active attack | Credentials leaked and used; ransomware; data exfiltration | Head of Security | 15 minutes | Every 30 minutes |
| SEV2 | Probable compromise or serious vulnerability being exploited | Suspicious admin logins; exploited critical CVE | Security on-call lead | 30 minutes | Every 1 hour |
| SEV3 | Contained event or vulnerability without evidence of exploitation | Malware blocked on a laptop; lost encrypted device | Security on-call | 4 hours | Daily |
| SEV4 | Policy violation or low-risk report | Phishing email reported, no click | Security on-call | 1 working day | On closure |

## 3. Roles

- **Incident Commander**: owns decisions, priorities and communication cadence.
- **Technical Lead**: directs containment and investigation work.
- **Communications Lead**: drafts messages to customers, authorities and staff; approved by Legal.
- **Scribe**: keeps a timestamped log of actions and decisions.

## 4. First 15 minutes

1. Acknowledge the alert and open an incident channel named `inc-YYYYMMDD-short-name`.
2. Assign an Incident Commander and a Scribe.
3. Classify the severity; if in doubt, classify one level higher and downgrade later.
4. Preserve evidence **before** changing anything: snapshot affected systems and copy relevant logs.

```bash
# Snapshot logs from the affected node before any change
journalctl --since "-6h" > /secure/evidence/$INCIDENT_ID/journal.log
kubectl get events --all-namespaces --sort-by=.lastTimestamp > /secure/evidence/$INCIDENT_ID/events.log
```

## 5. Containment

| Situation | Action |
|---|---|
| Compromised user account | Disable the account, revoke active sessions and tokens, force password reset and re-enrol multi-factor authentication |
| Compromised service credential | Rotate the secret, redeploy dependent services, review audit logs for use of the old credential |
| Compromised host or node | Isolate from the network without powering off, to keep memory evidence |
| Exposed storage or database | Block public access, rotate access keys, capture access logs |

```bash
# Isolate a node while keeping it running
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data=false
```

Do not delete compromised resources until the Technical Lead confirms that evidence has been preserved.

## 6. Notification obligations

When an incident involves personal data, the following clocks start when Crate becomes aware of the breach:

| Audience | Deadline | Source |
|---|---|---|
| Customers for whom Crate is a processor (for example Nortecloud Retail under DPA-2025-014) | **24 hours** | Customer data processing agreements |
| Supervisory authority, where Crate is controller | **72 hours** | Privacy Policy v3.0 and data protection law |
| Affected individuals, where the breach is likely to result in a high risk | Without undue delay | Data protection law |
| Suppliers or partners affected | As agreed in the contract; the Supplier Code of Conduct requires suppliers to notify Crate within 48 hours | Contracts |

The Communications Lead prepares the notification with Legal. A notification may be sent in phases if full details are not yet available.

## 7. Investigation

1. Establish the timeline from logs and evidence.
2. Identify the root cause, the data and systems affected and the period of exposure.
3. Confirm that the threat has been removed and that no persistence mechanisms remain.
4. Record all findings in the incident log.

## 8. Recovery

Restore services from known-good backups or rebuild from trusted images. Raise monitoring on affected systems for at least 14 days. The Incident Commander closes the incident only when the Technical Lead confirms that the threat has been eliminated and normal operations have resumed.

## 9. Post-incident review

A blameless review is held within **5 working days** of closure for SEV1 and SEV2 incidents. The review produces a written report with timeline, root cause, what worked, what did not, and tracked corrective actions with owners and deadlines.

## 10. Revision history

| Version | Date | Main changes |
|---|---|---|
| 3.0 | 2024-06-01 | Introduced severity levels SEV1 to SEV4 |
| 3.2 | 2025-07-01 | Added 24-hour customer notification for processor contracts |
| 4.0 | 2026-03-01 | Added evidence-preservation step before containment; blameless review mandatory for SEV2 |
