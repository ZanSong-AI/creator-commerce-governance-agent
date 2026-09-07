# Contributing

This repository is an evidence-bound portfolio system. Contributions should
preserve its human-review and source-lineage guarantees.

## Local checks

```bash
make test-backend
make test-frontend
docker compose config
```

## Pull-request requirements

- Do not add real creator, merchant, account, or platform data.
- Do not commit full policy snapshots, credentials, runtime reports, model
  caches, signing keys, or local databases.
- Keep legal requirements, regulator guidance, and platform policies typed as
  distinct source classes.
- Do not add automated legal conclusions, enforcement, reporting, or approval.
- Add tests for state transitions and lineage-affecting behavior.
- Document material architecture decisions in `docs/adr/`.

Generated metrics must come from a reproducible run and must include failure
cases and limitations.
