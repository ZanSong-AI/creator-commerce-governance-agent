from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Source, SourceSnapshot
from ..settings import Settings


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.suppressed += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.suppressed:
            self.suppressed -= 1

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)

    def text(self) -> str:
        return "\n".join(self.parts)


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalized_text_with_positions(content: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    positions: list[int] = []
    for index, character in enumerate(content):
        if character.isspace():
            if characters and characters[-1] != " ":
                characters.append(" ")
                positions.append(index)
            continue
        characters.append(character)
        positions.append(index)
    if characters and characters[-1] == " ":
        characters.pop()
        positions.pop()
    return "".join(characters), positions


def requirement_review_context(
    content: str,
    exact_quote: str,
    *,
    surrounding_lines: int = 1,
    max_chars: int = 6000,
) -> dict[str, object]:
    """Return a bounded, line-addressable excerpt around an exact quote.

    Source text remains untrusted input. The result is plain text only and is
    intentionally bounded so a review surface does not need the full snapshot.
    """
    normalized_content, positions = _normalized_text_with_positions(content)
    normalized_quote = " ".join(exact_quote.split())
    normalized_start = normalized_content.find(normalized_quote)
    if normalized_start < 0 or not normalized_quote:
        return {
            "excerpt": "",
            "excerpt_sha256": None,
            "exact_quote_found": False,
            "start_line": None,
            "end_line": None,
            "truncated": False,
        }

    original_start = positions[normalized_start]
    normalized_end = normalized_start + len(normalized_quote)
    original_end = positions[normalized_end - 1] + 1

    excerpt_start = original_start
    for _ in range(surrounding_lines + 1):
        boundary = content.rfind("\n", 0, excerpt_start)
        if boundary < 0:
            excerpt_start = 0
            break
        excerpt_start = boundary
    if excerpt_start > 0:
        excerpt_start += 1

    excerpt_end = original_end
    for _ in range(surrounding_lines + 1):
        boundary = content.find("\n", excerpt_end)
        if boundary < 0:
            excerpt_end = len(content)
            break
        excerpt_end = boundary + 1

    bounded_start = excerpt_start
    bounded_end = excerpt_end
    if excerpt_end - excerpt_start > max_chars:
        quote_length = original_end - original_start
        left_budget = max(0, (max_chars - quote_length) // 2)
        bounded_start = max(excerpt_start, original_start - left_budget)
        bounded_end = min(excerpt_end, bounded_start + max_chars)
        if bounded_end - bounded_start < max_chars:
            bounded_start = max(excerpt_start, bounded_end - max_chars)

    excerpt = content[bounded_start:bounded_end].strip()
    return {
        "excerpt": excerpt,
        "excerpt_sha256": sha256_text(excerpt),
        "exact_quote_found": True,
        "start_line": content.count("\n", 0, bounded_start) + 1,
        "end_line": content.count("\n", 0, bounded_end) + 1,
        "truncated": bounded_start > excerpt_start or bounded_end < excerpt_end,
    }


def load_registry(settings: Settings) -> dict:
    path = settings.project_root / "config" / "source_registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_source(settings: Settings, stable_key: str) -> dict:
    return next(
        item
        for item in load_registry(settings)["sources"]
        if item["stable_key"] == stable_key
    )


REGISTRY_FIELDS = (
    "publisher",
    "title",
    "official_url",
    "source_type",
    "jurisdiction",
    "published_date",
    "effective_date",
    "version",
    "applicable_scope",
    "fetch_mode",
    "redistribution_note",
)

FRESHNESS_FIELDS = {
    "official_url",
    "source_type",
    "jurisdiction",
    "published_date",
    "effective_date",
    "version",
    "applicable_scope",
    "fetch_mode",
}


def sync_registry_sources(
    session: Session, settings: Settings
) -> tuple[list[Source], dict[str, object]]:
    registry = load_registry(settings)
    registered: list[Source] = []
    changes: list[dict[str, object]] = []
    created = 0
    updated = 0
    invalidated = 0
    for item in registry["sources"]:
        source = session.scalar(select(Source).where(Source.stable_key == item["stable_key"]))
        values = {key: item[key] for key in ("stable_key", *REGISTRY_FIELDS)}
        values["official_url"] = str(values["official_url"])
        for field in ("published_date", "effective_date"):
            values[field] = date.fromisoformat(values[field]) if values.get(field) else None
        if source is None:
            source = Source(**values)
            session.add(source)
            created += 1
            changes.append({"stable_key": item["stable_key"], "kind": "created", "fields": []})
        else:
            changed_fields = [key for key in REGISTRY_FIELDS if getattr(source, key) != values[key]]
            freshness_invalidated = bool(FRESHNESS_FIELDS.intersection(changed_fields))
            before_status = source.status
            for key in REGISTRY_FIELDS:
                value = values[key]
                setattr(source, key, value)
            if changed_fields:
                updated += 1
                if freshness_invalidated:
                    source.status = "registered"
                    source.last_checked_at = None
                    invalidated += 1
                changes.append(
                    {
                        "stable_key": item["stable_key"],
                        "kind": "updated",
                        "fields": changed_fields,
                        "freshness_invalidated": freshness_invalidated,
                        "previous_status": before_status,
                        "current_status": source.status,
                    }
                )
        registered.append(source)
    session.commit()
    for source in registered:
        session.refresh(source)
    return registered, {
        "registry_version": registry["registry_version"],
        "sources": len(registered),
        "created": created,
        "updated": updated,
        "freshness_invalidated": invalidated,
        "changes": changes,
        "note": "Registry sync never creates, reviews, or approves a requirement.",
    }


def create_or_update_registry_sources(session: Session, settings: Settings) -> list[Source]:
    sources, _ = sync_registry_sources(session, settings)
    return sources


def _write_runtime_snapshot(settings: Settings, snapshot: SourceSnapshot) -> None:
    target = settings.runtime_root / "sources" / snapshot.source_id
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{snapshot.content_hash}.txt"
    if not path.exists():
        path.write_text(snapshot.content_text, encoding="utf-8")


def _diff(previous: SourceSnapshot | None, content: str) -> tuple[str | None, dict]:
    if previous is None:
        return None, {"kind": "initial", "added_lines": len(content.splitlines()), "removed_lines": 0}
    changes = list(
        difflib.unified_diff(
            previous.content_text.splitlines(),
            content.splitlines(),
            fromfile=previous.content_hash,
            tofile=sha256_text(content),
            lineterm="",
        )
    )
    return previous.id, {
        "kind": "unchanged" if previous.content_text == content else "changed",
        "added_lines": sum(1 for line in changes if line.startswith("+") and not line.startswith("+++")),
        "removed_lines": sum(1 for line in changes if line.startswith("-") and not line.startswith("---")),
        "preview": changes[:40],
    }


def store_snapshot(
    session: Session,
    settings: Settings,
    *,
    source: Source,
    content: str,
    fetch_status: str,
    locator_map: dict,
) -> SourceSnapshot:
    content_hash = sha256_text(content)
    authoritative_refresh = fetch_status in {"current", "manual_snapshot"}
    existing = session.scalar(
        select(SourceSnapshot).where(
            SourceSnapshot.source_id == source.id,
            SourceSnapshot.content_hash == content_hash,
        )
    )
    if authoritative_refresh:
        source.last_checked_at = datetime.now(UTC)
    if existing:
        if authoritative_refresh:
            source.status = "current"
        elif source.status not in {"current", "changed"}:
            source.status = "fixture_only"
        session.commit()
        return existing
    previous = session.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_id == source.id)
        .order_by(SourceSnapshot.retrieved_at.desc())
        .limit(1)
    )
    previous_id, summary = _diff(previous, content)
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=content_hash,
        content_text=content,
        locator_map=locator_map,
        diff_from_snapshot_id=previous_id,
        diff_summary=summary,
        fetch_status=fetch_status,
    )
    if authoritative_refresh:
        prior_authoritative = previous is not None and previous.fetch_status in {
            "current",
            "manual_snapshot",
        }
        source.status = "changed" if prior_authoritative else "current"
    elif source.status not in {"current", "changed"}:
        source.status = "fixture_only"
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    _write_runtime_snapshot(settings, snapshot)
    return snapshot


