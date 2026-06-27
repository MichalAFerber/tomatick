#!/usr/bin/env bash
#
# Build Tomatick, package a drag-to-Applications .dmg, and cut a GitHub release.
#
# Usage:
#   ./scripts/release.sh            # version read from tomatick/__init__.py, tag v<version>
#   ./scripts/release.sh --dry-run  # build + dmg only, skip the GitHub release
#
# Prereqs: a venv with deps installed (python3.12 -m venv venv && pip install -r
# requirements.txt) and an authenticated gh CLI (gh auth status). The build is
# arm64 — run it on an Apple Silicon Mac.

set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# --- single source of truth: version from tomatick/__init__.py -------------
VER=$(grep -E '^__version__' tomatick/__init__.py | sed -E 's/.*"([^"]+)".*/\1/')
if [[ -z "$VER" ]]; then
  echo "error: could not read __version__ from tomatick/__init__.py" >&2
  exit 1
fi
TAG="v$VER"
DMG="dist/Tomatick-$VER.dmg"
echo "==> Releasing Tomatick $VER (tag $TAG)"

# --- activate venv ---------------------------------------------------------
if [[ -f venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "error: ./venv not found. Create it with:" >&2
  echo "       python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

# --- guard: release must not already exist ---------------------------------
if [[ $DRY_RUN -eq 0 ]] && gh release view "$TAG" >/dev/null 2>&1; then
  echo "error: release $TAG already exists. Bump the version in tomatick/__init__.py first." >&2
  exit 1
fi

# --- build the .app --------------------------------------------------------
echo "==> Building app bundle (py2app)..."
rm -rf build dist
python setup.py py2app >/tmp/tomatick-py2app.log 2>&1 || {
  echo "build failed; tail of log:" >&2; tail -25 /tmp/tomatick-py2app.log >&2; exit 1; }
codesign -v dist/Tomatick.app
ARCH=$(file -b dist/Tomatick.app/Contents/MacOS/Tomatick)
echo "    built: $ARCH"

# --- build the .dmg (app + Applications symlink) ---------------------------
echo "==> Packaging $DMG..."
STAGE=$(mktemp -d)
cp -R dist/Tomatick.app "$STAGE/Tomatick.app"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "Tomatick $VER" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"
SHA=$(shasum -a 256 "$DMG" | awk '{print $1}')
echo "    $(ls -lh "$DMG" | awk '{print $5}')  sha256=$SHA"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "==> --dry-run: skipping GitHub release. Artifact ready at $DMG"
  exit 0
fi

# --- cut the GitHub release ------------------------------------------------
echo "==> Creating GitHub release $TAG..."
NOTES=$(cat <<EOF
Tomatick $VER — a macOS menu bar timer, stopwatch, pomodoro, and alarm with timestamped SQLite history.

## Install
1. Download **Tomatick-$VER.dmg** below.
2. Open it and drag **Tomatick** onto **Applications**.
3. First launch only: right-click **Tomatick** in Applications → **Open** → **Open** (the bundle is unsigned). If macOS still refuses:
   \`\`\`bash
   xattr -dr com.apple.quarantine /Applications/Tomatick.app
   \`\`\`

It's a **menu bar** app — no Dock icon. Look for the stopwatch icon in the top-right menu bar.

## Requirements
- **Apple Silicon** (M1/M2/M3/M4) — the build bundles an arm64 Python and won't run on Intel Macs.

## Notes
- Unsigned / not notarized (hence the one-time Gatekeeper bypass above).
- \`SHA-256\` (Tomatick-$VER.dmg): \`$SHA\`
EOF
)

gh release create "$TAG" \
  "$DMG" \
  --title "Tomatick $VER" \
  --target main \
  --notes "$NOTES"

echo "==> Done: $(gh release view "$TAG" --json url -q .url)"
