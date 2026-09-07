from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import RequirementControlMapping, SourceSnapshot
from ..settings import Settings
from .governance import create_fixture_candidates, load_requirement_fixtures, seed_controls
from .sources import create_or_update_registry_sources, store_snapshot


def bootstrap_demo(session: Session, settings: Settings) -> dict[str, int | str]:
    sources = create_or_update_registry_sources(session, settings)
    sources_by_key = {source.stable_key: source for source in sources}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in load_requirement_fixtures(settings)["requirements"]:
        grouped[item["source_key"]].append(item)
    snapshots_by_key: dict[str, SourceSnapshot] = {}
    for source_key, items in grouped.items():
        source = sources_by_key[source_key]
        content = "\n\n".join(
            [
                f"SOURCE: {source.title}",
                f"OFFICIAL URL: {source.official_url}",
                "PUBLIC TEST FIXTURE — MINIMUM ATTRIBUTED EXCERPTS ONLY",
                *[f"{item['locator']}: {item['exact_quote']}" for item in items],
            ]
        )
        snapshots_by_key[source_key] = store_snapshot(
            session,
            settings,
            source=source,
            content=content,
            fetch_status="public_test_fixture",
            locator_map={
                "official_url": source.official_url,
                "notice": "Test fixture; refresh official source before operational use.",
            },
        )
    for source in sources:
        snapshots = list(
            session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.source_id == source.id)
                .order_by(SourceSnapshot.retrieved_at.desc())
            )
        )
        if any(item.fetch_status in {"current", "manual_snapshot"} for item in snapshots):
            continue
        source.status = "fixture_only" if snapshots else "registered"
        source.last_checked_at = None
    session.commit()
    candidates = create_fixture_candidates(session, settings, snapshots_by_source_key=snapshots_by_key)
    controls = seed_controls(session)
    mapping_count = session.scalar(select(func.count()).select_from(RequirementControlMapping)) or 0
    return {
        "sources": len(sources),
        "snapshots": len(snapshots_by_key),
        "requirement_candidates": len(candidates),
        "controls": len(controls),
        "mappings": int(mapping_count),
        "note": "Candidates remain unapproved. Song must review requirements and mappings before rule runs.",
    }
