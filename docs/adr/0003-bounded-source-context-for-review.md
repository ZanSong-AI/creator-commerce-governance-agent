# ADR 0003: Bounded source context for requirement review

## Status

Accepted — 2026-08-28.

## Context

An exact quote and snapshot hash prove lineage, but they do not give a reviewer enough surrounding text to detect a narrowed trigger, omitted condition, or nearby exception. Sending every full runtime snapshot to every review card would increase payload size, duplicate controlled source text, and expand the UI attack surface.

## Decision

The requirement-lineage read model computes a plain-text excerpt around the exact quote. Matching collapses whitespace only for location, then maps the match back to the immutable original text. The projection includes original line range, excerpt SHA-256, exact-match state, and truncation state, and is limited to 6,000 characters. It is never persisted as a substitute snapshot and never rendered as HTML.

## Consequences

- Song can compare the structured actor, trigger, action, exception, and scope against nearby official text without opening a full snapshot first.
- A missing quote context disables approval in the UI and remains blocked by the existing backend validator.
- The full snapshot and canonical official URL remain available for deeper review.
- Source text remains untrusted data and cannot alter system or review rules.
