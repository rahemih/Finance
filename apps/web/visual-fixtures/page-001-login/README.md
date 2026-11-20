# WEB-P0 · PAGE-001 · ورود به حساب کاربری

**Scope:** exact PAGE-001 standalone HTML prototype and its approved visual authority; *not* a functional authentication service. User authorized registration on 2026-11-02.

## What is source-tracked

- `index.html` — complete standalone HTML/CSS/JS visual preview, with both WEBP artworks embedded as data URIs. Can be opened directly in a browser with no package installation.
- `registration.json` — immutable SHA-256 of the supplied standalone page, reference-image hashes, local rendered screenshot hashes and provenance metadata.
- `web-p0-login-visual.yml` (workflow) — headless Chrome captures at 1672×941, 720×1860 and 360×913, validates outputs, stores PNGs as Actions artifacts.

**Authoritative visual design:** embedded approved screenshots in the [master Google Doc](https://docs.google.com/document/d/19trhKWaIB9YUqc3h7sgrovKwRiJKFUM_RSjmj6NDPQ0/edit). New generated pictures are never approved replacements for those images.

**Safety:** No real authentication, request to backend, storage of credentials, financial action, trading order, broker, exchange, or Live/Auto integration. Login form interception is a preview-only interaction. DO NOT mount at `/auth/login` before upstream routing, Auth and security contracts pass.

**Governance:** Draft, stacked on PR #509, blocked from merging to protected main until all required independent governance controls and owner Human Gate pass. This record is evidence of registration, not pixel-perfect certification.

## Original local rendered screenshots

The exact browser PNGs are recorded in `registration.json` by name, resolution and SHA-256. GitHub Actions regenerates images and archives them under its run artifacts. **The original local PNG bytes are not in Git history unless uploaded separately and verified**; do not interpret checksum entries as proof they are source tracked.
