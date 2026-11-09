# Telaryn — Deployment Architecture (Public Overview)

This is a **portable design reference**, not an inventory of any running
Telaryn environment. It intentionally omits resource identifiers, operator
identities, subscription or tenant values, direct administrative endpoints,
recovery identifiers, and environment-specific commands.

## Components

```text
 Browser
    |
    | HTTPS (public gateway, authenticated application routes)
    v
 Reverse proxy / frontend static assets
    |
    +--- /api --> FastAPI application
                        |
                        +--> PostgreSQL (private network)
                        |
                        +--> AI provider (optional; controlled disclosure)
                        |
                        +--> Email delivery (managed identity)
```

One possible deployment uses managed container hosting, private PostgreSQL,
managed identities, a secrets manager, centralized diagnostics, and
infrastructure-as-code. The exact services and names are environment-owned
configuration, not application source.

## Security principles

1. **Separate environments.** Development, staging, and production have
   independent data, sessions, secrets, network boundaries, and operational
   identities. Never import staging users or backups into production.
2. **No credentials in source.** Runtime secrets are obtained through approved
   secret management, preferably without long-lived static cloud credentials.
3. **Enforce authorization on the server.** Workspace access checks apply to
   read and write operations, including search and exports.
4. **Keep data and telemetry bounded.** Avoid user-authored work content,
   credentials, cookies, and AI raw payloads in operational logs.
5. **Preserve human control of AI changes.** A model can propose updates, but
   authoritative changes require explicit, reviewed user action.
6. **Validate recovery.** Backups without verified clean-environment restores
   do not establish a usable recovery posture.
7. **Use immutable release references.** Deploy tested image versions with
   a documented, tested rollback plan.

## Public access and private data

A deployment may expose public product and sign-in pages while keeping
workspace data behind Telaryn authentication and authorization. A public-facing
product does not imply public user data or permissive API access.

Applications must explicitly configure allowed origins, cookie security,
authentication, email invitation behavior, audit retention, private-feedback
access, and external AI-provider disclosure for each environment.

## Operational separation

The original private repository maintains deploy-specific environment runbooks
and infrastructure automation. Those are deliberately **excluded** from the
public source preview. Keep actual tenant/resource identifiers, privileged
identities, incident-response procedures, secret rotation evidence, and
recovery targets in an access-controlled operational system.

See [Operations overview](operations-overview.md) for a generic deployment
review checklist.
