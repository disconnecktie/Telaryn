# Telaryn — Operations Overview (Public)

This document is a **non-executable review checklist** for independent
deployments. It is not a production recovery runbook and does not identify
or authorize changes to a live cloud account.

## Before deployment

- Establish who owns application access, cloud roles, cost and billing,
  incident escalation, data retention, and backups.
- Confirm explicit deployment approval, a separate production boundary,
  budget controls, and independently issued environment credentials.
- Configure HTTPS, access restrictions, and a least-privilege application
  identity before exposing any sign-in or user-work endpoints.
- Keep private customer data, ticket exports, access requests, audit findings,
  and credentials out of source control and CI artifacts.
- Review third-party service agreements and data-processing terms, especially
  for user-authored content sent to AI services.

## Release verification

- Review the exact commit/image digest to be deployed.
- Run backend and frontend tests, dependency scans, and static analysis.
- Verify all protected APIs reject anonymous users, enforce workspace isolation,
  and prevent cross-workspace reads and modifications.
- Validate content security policy, origin checks, cookies, error redaction,
  API request-size limits, and safe feedback upload handling.
- Prove private network separation for database, secret store, and logging.
- Confirm email ownership and invitation-token scope, expiry, and reuse rules.
- Exercise representative desktop and mobile workflows.

## Recovery and rollback

- Verify an independently stored, access-controlled logical backup.
- Restore it into a **separate non-production target**; check schema version,
  data integrity, authentication boundaries, and representative workflows.
- Test compatible application-image rollback without silently reversing
  database migrations or deleting live data.
- Record outcomes without copying database dumps, connection strings,
  identity tokens, or user data into a public issue or CI log.

## During operations

- Alert on failures, resource usage, and abnormal authentication activity;
  do not log secrets or private ticket bodies.
- Review cloud permissions periodically and rotate compromised credentials.
- Track retention and deletion requirements for logs, feedback, access requests,
  and backups.
- Keep exact administrative identities, tenant and resource values, emergency
  procedures, backup locations, and operator contact information in a separate,
  access-controlled runbook.

## Repository publication boundary

The **private** Atlas development repository contains operational procedures used for
the original deployment. This public source preview omits those instructions.
Publishing the existing repository itself would still expose historical versions;
use a fresh, reviewed history for any public source release.

See [Deployment architecture](deployment-architecture.md) for the public model.
