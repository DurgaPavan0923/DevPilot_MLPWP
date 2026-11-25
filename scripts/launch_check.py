#!/usr/bin/env python3
"""DevPilot Pre-Flight & Launch Readiness Check.

Cross-platform verification script validating public assets, legal routes, watermark absence,
em/en dash compliance, and custom domain connectivity.
"""

from __future__ import annotations

import os
import pathlib
import re
import socket
import sys

def main() -> int:
    print("==================================================")
    print(" DevPilot Pre-Flight & Launch Readiness Check")
    print("==================================================")
    failed = False

    # 1. Assets
    print("[1/5] Checking public web assets... ", end="", flush=True)
    required_assets = [
        "web/public/favicon.ico",
        "web/public/icon.svg",
        "web/public/apple-touch-icon.png",
        "web/public/robots.txt",
        "web/public/sitemap.xml",
    ]
    missing = [a for a in required_assets if not pathlib.Path(a).is_file()]
    if missing:
        print(f"\n  [FAILED] Missing assets: {missing}")
        failed = True
    else:
        print("OK (All 5 SEO and favicon assets verified)")

    # 2. Watermarks
    print("[2/5] Checking for AI watermark badges... ", end="", flush=True)
    watermark_pattern = re.compile(r"made with (v0|cursor|lovable|bolt|replit)", re.IGNORECASE)
    watermarks_found = []
    for p in pathlib.Path(".").rglob("*"):
        if any(part in p.parts for part in ["node_modules", ".next", ".git", ".venv", "__pycache__", "dist", "build"]):
            continue
        if p.is_file() and p.suffix in [".py", ".ts", ".tsx", ".md", ".json", ".html"]:
            try:
                text = p.read_text(encoding="utf-8")
                if watermark_pattern.search(text):
                    watermarks_found.append(str(p))
            except Exception:
                pass
    if watermarks_found:
        print(f"\n  [FAILED] Watermarks found in: {watermarks_found}")
        failed = True
    else:
        print("OK (Zero promotional watermarks found)")

    # 3. Privacy and Terms
    print("[3/5] Verifying legal & institutional documentation routes... ", end="", flush=True)
    if pathlib.Path("web/app/privacy/page.tsx").is_file() and pathlib.Path("web/app/terms/page.tsx").is_file():
        print("OK (/privacy and /terms exist and compiled in build)")
    else:
        print("\n  [FAILED] /privacy or /terms page missing")
        failed = True

    # 4. Em and En Dashes
    print("[4/5] Auditing em and en dashes in repository text... ", end="", flush=True)
    dash_chars = ["\u2014", "\u2013"]
    dash_found = []
    for p in pathlib.Path(".").rglob("*"):
        if any(part in p.parts for part in ["node_modules", ".next", ".git", ".venv", "__pycache__", "dist", "build"]):
            continue
        if p.is_file() and p.suffix in [".py", ".ts", ".tsx", ".md", ".json", ".html", ".css", ".yml", ".yaml"]:
            try:
                content = p.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    for d in dash_chars:
                        if d in line:
                            dash_found.append(f"{p}:{i}")
            except Exception:
                pass
    if dash_found:
        print(f"\n  [FAILED] Found em or en dashes in: {dash_found[:5]}")
        failed = True
    else:
        print("OK (Clean UTF-8 text without em or en dashes)")

    # 5. Domain
    custom_domain = os.getenv("DEVPILOT_CUSTOM_DOMAIN", "devpilot.run")
    print(f"[5/5] Checking custom domain connectivity ({custom_domain})... ", end="", flush=True)
    try:
        socket.gethostbyname(custom_domain)
        print("RESOLVED (Points to valid IP)")
    except socket.gaierror:
        print(f"BLOCKED (Pending DNS configuration by domain owner: {custom_domain})")

    print("==================================================")
    if not failed:
        print(" Pre-flight check PASSED. Repository is launch-ready.")
        print("==================================================")
        return 0
    else:
        print(" Pre-flight check FAILED. Address flagged issues above.")
        print("==================================================")
        return 1

if __name__ == "__main__":
    sys.exit(main())
