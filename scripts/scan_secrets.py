#!/usr/bin/env python3
"""
HAL 9000 — secret scanner
=========================

Greps the working tree for live credential shapes and exits non-zero if it
finds one. Standard library only, no network, no install step.

Why not gitleaks: in this project it passed silently twice in one week —
once by crashing with SIGILL (a crash is not a pass, but the job was green)
and once because it had no Anthropic rule at all. The lesson taken here is
that a scanner must prove it can fail, every run, on this machine:

    python3 scripts/scan_secrets.py --self-test

plants each pattern in a throwaway directory and asserts the scanner
catches it. CI runs the self-test BEFORE the real scan, so a scanner that
has silently stopped working turns the build red instead of green.

Usage:
    python3 scripts/scan_secrets.py            # scan the tree, exit 1 on a hit
    python3 scripts/scan_secrets.py --self-test
    python3 scripts/scan_secrets.py PATH ...

Exit codes:  0 clean   1 secret found   2 scanner error / self-test failed
"""

import argparse
import math
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------------------
# Patterns. Each is (name, compiled regex). Keep them anchored on the
# vendor's literal prefix wherever one exists — prefixes are what make a
# match a credential rather than a random string.
# ---------------------------------------------------------------------------
B64 = r"A-Za-z0-9_\-"

PATTERNS = [
    ("anthropic-api-key",   re.compile(r"sk-ant-[" + B64 + r"]{24,}")),
    ("openai-api-key",      re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{32,}")),
    ("github-pat-classic",  re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("github-pat-fine",     re.compile(r"github_pat_[A-Za-z0-9_]{60,}")),
    ("aws-access-key-id",   re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b")),
    ("aws-secret-access-key",
     re.compile(r"(?i)aws.{0,20}?(?:secret|private).{0,20}?['\"=:\s]([A-Za-z0-9/+=]{40})")),
    ("slack-token",         re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google-api-key",      re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("private-key-block",   re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
]

# Generic high-entropy: a secret-ish name assigned a long random-looking value.
GENERIC = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|AUTH)[A-Z0-9_]*)"
    r"\s*[:=]\s*['\"]?([" + B64 + r"+/=]{24,})['\"]?"
)
ENTROPY_THRESHOLD = 4.0

# Directories never worth scanning. Deliberately short: only VCS internals
# and dependency/build caches. Media directories are NOT skipped by name —
# a key dropped into Animations/ or Fonts/ must still be found. Media files
# are excluded by extension instead, which has no such blind spot.
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env", "ENV",
    "dist", "build", ".mypy_cache", ".pytest_cache",
}
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".bmp", ".tiff",
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".mp4", ".mov", ".avi", ".mkv",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".tar", ".pdf", ".3mf", ".stl",
    ".pyc", ".so", ".dylib", ".dll", ".ai",
}
MAX_BYTES = 2 * 1024 * 1024

# Lines carrying this marker are exempt. Use it only for documented
# placeholders, and keep the reason on the same line.
ALLOW_MARKER = "scan-secrets:allow"


def shannon(s: str) -> float:
    if not s:
        return 0.0
    return -sum(
        (n / len(s)) * math.log2(n / len(s))
        for n in (s.count(c) for c in set(s))
    )


def mask(secret: str) -> str:
    """Never print a found secret in full — CI logs are not a safe place."""
    if len(secret) <= 10:
        return secret[:2] + "*" * (len(secret) - 2)
    return f"{secret[:6]}…{secret[-2:]} ({len(secret)} chars)"


def scan_text(text, path):
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for name, rx in PATTERNS:
            for m in rx.finditer(line):
                findings.append((path, lineno, name, mask(m.group(0))))
        for m in GENERIC.finditer(line):
            var, val = m.group(1), m.group(2)
            if any(rx.search(val) for _, rx in PATTERNS):
                continue                      # already reported above
            if shannon(val) >= ENTROPY_THRESHOLD:
                findings.append((path, lineno, f"high-entropy-{var.lower()}", mask(val)))
    return findings


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if os.path.splitext(fn)[1].lower() in SKIP_EXTS:
                    continue
                try:
                    if os.path.getsize(p) > MAX_BYTES or os.path.islink(p):
                        continue
                except OSError:
                    continue
                yield p


