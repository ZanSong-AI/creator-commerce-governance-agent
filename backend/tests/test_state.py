from __future__ import annotations

import pytest

from ccg_agent.state import Actor, assert_human_transition


@pytest.mark.parametrize("actor_type", ["model", "worker", "system"])
@pytest.mark.parametrize("target", ["approved", "confirmed_control_issue", "dismissed"])
def test_non_human_cannot_cross_review_boundary(actor_type: str, target: str) -> None:
    with pytest.raises(PermissionError):
        assert_human_transition(Actor(actor_type=actor_type, actor_id="test"), target)


def test_human_can_cross_review_boundary() -> None:
    assert_human_transition(Actor(actor_type="human", actor_id="reviewer-001"), "approved")


def test_worker_can_create_candidate() -> None:
    assert_human_transition(Actor(actor_type="worker", actor_id="celery"), "candidate")