def _ecfr_xml_text(content: str) -> str:
    root = ElementTree.fromstring(content)
    lines: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in {"HEAD", "P", "FP", "PSPACE"}:
            continue
        value = " ".join("".join(element.itertext()).split())
        if value and (not lines or lines[-1] != value):
            lines.append(value)
    return "\n".join(lines)


def _fetch_ecfr_api(
    client: httpx.Client,
    settings: Settings,
    source: Source,
    registry_item: dict,
) -> tuple[str, dict]:
    retrieval = registry_item.get("retrieval") or {}
    title = int(retrieval["title"])
    part = str(retrieval["part"])
    hostname = urlparse(source.official_url).hostname
    if hostname != "www.ecfr.gov":
        raise HTTPException(status_code=400, detail="eCFR API mode requires www.ecfr.gov")

    metadata_url = "https://www.ecfr.gov/api/versioner/v1/titles.json"
    metadata_response = client.get(metadata_url)
    metadata_response.raise_for_status()
    metadata = metadata_response.json()
    title_metadata = next(
        (item for item in metadata.get("titles", []) if int(item.get("number", -1)) == title),
        None,
    )
    if not title_metadata or not title_metadata.get("up_to_date_as_of"):
        raise ValueError("eCFR title metadata is missing up_to_date_as_of")
    as_of = date.fromisoformat(title_metadata["up_to_date_as_of"]).isoformat()
    retrieval_url = (
        f"https://www.ecfr.gov/api/versioner/v1/full/{as_of}/title-{title}.xml?part={part}"
    )
    response = client.get(retrieval_url)
    response.raise_for_status()
    if len(response.content) > settings.max_source_bytes:
        raise HTTPException(status_code=413, detail="Source exceeds configured snapshot size")
    content = _ecfr_xml_text(response.text)
    marker = "if the representation is made through both visual and audible means"
    if len(content) < 500 or marker not in content.lower():
        raise ValueError("eCFR API response is incomplete or missing the reviewed marker")
    return content, {
        "content_type": response.headers.get("content-type"),
        "official_url": source.official_url,
        "retrieval_url": retrieval_url,
        "retrieval_mode": "official_ecfr_versioner_api",
        "up_to_date_as_of": as_of,
        "latest_amended_on": title_metadata.get("latest_amended_on"),
        "title": title,
        "part": part,
    }


