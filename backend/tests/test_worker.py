from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from ccg_agent import worker


def test_media_task_delivery_contract_is_bounded_and_late_acknowledged() -> None:
    task = worker.celery_app.tasks["media.analyze_case"]

    assert worker.celery_app.conf.worker_prefetch_multiplier == 1
    assert task.acks_late is True
    assert task.reject_on_worker_lost is True
    assert task.autoretry_for == (RuntimeError,)
    assert task.max_retries == 2
    assert task.retry_backoff is True


def test_evaluation_task_does_not_claim_automatic_idempotent_retry() -> None:
    task = worker.celery_app.tasks["evaluation.run_gold"]

    assert task.acks_late is False
    assert getattr(task, "autoretry_for", ()) == ()


def test_media_task_retries_one_transient_runtime_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = SimpleNamespace(id="case-retry")
    fake_session = SimpleNamespace(get=lambda model, case_id: case)

    @contextmanager
    def fake_session_local():
        yield fake_session

    attempts = 0

    def flaky_extract(session, settings, media_case):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("synthetic transient media-tool failure")
        return []

    monkeypatch.setattr(worker, "SessionLocal", fake_session_local)
    monkeypatch.setattr(worker, "extract_evidence", flaky_extract)
    monkeypatch.setattr(worker, "run_approved_controls", lambda session, media_case: ([], []))
    monkeypatch.setattr(worker, "record_event", lambda *args, **kwargs: None)

    result = worker.analyze_media_case.apply(args=(case.id,)).get()

    assert result == {
        "status": "analyzed",
        "case_id": case.id,
        "evidence_count": 0,
        "test_count": 0,
        "finding_count": 0,
    }
    assert attempts == 2
