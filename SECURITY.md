# Security Policy (Public Source Preview)

Telaryn is under active development. Do not treat a local development
configuration as safe for public deployment.

## Report a vulnerability privately

Please use GitHub's **Report a vulnerability** / private security advisory
feature on the public repository when that feature is enabled. Do not put
exploits, credentials, private account information, or user data in public
issues or pull requests.

If private vulnerability reporting has not yet been enabled, contact the
repository owner privately through an agreed channel. Do not publish details
while arranging responsible disclosure.

## Security boundaries

- Backend-controlled authentication, authorization, and workspace isolation
- Secret management outside source control
- Project and Ticket AI-context controls that are not access-control substitutes
- Independent authentication and approval for AI actions
- Explicit disclosure before transmission of user-authored content to an
  external AI provider
- Database and uploaded-data protection, retention, and recovery validation
- Redacted errors, bounded logs, and reviewed operational diagnostics

Report scope and response arrangements should be published before accepting
external contributors or public vulnerability reports.

## Security testing

A clean automated secrets scan does not prove the absence of all credentials.
If an actual secret is found, revoke or rotate it first, then investigate its
use and remove it from any public history as appropriate.

This source preview contains no live cloud deployment targets. Security
reports should not rely on any assumed connection to the owner's private
staging or production environment.
