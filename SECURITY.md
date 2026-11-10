# Telaryn Security Policy

Telaryn is under active development. Do not treat the local development
configuration as safe for public deployment.

## Report a vulnerability privately

Send vulnerability reports to **security@telaryn.app**. This is the designated
private reporting mailbox for the Telaryn service and source repository.
If GitHub's private vulnerability reporting feature is enabled in this
repository, you may instead use **Security → Advisories → Report a vulnerability**
to submit a confidential report.

Please provide a concise reproduction path, affected component/version and
potential impact. Do **not** include real account credentials, production
secrets, customer content or exploitation of a live system. Do not put
vulnerability details in public issues or pull requests. Allow the maintainer
to confirm a secure communication channel before sharing sensitive evidence.

## Security boundaries

- Backend-controlled authentication, authorization, and workspace isolation
- Secret management outside source control
- Project and Ticket AI-context controls that are not access-control substitutes
- Independent authentication and approval for AI actions
- Explicit disclosure before transmission of user-authored content to an
  external AI provider
- Database and uploaded-data protection, retention, and recovery validation
- Redacted errors, bounded logs, and reviewed operational diagnostics

Reports are handled privately through the published security mailbox. An
external researcher should request authorization before attempting active
testing of any hosted service; source availability does not authorize testing
production systems or accessing other users' data.

## Security testing

A clean automated secrets scan does not prove the absence of all credentials.
If an actual secret is found, revoke or rotate it first, then investigate its
use and remove it from any public history as appropriate.

This repository contains no live cloud deployment targets or authority over
the separately operated private Atlas staging and production environments.
