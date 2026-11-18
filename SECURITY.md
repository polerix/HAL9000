# Security Policy

## Reporting a vulnerability

Please do not open a public issue for security problems.
Use GitHub's private reporting: https://github.com/polerix/HAL9000/security/advisories/new

## Secrets

This project must never contain API keys, tokens or passwords in the repository.
If you find one, report it as above so it can be revoked and removed.

Every push and pull request runs `scripts/scan_secrets.py`, which fails the
build on committed credential shapes. It runs its own `--self-test` first, so a
scanner that has silently stopped detecting anything turns the build red rather
than passing for the wrong reason.

### Where the Anthropic API key lives

Nowhere in this repository, and nowhere in the browser.

- `HAL9000-TERMINAL-WEB.html` holds no key and never asks for one. There is no
  key field and no prompt. If a page claiming to be this one asks you to paste
  an `sk-ant-…` key, it is not this build.
- The key is read from the environment by `hal_sidecar.py`, which binds
  `127.0.0.1` only. On a Pi it comes from `/etc/hal9000/env`, root-owned and
  mode 0600.
- It is never logged, never returned in a response, and never included in an
  error body.

Rationale: [`docs/ADR-001-ai-backend.md`](docs/ADR-001-ai-backend.md).
