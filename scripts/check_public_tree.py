"""Fail closed on common public-release privacy and artifact mistakes."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    "node_modules",
    "dist",
    ".pnpm-store",
    ".runtime",
    "__pycache__",
    "playwright-report",
    "test-results",
}
FORBIDDEN_NAMES = {".env", ".DS_Store"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite3", ".db"}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
}
MAX_PUBLIC_FILE_BYTES = 10 * 1024 * 1024
PERSONAL_ROOT_MARKER = "/" + "Users" + "/"
LOCAL_FILE_URI_MARKER = "file:" + "///"


def tracked_candidates() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not SKIP_PARTS.intersection(path.relative_to(ROOT).parts)
    ]


def main() -> int:
    errors: list[str] = []
    files = tracked_candidates()
    for path in files:
        relative = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden release artifact: {relative}")
        if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
            errors.append(f"oversized public file: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            if PERSONAL_ROOT_MARKER in text or LOCAL_FILE_URI_MARKER in text:
                errors.append(f"personal absolute path in: {relative}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Public-tree check passed for {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
