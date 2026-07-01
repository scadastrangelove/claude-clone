#!/usr/bin/env bash
#
# install.sh — create a second, independent Claude Desktop instance on macOS
# with its own login/profile, a distinct Dock icon, and native (arm64) execution.
#
# Why this exists: Claude Desktop stores your session in one fixed profile dir,
# so a second window is always the same account. This wraps the *same* signed
# binary with a different profile via the CLAUDE_USER_DATA_DIR env var — no full
# app copy, no re-download. Both instances run side by side.
#
# Usage:
#   ./install.sh                       # defaults: name "Claude Work", badge "W"
#   ./install.sh -n "Claude Alt" -b A  # custom app name + badge letter
#   ./install.sh -n "Claude Work" --copy-settings   # also clone UI prefs
#
# Options:
#   -n NAME            App/instance name (default: "Claude Work")
#   -b LETTER          Badge letter on the icon (default: first letter of NAME)
#   -H HUE             Hue shift 0-255 for the icon background (default: 150)
#   -s PATH            Source Claude.app (default: /Applications/Claude.app)
#   --copy-settings    Copy claude_desktop_config.json (UI prefs) from the main
#                      profile. Never copies login tokens / cookies.
#   -h, --help         Show this help
#
set -euo pipefail

NAME="Claude Work"
BADGE=""
HUE=150
SRC_APP="/Applications/Claude.app"
COPY_SETTINGS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n) NAME="$2"; shift 2;;
    -b) BADGE="$2"; shift 2;;
    -H) HUE="$2"; shift 2;;
    -s) SRC_APP="$2"; shift 2;;
    --copy-settings) COPY_SETTINGS=1; shift;;
    -h|--help) sed -n '2,30p' "$0"; exit 0;;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
done

HERE="$(cd "$(dirname "$0")" && pwd)"
[[ -z "$BADGE" ]] && BADGE="$(echo "${NAME:0:1}" | tr '[:lower:]' '[:upper:]')"

# derive slug / paths (strip a leading "claude-" so we don't get Claude-claude-…)
SLUG="$(echo "$NAME" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')"
SLUG="${SLUG#claude-}"; SLUG="${SLUG:-instance}"
APP="/Applications/${NAME}.app"
PROFILE="$HOME/Library/Application Support/Claude-${SLUG}"
MAIN_PROFILE="$HOME/Library/Application Support/Claude"
BUNDLE_ID="com.anthropic.claudefordesktop.${SLUG}"
REAL_BIN="${SRC_APP}/Contents/MacOS/Claude"

echo "==> Instance : $NAME"
echo "==> Wrapper  : $APP"
echo "==> Profile  : $PROFILE"

[[ -x "$REAL_BIN" ]] || { echo "ERROR: Claude not found at $SRC_APP" >&2; exit 1; }

# --- 1. (re)build the wrapper app bundle -----------------------------------
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
mkdir -p "$PROFILE"

# launcher: force arm64 (avoid the Rosetta trap) + set the isolated profile
cat > "$APP/Contents/MacOS/launcher" <<SH
#!/bin/bash
export CLAUDE_USER_DATA_DIR="$PROFILE"
exec /usr/bin/arch -arm64 "$REAL_BIN" "\$@"
SH
chmod +x "$APP/Contents/MacOS/launcher"

# Info.plist — arch preference is the other half of the Rosetta fix
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>${NAME}</string>
    <key>CFBundleDisplayName</key>     <string>${NAME}</string>
    <key>CFBundleExecutable</key>      <string>launcher</string>
    <key>CFBundleIdentifier</key>      <string>${BUNDLE_ID}</string>
    <key>CFBundleIconFile</key>        <string>app.icns</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>LSMinimumSystemVersion</key>  <string>10.13</string>
    <key>NSHighResolutionCapable</key> <true/>
    <key>LSRequiresNativeExecution</key><true/>
    <key>LSArchitecturePriority</key>  <array><string>arm64</string></array>
</dict>
</plist>
PLIST

# --- 2. distinct Dock icon --------------------------------------------------
if command -v python3 >/dev/null && python3 -c "import PIL" 2>/dev/null; then
  if python3 "$HERE/make-icon.py" \
        --base "${SRC_APP}/Contents/Resources/electron.icns" \
        --out  "$APP/Contents/Resources/app.icns" \
        --hue  "$HUE" --letter "$BADGE"; then
    echo "==> Icon     : hue+${HUE}, badge '${BADGE}'"
  else
    cp "${SRC_APP}/Contents/Resources/electron.icns" "$APP/Contents/Resources/app.icns"
    echo "==> Icon     : icon generation failed, using stock icon"
  fi
else
  cp "${SRC_APP}/Contents/Resources/electron.icns" "$APP/Contents/Resources/app.icns"
  echo "==> Icon     : (no Python/Pillow) using stock icon — see README to add Pillow"
fi

# --- 3. optional: clone UI preferences (never credentials) -----------------
if [[ "$COPY_SETTINGS" == "1" && -f "$MAIN_PROFILE/claude_desktop_config.json" ]]; then
  cp "$MAIN_PROFILE/claude_desktop_config.json" "$PROFILE/claude_desktop_config.json"
  echo "==> Settings : copied claude_desktop_config.json (prefs only)"
fi

# --- 4. register + refresh icon caches -------------------------------------
touch "$APP" "$APP/Contents/Info.plist"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true
rm -rf "$(getconf DARWIN_USER_CACHE_DIR)/com.apple.iconservices.store" 2>/dev/null || true
killall Dock 2>/dev/null || true

cat <<DONE

Done. Launch "$NAME" from Spotlight or /Applications, then sign in with your
second account. It runs alongside your main Claude with its own login.

  Verify it's native (not Rosetta):
    sample "$NAME" 1 | grep 'Code Type'     # expect: ARM64

  Bring over Claude Code session lists (optional):
    ./sync-sessions.sh "$MAIN_PROFILE" "$PROFILE"
DONE
