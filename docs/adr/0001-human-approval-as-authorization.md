# ADR 0001: Human approval is an authorization boundary

- Status: Accepted
- Date: 2026-08-24

## Context

Models may misquote a source, misread authority, infer missing scope, or overstate a product finding. A prompt that says "ask a human" does not prevent a worker from writing approved state.

## Decision

Requirements, mappings, and findings begin as candidates. Approval/disposition targets are reserved for an explicitly identified human actor. Model, worker, and system actors are rejected by a shared state guard and PostgreSQL trigger. The local header is not production authentication; SSO/RBAC remain a deployment requirement.

## Consequences

- Extra review UI and domain records are required.
- High-confidence output still waits for review.
- Approval state cannot be derived from model confidence.
- The portfolio can demonstrate authorization as code rather than as policy prose.
