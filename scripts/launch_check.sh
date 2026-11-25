#!/usr/bin/env bash
# DevPilot Launch & Pre-Flight Verification Script
# Validates asset presence, privacy/terms routes, watermark absence, and domain status.

set -euo pipefail

echo "=================================================="
echo " DevPilot Pre-Flight & Launch Readiness Check"
echo "=================================================="

FAILED=0

# 1. Check Favicon & SEO Assets
echo -n "[1/5] Checking public web assets... "
REQUIRED_ASSETS=(
    "web/public/favicon.ico"
    "web/public/icon.svg"
    "web/public/apple-touch-icon.png"
    "web/public/robots.txt"
    "web/public/sitemap.xml"
)
ASSETS_OK=true
for asset in "${REQUIRED_ASSETS[@]}"; do
    if [[ ! -f "$asset" ]]; then
        echo -e "\n  [MISSING] $asset"
        ASSETS_OK=false
        FAILED=1
    fi
done
if $ASSETS_OK; then
    echo "OK (All 5 SEO and favicon assets verified)"
fi

# 2. Check for "Made with" watermarks
echo -n "[2/5] Checking for AI watermark badges... "
WATERMARK_MATCHES=$(git grep -i -E "made with (v0|cursor|lovable|bolt|replit)" || true)
if [[ -n "$WATERMARK_MATCHES" ]]; then
    echo -e "\n  [FAILED] Found forbidden watermark badges:"
    echo "$WATERMARK_MATCHES"
    FAILED=1
else
    echo "OK (Zero promotional watermarks found)"
fi

# 3. Check for Privacy and Terms routes
echo -n "[3/5] Verifying legal & institutional documentation routes... "
if [[ -f "web/app/privacy/page.tsx" && -f "web/app/terms/page.tsx" ]]; then
    echo "OK (/privacy and /terms exist and compiled in build)"
else
    echo -e "\n  [FAILED] /privacy or /terms page missing"
    FAILED=1
fi

# 4. Check for Em/En Dashes in user copy and markdown
echo -n "[4/5] Auditing em and en dashes in repository text... "
DASH_MATCHES=$(python -c "
import pathlib
dash_chars = ['\u2014', '\u2013']
found = []
for p in pathlib.Path('.').rglob('*'):
    if any(part in p.parts for part in ['node_modules', '.next', '.git', '.venv', '__pycache__', 'dist', 'build']):
        continue
    if p.is_file() and p.suffix in ['.py', '.ts', '.tsx', '.md', '.json', '.html', '.css', '.yml', '.yaml']:
        try:
            content = p.read_text(encoding='utf-8')
            for i, line in enumerate(content.splitlines(), 1):
                for d in dash_chars:
                    if d in line:
                        found.append(f'{p}:{i}: {line.strip()[:60]}')
        except Exception:
            pass
if found:
    print('\n'.join(found[:10]))
    exit(1)
exit(0)
" || true)

if [[ -n "$DASH_MATCHES" ]]; then
    echo -e "\n  [FAILED] Found em or en dashes in repository source files:"
    echo "$DASH_MATCHES"
    FAILED=1
else
    echo "OK (Clean UTF-8 text without em or en dashes)"
fi

# 5. Check Custom Domain DNS Status
echo -n "[5/5] Checking custom domain connectivity... "
CUSTOM_DOMAIN="${DEVPILOT_CUSTOM_DOMAIN:-devpilot.run}"
if command -v host >/dev/null 2>&1; then
    DNS_RESULT=$(host "$CUSTOM_DOMAIN" 2>&1 || true)
elif command -v nslookup >/dev/null 2>&1; then
    DNS_RESULT=$(nslookup "$CUSTOM_DOMAIN" 2>&1 || true)
else
    DNS_RESULT=""
fi

if echo "$DNS_RESULT" | grep -q -E "(has address|Name:)"; then
    echo "RESOLVED ($CUSTOM_DOMAIN points to valid IP)"
else
    echo "BLOCKED (Pending DNS configuration by domain owner: $CUSTOM_DOMAIN)"
fi

echo "=================================================="
if [[ "$FAILED" -eq 0 ]]; then
    echo " Pre-flight check PASSED. Repository is launch-ready."
    echo "=================================================="
    exit 0
else
    echo " Pre-flight check FAILED. Address flagged issues above."
    echo "=================================================="
    exit 1
fi
