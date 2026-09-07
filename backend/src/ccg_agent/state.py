from __future__ import annotations

from dataclasses import dataclass

HUMAN_ONLY_TARGETS = {
    "approved",
    "rejected",
    "superseded",
    "confirmed_control_issue",
    "dismissed",
    "not_applicable",
    "needs_more_evidence",
}


@dataclass(frozen=True)
class Actor:
    actor_type: str
    actor_id: str


def assert_human_transition(actor: Actor, target_status: str) -> None:
    if target_status in HUMAN_ONLY_TARGETS and actor.actor_type != "human":
        raise PermissionError(f"only a human reviewer may transition an entity to {target_status}")