def _fetch_tiktok_faq_api(
    client: httpx.Client,
    settings: Settings,
    source: Source,
    registry_item: dict,
) -> tuple[str, dict]:
    """Read one allowlisted TikTok Help Center article through TikTok's public FAQ API."""
    retrieval = registry_item.get("retrieval") or {}
    faq_id = str(retrieval["faq_id"])
    expected_title = str(retrieval["expected_title"])
    locale = str(retrieval.get("locale", "en"))
    country = str(retrieval.get("country", "US"))
    hostname = urlparse(source.official_url).hostname
    if hostname != "support.tiktok.com":
        raise HTTPException(
            status_code=400,
            detail="TikTok FAQ API mode requires a support.tiktok.com canonical URL",
        )
    if not faq_id.isdecimal() or len(faq_id) > 32:
        raise ValueError("TikTok FAQ ID is invalid")

    retrieval_url = "https://www.tiktok.com/feedback/1/faq_detail_by_id/"
    response = client.get(
        retrieval_url,
        params={
            "faq_id": faq_id,
            "country": country,
            "lang": locale,
            "entrance": "general",
            "app_id": "1284",
            "app_key": "tiktok-web",
            "fetch_faq_version": "1",
            "aid": "1284",
            "app_name": "tiktok_web",
            "appkey": "tiktok-web",
            "channel": "tiktok_web",
            "device_platform": "web_pc",
            "app_language": locale,
        },
    )
    response.raise_for_status()
    if len(response.content) > settings.max_source_bytes:
        raise HTTPException(status_code=413, detail="Source exceeds configured snapshot size")
    payload = response.json()
    if payload.get("status_code") != 200 or payload.get("status_message") != "success":
        raise ValueError("TikTok FAQ API did not return a successful response")
    articles = payload.get("faq_list")
    if not isinstance(articles, list):
        raise ValueError("TikTok FAQ API response is missing faq_list")
    article = next(
        (item for item in articles if isinstance(item, dict) and str(item.get("FaqId")) == faq_id),
        None,
    )
    if article is None:
        raise ValueError("TikTok FAQ API response does not contain the registered FAQ ID")
    title = str(article.get("Name") or "").strip()
    if title != expected_title:
        raise ValueError("TikTok FAQ API title does not match the registered title")
    html_value = article.get("Value")
    if not isinstance(html_value, str):
        raise ValueError("TikTok FAQ API response is missing article HTML")
    parser = VisibleTextParser()
    parser.feed(html_value)
    article_text = re.sub(r"\s+([,.;:!?])", r"\1", parser.text())
    marker = str(retrieval["expected_marker"])
    normalized_article_text = re.sub(
        r"\s+([,.;:!?])", r"\1", " ".join(article_text.split())
    ).casefold()
    normalized_marker = re.sub(r"\s+([,.;:!?])", r"\1", " ".join(marker.split())).casefold()
    if len(article_text) < 500 or normalized_marker not in normalized_article_text:
        raise ValueError("TikTok FAQ API response is incomplete or missing the reviewed marker")
    content = f"{title}\n{article_text}"
    return content, {
        "content_type": response.headers.get("content-type"),
        "official_url": source.official_url,
        "retrieval_url": str(response.request.url),
        "retrieval_mode": "official_tiktok_public_faq_api",
        "normalizer_version": "tiktok-faq-html-v1",
        "faq_id": faq_id,
        "article_title": title,
        "locale": locale,
        "country": country,
        "use_default_language": bool(article.get("UseDefaultLang")),
        "is_ai_translated": bool(article.get("IsAITranslated")),
        "style_version": article.get("StyleVersion"),
    }


