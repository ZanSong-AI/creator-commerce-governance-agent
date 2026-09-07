#!/usr/bin/env python3
"""Validate all public MP4 fixtures against the production media admission gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from ccg_agent.models import MediaCase  # noqa: E402
from ccg_agent.services.media import _asset_path, _probe, _validate_probe  # noqa: E402
from ccg_agent.settings import Settings  # noqa: E402


def main() -> int:
    settings = Settings(project_root=ROOT)
    manifest = json.loads((ROOT / "fixtures" / "media" / "cases.json").read_text(encoding="utf-8"))
    maxima = {
        "bytes": 0,
        "duration_seconds": 0.0,
        "width": 0,
        "height": 0,
        "video_frames": 0,
    }
    verified: list[str] = []
    for item in manifest["cases"]:
        case = MediaCase(
            stable_key=item["stable_key"],
            asset_path=item["asset_path"],
            asset_sha256=item["asset_sha256"],
            mime_type=item["mime_type"],
            caption=item["caption"],
            jurisdiction=item["jurisdiction"],
            relationship_type=item["relationship_type"],
            platform_disclosure_flag=item["platform_disclosure_flag"],
            aigc_expected=item["aigc_expected"],
            visible_aigc_label=item["visible_aigc_label"],
            expected_outcomes=item["expected_outcomes"],
            metadata_json={"synthetic": True},
        )
        path = _asset_path(case, settings)
        probe = _probe(path)
        _validate_probe(probe, settings)
        maxima["bytes"] = max(maxima["bytes"], path.stat().st_size)
        maxima["duration_seconds"] = max(
            maxima["duration_seconds"], float(probe["format"]["duration"])
        )
        for stream in probe["streams"]:
            if stream.get("codec_type") != "video":
                continue
            maxima["width"] = max(maxima["width"], int(stream["width"]))
            maxima["height"] = max(maxima["height"], int(stream["height"]))
            maxima["video_frames"] = max(maxima["video_frames"], int(stream["nb_frames"]))
        verified.append(case.stable_key)

    print(
        json.dumps(
            {
                "status": "passed",
                "cases_verified": len(verified),
                "first_case": verified[0],
                "last_case": verified[-1],
                "maxima": maxima,
                "limits": {
                    "bytes": settings.max_media_bytes,
                    "duration_seconds": settings.max_media_duration_seconds,
                    "width": settings.max_video_width,
                    "height": settings.max_video_height,
                    "video_frames": settings.max_video_frames,
                },
                "checks": [
                    "project-root confinement",
                    "declared MIME and extension",
                    "ISO BMFF ftyp signature",
                    "file size",
                    "SHA-256",
                    "FFprobe metadata",
                    "duration",
                    "resolution",
                    "video frame count",
                ],
                "persistence": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
