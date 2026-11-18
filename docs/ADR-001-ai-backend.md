# ADR-001 — Where the Anthropic API key lives

- **Status:** Accepted, implemented on branch `security/local-key-only`
- **Date:** 2026-11-16

> **Note on provenance.** This branch was specified against "ADR-001 Option 2,
> in docs". No `docs/` directory and no ADR existed in the repository when the
> work started — the file had never been committed. This document records the
> decision as built, so the ADR number referenced elsewhere resolves to
> something real. Correct it if it diverges from the original intent.

## Context

`HAL9000-TERMINAL-WEB.html` is a single-file web terminal. Until this branch it
asked the visitor for an Anthropic API key — in a setup overlay field and, as a
fallback, a `window.prompt()` — then called `api.anthropic.com` straight from
the page using `anthropic-dangerous-direct-browser-access: true`. The key was
persisted to `localStorage`, encrypted with AES-GCM under a PBKDF2-derived
passphrase.

Three problems:

1. **The field is phishable.** A page that asks for an `sk-ant-…` key trains
   visitors to type live keys into a web form. Encrypting it afterwards does
   not change what the form teaches, and a tampered or cloned copy of the page
   keeps the field while dropping the encryption.
2. **Client-side encryption protects nothing here.** The passphrase, the
   derivation and the decrypted key all live in the same JavaScript context as
   any injected script. It raises the cost of reading `localStorage` at rest
   and nothing else.
3. **The page owned HAL's character.** The system prompt was a template literal
   in the page, so anything that could modify the page could rewrite who HAL is
   while still spending the key.

## Decision

The browser holds no key under any circumstances. HAL's voice is answered by
whichever of three tiers is available, chosen at runtime:

| Tier | Trigger | Key location | Prompt assembled |
|---|---|---|---|
| **Sidecar** | `GET http://127.0.0.1:3001/api/health` answers `{"ok": true}` within 400 ms | `ANTHROPIC_API_KEY` in the sidecar process environment | Server side, in `hal_claude.py` |
| **Quotes** | anything else | none | n/a — HAL speaks a line from `HAL_QUOTES` |
| **Direct** (dev) | `?direct` in the URL | a closure in the tab, session only | In the page (unavoidable) |

`askHal(utterance, ctx)` is the single dispatcher. Its contract is unchanged
from the `callClaude` it replaced: `string -> string|null`, where `null` means
"no backend answered" and the caller speaks a film quote.

### The sidecar

`hal_sidecar.py`, standard library only:

```
GET  /api/health -> {"ok": bool, "model": str}
POST /api/ask    -> {"reply": str}
     body: {"utterance": str, "crewName": str, "weather": object|null}
```

- Binds `127.0.0.1` from a module constant. There is no flag, no argument and
  no environment variable that can move it to `0.0.0.0`.
- Requires a loopback `Host` header, which blocks DNS-rebinding from a remote
  page that resolves a hostname to 127.0.0.1.
- CORS is limited to loopback origins and `file://` (`Origin: null`).
- The key is never logged, echoed, returned in a response, or included in an
  error. Upstream failures are reported by status code only.

### The browser sends data, not prose

The page POSTs `{utterance, crewName, weather}` as plain values. `hal_claude.py`
owns the persona string and the weather sentence and ignores every other field
in the body, so a page that adds `"system"`, `"model"` or `"max_tokens"` to the
request changes nothing about the call that is made.

## Consequences

- The public GitHub Pages demo has no AI backend. It is a scripted prop that
  speaks film quotes, and the README says so.
- Running the real voice mode requires starting a process locally. That is the
  intended cost.
- `hal_viewscreen.py` (the Pi kiosk) and the sidecar share one implementation
  of the API call via `hal_claude.py`, so they cannot drift apart.
- The `?direct` tier is the one remaining place a key is typed into a browser.
  It is dev-only, unlinked, and holds the key in memory for one tab. It lives
  in a single commit and can be reverted on its own.

## Alternatives rejected

- **Keep the field, encrypt harder.** Does not address the phishing surface,
  which is the actual risk.
- **Hide the field behind a flag.** A field behind a flag is still a field. A
  field that does not exist cannot be phished.
- **Proxy through a hosted function.** Moves the key off the visitor's machine
  but puts the project's key behind a public endpoint and makes the demo cost
  money per visitor. Out of scope for a prop.
