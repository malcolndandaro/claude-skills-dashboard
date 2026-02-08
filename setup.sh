#!/usr/bin/env bash
#
# Claude Skills Dashboard - One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/malcolndandaro/claude-skills-dashboard/main/setup.sh | bash
#
# What this script does:
#   1. Checks prerequisites (Python 3.10+, jq, pip)
#   2. Prompts whether to install at user level or project level
#   3. Installs the skill tracking hook into the chosen settings.json
#   4. Installs the claude-skills-dashboard Python package from GitHub
#

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
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

# ─── 2. Choose install scope ─────────────────────────────────────────────────

echo -e "${BOLD}Where should the tracker be installed?${NC}"
echo ""
echo -e "  ${BOLD}1)${NC} User level   ${DIM}~/.claude/settings.json${NC}"
echo -e "     Tracks skill usage across ${BOLD}all${NC} projects."
echo -e "     Log: ${DIM}~/.claude/skill-tracking.jsonl${NC}"
echo ""
echo -e "  ${BOLD}2)${NC} Project level ${DIM}.claude/settings.json${NC}"
echo -e "     Tracks skill usage for the ${BOLD}current project only${NC}."
echo -e "     Log: ${DIM}.claude/skill-tracking.jsonl${NC}"
echo ""

# Read choice — handle both piped (curl | bash) and interactive usage
if [ -t 0 ]; then
    # Interactive terminal
    while true; do
        echo -n -e "Enter choice ${DIM}[1/2, default: 1]${NC}: "
        read -r SCOPE_CHOICE
        SCOPE_CHOICE="${SCOPE_CHOICE:-1}"
        case "$SCOPE_CHOICE" in
            1|2) break ;;
            *) echo -e "${RED}Please enter 1 or 2.${NC}" ;;
        esac
    done
else
    # Non-interactive (piped) — use /dev/tty for prompting
    if [ -e /dev/tty ]; then
        while true; do
            echo -n -e "Enter choice ${DIM}[1/2, default: 1]${NC}: "
            read -r SCOPE_CHOICE < /dev/tty
            SCOPE_CHOICE="${SCOPE_CHOICE:-1}"
            case "$SCOPE_CHOICE" in
                1|2) break ;;
                *) echo -e "${RED}Please enter 1 or 2.${NC}" ;;
            esac
        done
    else
        # No tty available at all — default to user level
        SCOPE_CHOICE=1
        info "No interactive terminal detected, defaulting to user level."
    fi
fi

echo ""

if [ "$SCOPE_CHOICE" = "2" ]; then
    INSTALL_SCOPE="project"
    CLAUDE_DIR=".claude"
    SETTINGS_FILE="$CLAUDE_DIR/settings.json"
    TRACKING_FILE="$CLAUDE_DIR/skill-tracking.jsonl"
    TRACKING_PATH='.claude/skill-tracking.jsonl'
    info "Installing at project level ($(pwd))"
else
    INSTALL_SCOPE="user"
    CLAUDE_DIR="$HOME/.claude"
    SETTINGS_FILE="$CLAUDE_DIR/settings.json"
    TRACKING_FILE="$CLAUDE_DIR/skill-tracking.jsonl"
    TRACKING_PATH='~/.claude/skill-tracking.jsonl'
    info "Installing at user level"
fi

echo ""

# ─── 3. Install the skill tracking hook ──────────────────────────────────────

# Build hook JSON with a placeholder, then substitute the tracking path.
# Using a quoted heredoc avoids any bash expansion inside the JSON.
HOOK_JSON=$(cat <<'HOOKEOF'
{
    "matcher": "",
    "hooks": [{
        "type": "command",
        "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> __TRACKING_PATH__"
    }]
}
HOOKEOF
)
HOOK_JSON="${HOOK_JSON//__TRACKING_PATH__/$TRACKING_PATH}"

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
            "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> __TRACKING_PATH__"
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF
    # Substitute the tracking path into the generated file
    sed -i "s|__TRACKING_PATH__|$TRACKING_PATH|g" "$SETTINGS_FILE"
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

# ─── 4. Install the dashboard Python package ─────────────────────────────────

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
echo -e "  Scope:          ${BOLD}$INSTALL_SCOPE${NC}"
echo "  Tracking file:  $TRACKING_FILE"
echo "  Settings file:  $SETTINGS_FILE"
echo ""
echo "  Run the dashboard:"
echo -e "    ${BOLD}claude-skills-dashboard${NC}"
echo ""
if [ "$INSTALL_SCOPE" = "project" ]; then
    echo -e "  ${DIM}Tip: The dashboard auto-discovers project-level tracking files."
    echo -e "  You can also point it at a specific file:${NC}"
    echo -e "    ${BOLD}claude-skills-dashboard --file $TRACKING_FILE${NC}"
    echo ""
    echo -e "  ${DIM}Consider adding .claude/skill-tracking.jsonl to .gitignore.${NC}"
    echo ""
fi
echo "  The tracker hook will automatically log skill usage"
echo "  every time Claude Code invokes a skill."
echo ""
