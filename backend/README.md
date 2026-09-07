# Backend

FastAPI owns synchronous API validation and human-authorized state transitions. Celery owns retryable background work. PostgreSQL is the system of record; Redis is transport, never authoritative state.

The implemented backend includes health/readiness checks, source versioning,
strict local-model extraction, human-only review transitions, media evidence,
deterministic controls, evaluation, audit exports, and Celery workers.

`requirements.lock` is the Python 3.11 constraints snapshot for runtime,
development, and media extras. Docker and GitHub Actions install through this
file and run `pip check`; `pyproject.toml` remains the human-maintained allowed
range contract. Regenerate the constraints intentionally with `pip-compile`
after checking current official releases, then rerun the complete test and
audit gates. A resolved lock improves reproducibility but is not a vulnerability
guarantee.
