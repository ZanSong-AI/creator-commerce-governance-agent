# Security Policy

## Supported versions

Security fixes are applied to the latest development branch until the first
tagged release exists.

## Reporting

Do not open a public issue containing credentials, private media, personal
data, or exploit details. Contact the repository owner through the private
channel listed on their GitHub profile.

## Deliberate boundaries

- The application accepts only allowlisted public-policy sources.
- Source text, captions, transcripts, and model responses are untrusted data.
- Cloud model calls and external enforcement actions are disabled in v0.1.
- Approval transitions require an explicitly identified human actor and are
  enforced again by PostgreSQL triggers.
- Runtime snapshots, audit exports, certificates, keys, and databases are
  excluded from version control.

This demonstration is not legal advice and is not affiliated with TikTok.

## Prototype limitation

The local portfolio UI uses an `X-Reviewer-Id` header and does not implement
production identity, SSO, RBAC, CSRF protection, or multi-tenant isolation.
Database constraints prove that a model/worker path cannot label itself human;
they do not replace deployment authentication. Do not expose this development
server to an untrusted network.
