# Service Level Agreement: Crate Platform

**Reference:** SLA-PLAT-2.0 · **Version:** 2.0 · **Effective:** 2025-07-01 · **Classification:** Confidential

## 1. Definitions

| Term | Meaning |
|---|---|
| **Availability** | The percentage of minutes in a calendar month in which the Platform responds successfully to health checks run every 60 seconds from at least three locations |
| **Downtime** | A minute in which two or more locations report failed health checks, excluding Excluded Time |
| **Excluded Time** | Scheduled maintenance, force majeure, and the other exclusions in section 7 |
| **Monthly Fee** | The Base Fee plus the Premium Support Fee for the month (EUR 21,700 for the Nortecloud Retail agreement MSA-2025-014) |

## 2. Availability commitment

Crate commits to a monthly Availability of **99.9 %**. Availability is calculated as:

```
Availability = (Total minutes - Excluded Time - Downtime) / (Total minutes - Excluded Time) x 100
```

and rounded to two decimal places.

### 2.1 Scheduled maintenance

Scheduled maintenance is limited to **4 hours per month** and must be notified at least **5 days** in advance. Maintenance windows run between 01:00 and 05:00 Madrid time on Sundays unless the Customer agrees otherwise. Emergency maintenance to fix a critical security vulnerability is excluded from the 4-hour limit but is counted as Downtime if it exceeds 2 hours.

## 3. Service credits

| Monthly Availability | Credit (% of Monthly Fee) |
|---|---|
| 99.90 % or above | 0 % |
| Below 99.90 % and at least 99.50 % | 5 % |
| Below 99.50 % and at least 99.00 % | 15 % |
| Below 99.00 % and at least 95.00 % | 30 % |
| Below 95.00 % | 50 % |

The maximum credit in any month is 50 % of the Monthly Fee.

### 3.1 Worked example

In a 30-day month (43,200 minutes) with no scheduled maintenance, the Platform records 346 minutes of Downtime.

- Availability = (43,200 - 346) / 43,200 = 99.20 %
- This falls in the band "below 99.50 % and at least 99.00 %", so the credit is 15 %.
- Credit = 15 % x EUR 21,700 = **EUR 3,255**, applied to the next invoice.

### 3.2 Claiming credits

The Customer must request a credit in writing within **30 days** of the end of the affected month. Credits are applied to the next invoice and are not paid in cash, except in the final month of the agreement.

## 4. Support

### 4.1 Support plans

| | Standard | Premium |
|---|---|---|
| Hours | 09:00 to 18:00, Monday to Friday (Madrid) | 24 hours, 7 days |
| Channels | Email and portal | Email, portal, phone hotline |
| Named technical contact | No | Yes |
| Included in Base Fee | Yes | No (Premium Support Fee) |

### 4.2 Response and resolution targets

| Severity | Description | Response (Premium) | Response (Standard) | Resolution target |
|---|---|---|---|---|
| S1 Critical | Platform unavailable or data loss | 15 minutes | 1 hour (working hours) | 4 hours |
| S2 High | Main functionality degraded, no workaround | 1 hour | 4 working hours | 8 hours |
| S3 Medium | Defect with a workaround | 4 working hours | 1 working day | 3 working days |
| S4 Low | Question or enhancement | 1 working day | 2 working days | Planned |

Response time is measured from the moment the ticket is registered. Resolution targets are targets, not guarantees, and do not give rise to credits.

### 4.3 Escalation

| Time without progress | Escalate to |
|---|---|
| S1: 1 hour | Head of Operations |
| S1: 3 hours | Chief Technology Officer |
| S2: 4 hours | Head of Operations |

## 5. Backup and recovery

| Parameter | Commitment |
|---|---|
| Recovery Point Objective (RPO) | 1 hour |
| Recovery Time Objective (RTO) | 4 hours |
| Backup frequency | Hourly |
| Backup retention | 30 days |
| Restore test | Quarterly, results shared with the Customer |

## 6. Reporting and review

Crate provides a monthly availability report within 5 working days of month end and holds a quarterly service review with the Customer.

## 7. Exclusions

The following do not count as Downtime:

1. Scheduled maintenance within the limits of section 2.1.
2. Force majeure.
3. Failures of the Customer's own network, systems or third-party services not supplied by Crate.
4. Use of the Platform contrary to the documentation or the agreement.
5. Denial-of-service attacks exceeding the protected capacity stated in Schedule A.
6. Suspension of the Services in accordance with the agreement.

## 8. Chronic failure

If Availability is below 99.90 % in three consecutive months, or in any four months in a rolling twelve-month period, the Customer may terminate the agreement under clause 11.2 of MSA-2025-014 without early termination fee.

## 9. Revision history

| Version | Date | Main changes |
|---|---|---|
| 1.0 | 2022-01-01 | First version |
| 2.0 | 2025-07-01 | Availability raised from 99.5 % to 99.9 %; five credit bands; 24x7 support added; RPO and RTO introduced; claim period extended from 15 to 30 days |
