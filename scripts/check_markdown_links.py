"""Validate repository-local Markdown links without accessing the network."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PARTS = {".git", "node_modules", "dist", ".pnpm-store", ".runtime"}


def markdown_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.md")
        if not SKIP_PARTS.intersection(path.relative_to(ROOT).parts)
    ]


def main() -> int:
    errors: list[str] = []
    checked = 0
    for document in markdown_files():
        for match in LINK_PATTERN.finditer(document.read_text(encoding="utf-8")):
            raw_target = match.group(1).strip().strip("<>")
            target = raw_target.split(maxsplit=1)[0]
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = unquote(target.split("#", maxsplit=1)[0])
            if not path_part:
                continue
            checked += 1
            if Path(path_part).is_absolute():
                errors.append(
                    f"{document.relative_to(ROOT)}: absolute local link {target}"
                )
                continue
            resolved = (document.parent / path_part).resolve()
            if (
                not resolved.exists()
                or ROOT not in resolved.parents
                and resolved != ROOT
            ):
                errors.append(
                    f"{document.relative_to(ROOT)}: missing or escaped link {target}"
                )
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Validated {checked} repository-local Markdown links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