def refresh_official_source(session: Session, settings: Settings, source: Source) -> SourceSnapshot:
    parsed = urlparse(source.official_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Only credential-free HTTPS official URLs are allowed")
    registry = load_registry(settings)
    registry_hosts = {urlparse(item["official_url"]).hostname for item in registry["sources"]}
    if parsed.hostname not in registry_hosts:
        raise HTTPException(status_code=400, detail="Source host is not in the official allowlist")
    try:
        with httpx.Client(
            timeout=20, follow_redirects=False, headers={"User-Agent": "CCGAgent/0.1 source-monitor"}
        ) as client:
            if source.fetch_mode == "ecfr_api":
                registry_item = _registry_source(settings, source.stable_key)
                content, locator_map = _fetch_ecfr_api(client, settings, source, registry_item)
                return store_snapshot(
                    session,
                    settings,
                    source=source,
                    content=content,
                    fetch_status="current",
                    locator_map=locator_map,
                )
            if source.fetch_mode == "tiktok_faq_api":
                registry_item = _registry_source(settings, source.stable_key)
                content, locator_map = _fetch_tiktok_faq_api(
                    client, settings, source, registry_item
                )
                return store_snapshot(
                    session,
                    settings,
                    source=source,
                    content=content,
                    fetch_status="current",
                    locator_map=locator_map,
                )
            response = client.get(source.official_url)
        if response.status_code != 200:
            if response.is_redirect or "manual_snapshot" in source.fetch_mode:
                source.status = "manual_snapshot_required"
                source.last_checked_at = datetime.now(UTC)
                session.commit()
                raise HTTPException(
                    status_code=409,
                    detail="Official page could not be safely fetched; a human-provided snapshot is required",
                )
            raise httpx.HTTPStatusError(
                "official source fetch failed", request=response.request, response=response
            )
        if len(response.content) > settings.max_source_bytes:
            raise HTTPException(status_code=413, detail="Source exceeds configured snapshot size")
        parser = VisibleTextParser()
        parser.feed(response.text)
        content = parser.text()
        expected_markers = {
            "tiktok-commercial-content-disclosure": "content disclosure setting",
            "tiktok-aigc-labeling": "AI-generated content",
        }
        marker = expected_markers.get(source.stable_key)
        if len(content) < 500 or (marker and marker.lower() not in content.lower()):
            source.status = "manual_snapshot_required"
            source.last_checked_at = datetime.now(UTC)
            session.commit()
            raise HTTPException(status_code=409, detail="Official page requires a human-provided snapshot")
        return store_snapshot(
            session,
            settings,
            source=source,
            content=content,
            fetch_status="current",
            locator_map={
                "content_type": response.headers.get("content-type"),
                "official_url": source.official_url,
            },
        )
    except HTTPException:
        raise
    except (httpx.HTTPError, UnicodeError, ValueError, ElementTree.ParseError) as exc:
        manual_required = "manual_snapshot" in source.fetch_mode
        source.status = "manual_snapshot_required" if manual_required else "fetch_error"
        source.last_checked_at = datetime.now(UTC)
        session.commit()
        if manual_required:
            raise HTTPException(
                status_code=409,
                detail="Official page could not be safely fetched; a human-provided snapshot is required",
            ) from exc
        raise HTTPException(
            status_code=502, detail=f"Official source fetch failed: {type(exc).__name__}"
        ) from exc


def store_manual_snapshot(
    session: Session,
    settings: Settings,
    *,
    source: Source,
    content: str,
    confirmed_url: str,
    locator_note: str,
) -> SourceSnapshot:
    if confirmed_url.rstrip("/") != source.official_url.rstrip("/"):
        raise HTTPException(
            status_code=400, detail="Confirmed URL does not match the registered official source"
        )
    return store_snapshot(
        session,
        settings,
        source=source,
        content=content,
        fetch_status="manual_snapshot",
        locator_map={"official_url": source.official_url, "human_note": locator_note},
    )