def scan(roots):
    findings = []
    for p in iter_files(roots):
        try:
            with open(p, "r", encoding="utf-8", errors="strict") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue                          # binary or unreadable: skip
        findings.extend(scan_text(text, p))
    return findings


# ---------------------------------------------------------------------------
# Self-test: prove the scanner can still fail.
# ---------------------------------------------------------------------------
SELF_TEST_CASES = [
    ("anthropic.txt",  "ANTHROPIC_API_KEY=sk-ant-api03-" + "A1b2C3d4E5f6G7h8J9k0L1m2", "anthropic-api-key"),
    ("gh_classic.txt", "token: ghp_" + "aB3dE5gH7jK9lM1nO3pQ5rS7tU9vW1xY3zA5", "github-pat-classic"),
    ("gh_oauth.txt",   "gho_" + "aB3dE5gH7jK9lM1nO3pQ5rS7tU9vW1xY3zA5", "github-pat-classic"),
    ("aws_id.txt",     "aws_access_key_id = AKIA" + "IOSFODNN7EXAMPLE", "aws-access-key-id"),
    ("aws_sec.txt",    "aws_secret_access_key = " + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "aws-secret-access-key"),  # scan-secrets:allow AWS's own published doc example, not live
    ("generic.txt",    "SESSION_SECRET = 'Zx9Qm2Vb7Nk4Lp1Rt6Ys3Wd8Hf5Jg0Cv'", "high-entropy"),  # scan-secrets:allow self-test fixture, random string
    ("privkey.txt",    "-----BEGIN RSA PRIVATE KEY-----", "private-key-block"),  # scan-secrets:allow self-test fixture, header only
]


def self_test() -> int:
    print("self-test: planting known credential shapes and checking detection")
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        for fn, content, expect in SELF_TEST_CASES:
            p = os.path.join(td, fn)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            hits = scan([p])
            kinds = [h[2] for h in hits]
            ok = any(k.startswith(expect) for k in kinds)
            print(f"  [{'PASS' if ok else 'FAIL'}] {expect:<24} {fn}"
                  + ("" if ok else f"  -> detected instead: {kinds or 'nothing'}"))
            failures += 0 if ok else 1

        # A clean file must NOT trip the scanner.
        p = os.path.join(td, "clean.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("ANTHROPIC_API_KEY=\nmodel = 'claude-haiku-4-5-20251001'\n"
                    "placeholder: sk-ant-...\n")
        hits = scan([p])
        ok = not hits
        print(f"  [{'PASS' if ok else 'FAIL'}] no-false-positive        clean.txt"
              + ("" if ok else f"  -> {hits}"))
        failures += 0 if ok else 1

    if failures:
        print(f"\nself-test FAILED: {failures} case(s). The scanner is not trustworthy.")
        return 2
    print("self-test passed: the scanner can detect every shape it claims to.\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail the build on committed secrets.")
    ap.add_argument("paths", nargs="*", default=None)
    ap.add_argument("--self-test", action="store_true",
                    help="prove the scanner still detects each pattern, then exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    roots = args.paths or ["."]
    findings = scan(roots)

    if not findings:
        print("secret scan: clean — no credential shapes found.")
        return 0

    print("secret scan: FAILED\n")
    for path, lineno, kind, masked in findings:
        print(f"  {path}:{lineno}: {kind}: {masked}")
    print(f"\n{len(findings)} potential secret(s) found.")
    print("Revoke anything real before removing it from the tree — deleting the")
    print("line does not un-leak the key. For a documented placeholder, add the")
    print(f"marker '{ALLOW_MARKER}' on that line with a reason.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
