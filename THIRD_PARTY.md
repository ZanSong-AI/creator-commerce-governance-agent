# Third-party software and content

The project uses open-source packages declared in `backend/pyproject.toml` and
`frontend/package.json`. CI produces dependency and license inventories and
fails on high-severity package advisories.

Implemented media integrations include FFmpeg (LGPL/GPL options depending on
the distributed build), Tesseract OCR (Apache-2.0), Faster-Whisper (MIT),
`espeak-ng` (GPL-3.0-or-later), and official `c2pa-python` 0.37.8
(Apache-2.0/MIT). They are used as system or package dependencies and are not
vendored into this repository.

PDF audit packages are rendered with ReportLab 5.0.1 (BSD-3-Clause), the
current PyPI release verified on 2026-08-27. ReportLab is installed as a Python
dependency and is not vendored into this repository.

The C2PA 2.4 specification is published under CC BY 4.0. The repository links
to and attributes the specification; it does not redistribute a full snapshot.

Playwright 1.62.1 (Apache-2.0) is a development dependency. The local E2E path
uses Microsoft's official Playwright Ubuntu image; it is not part of the
application's five-service runtime.

Official policy URLs are stored as source metadata. Full retrieved pages are
runtime artifacts and are not redistributed. Any short excerpt committed as a
test fixture must be minimal, attributed, and reviewed before release.

No TikTok logo, private platform data, or real creator content is included.

Open Policy Agent, NIST OSCAL, and ComplianceAsCode are architecture references
documented in `docs/OPEN_SOURCE_BENCHMARK.md`. They are not vendored dependencies,
and no source code was copied from them.
