#!/usr/bin/env bash
#
# Claude Skills Dashboard - One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/malcolndandaro/claude-skills-dashboard/main/setup.sh | bash
#
# What this script does:
#   1. Checks prerequisites (Python 3.10+, jq, pip)
#   2. Installs the skill tracking hook into ~/.claude/settings.json
#   3. Installs the claude-skills-dashboard Python package from PyPI/GitHub
#

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────

info()    { echo -e "${BLUE}[info]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
ok()      { echo -e "${GREEN}[ok]${NC}    $*"; }
fail()    { echo -e "${RED}[error]${NC} $*"; exit 1; }

# ─── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Claude Skills Dashboard — Installer${NC}"
echo "──────────────────────────────────────"
echo ""

# ─── 1. Check prerequisites ──────────────────────────────────────────────────

info "Checking prerequisites..."

# Python 3.10+
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    fail "Python 3 is required but not found. Install Python 3.10+ and try again."
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python 3.10+ is required (found $PY_VERSION). Please upgrade and try again."
fi
ok "Python $PY_VERSION"

# pip
if ! $PYTHON -m pip --version &>/dev/null; then
    fail "pip is required but not found. Install pip and try again."
fi
ok "pip"

# jq
if ! command -v jq &>/dev/null; then
    fail "jq is required but not found.\n  Install it with:\n    macOS:  brew install jq\n    Ubuntu: sudo apt-get install jq\n    Other:  https://stedolan.github.io/jq/download/"
fi
ok "jq"

echo ""

# ─── 2. Install the skill tracking hook ──────────────────────────────────────

CLAUDE_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
TRACKING_FILE="$CLAUDE_DIR/skill-tracking.jsonl"

HOOK_COMMAND='echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session\":\"$CLAUDE_SESSION_ID\",\"skill\":\"$CLAUDE_SKILL\",\"args\":${CLAUDE_SKILL_ARGS:-null},\"cwd\":\"$PWD\"}" >> ~/.claude/skill-tracking.jsonl'

HOOK_JSON='{
    "matcher": "",
    "hooks": [{
        "type": "command",
        "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> ~/.claude/skill-tracking.jsonl"
    }]
}'

info "Setting up skill tracking hook..."

# Create directories & files
mkdir -p "$CLAUDE_DIR"
[ -f "$TRACKING_FILE" ] || touch "$TRACKING_FILE"

if [ ! -f "$SETTINGS_FILE" ]; then
    # No settings file — create one from scratch
    info "Creating $SETTINGS_FILE"
    cat > "$SETTINGS_FILE" <<'SETTINGS_EOF'
{
  "hooks": {
    "Skill": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> ~/.claude/skill-tracking.jsonl"
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF
    ok "Created settings with skill tracking hook"
else
    # Settings file exists — check if hook is already there
    if jq -e '.hooks.Skill[] | select(.hooks[].command | contains("skill-tracking.jsonl"))' "$SETTINGS_FILE" >/dev/null 2>&1; then
        ok "Skill tracking hook is already installed"
    else
        # Back up existing settings
        BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$SETTINGS_FILE" "$BACKUP_FILE"
        info "Backed up settings to $BACKUP_FILE"

        if jq -e '.hooks.Skill' "$SETTINGS_FILE" >/dev/null 2>&1; then
            # Skill hooks array exists — append
            jq --argjson hook "$HOOK_JSON" '.hooks.Skill += [$hook]' \
                "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
        elif jq -e '.hooks' "$SETTINGS_FILE" >/dev/null 2>&1; then
            # hooks object exists but no Skill key
            jq --argjson hook "$HOOK_JSON" '.hooks.Skill = [$hook]' \
                "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
        else
            # No hooks object at all
            jq --argjson hook "$HOOK_JSON" '. + {hooks: {Skill: [$hook]}}' \
                "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
        fi
        ok "Skill tracking hook added to settings"
    fi
fi

echo ""

# ─── 3. Install the dashboard Python package ─────────────────────────────────

REPO_URL="https://github.com/malcolndandaro/claude-skills-dashboard.git"

info "Installing claude-skills-dashboard..."

$PYTHON -m pip install --quiet "git+${REPO_URL}" 2>&1 | while IFS= read -r line; do
    echo -e "  ${line}"
done

ok "claude-skills-dashboard installed"

echo ""

# ─── Done ─────────────────────────────────────────────────────────────────────

echo "──────────────────────────────────────"
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo "  Tracking file:  $TRACKING_FILE"
echo "  Settings file:  $SETTINGS_FILE"
echo ""
echo "  Run the dashboard:"
echo -e "    ${BOLD}claude-skills-dashboard${NC}"
echo ""
echo "  The tracker hook will automatically log skill usage"
echo "  every time Claude Code invokes a skill."
echo ""
