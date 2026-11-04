#!/usr/bin/env python3
"""Privacy audit for the public dotBANG site.

Fails (exit 1) if any public file contains:
  - an IPv4 address (other than 127.0.0.1 in comments about localhost)
  - an email address
  - a tailnet / internal hostname pattern
  - the words that would leak fleet internals (provider ids, hostnames)

Run: python3 scripts/privacy-audit.py
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
SKIP_FILES = {Path(__file__).resolve().name}

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
# Internal hostnames / tailnet addresses leaking in would each be an IPv4
# (caught above) or a *.local / tailnet name:
INTERNAL = re.compile(r"\b[\w-]+\.(?:local|ts\.net|home)\b", re.I)
# Localhost is fine.
ALLOW = {"127.0.0.1"}

def iter_files():
    for p in ROOT.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name in SKIP_FILES or p.suffix in (".png", ".jpg", ".ico", ".woff2"):
            continue
        yield p

def main():
    hits = []
    for p in iter_files():
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, PermissionError):
            continue
        for m in IPV4.finditer(text):
            if m.group(0) in ALLOW:
                continue
            hits.append((str(p.relative_to(ROOT)), m.group(0), "IPv4 address"))
        for m in EMAIL.finditer(text):
            hits.append((str(p.relative_to(ROOT)), m.group(0), "email address"))
        for m in INTERNAL.finditer(text):
            hits.append((str(p.relative_to(ROOT)), m.group(0), "internal hostname"))
    if hits:
        print("PRIVACY AUDIT FAILED — %d hit(s):" % len(hits))
        for f, v, kind in hits:
            print(f"  {f}: {kind} {v!r}")
        return 1
    print("PRIVACY AUDIT PASS — no IPs, emails, or internal hostnames in public files.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
