#!/usr/bin/env bash
#
# Claude Skills Dashboard - Hook Installation Script
#
# This script installs a Claude Code hook that tracks skill invocations
# to ~/.claude/skill-tracking.jsonl for the dashboard to display.
#

set -e

CLAUDE_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
TRACKING_FILE="$CLAUDE_DIR/skill-tracking.jsonl"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Claude Skills Dashboard - Hook Installer"
echo "========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Install it with:"
    echo "  macOS:  brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    echo "  Other:  https://stedolan.github.io/jq/download/"
    exit 1
fi

# Create .claude directory if it doesn't exist
if [ ! -d "$CLAUDE_DIR" ]; then
    echo -e "${YELLOW}Creating $CLAUDE_DIR directory...${NC}"
    mkdir -p "$CLAUDE_DIR"
fi

# Create tracking file if it doesn't exist
if [ ! -f "$TRACKING_FILE" ]; then
    echo -e "${YELLOW}Creating tracking file: $TRACKING_FILE${NC}"
    touch "$TRACKING_FILE"
fi

# Define the hook command
HOOK_COMMAND='echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session\":\"$CLAUDE_SESSION_ID\",\"skill\":\"$CLAUDE_SKILL\",\"args\":${CLAUDE_SKILL_ARGS:-null},\"cwd\":\"$PWD\"}" >> ~/.claude/skill-tracking.jsonl'

# Create default settings if file doesn't exist
if [ ! -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}Creating new settings file: $SETTINGS_FILE${NC}"
    cat > "$SETTINGS_FILE" << 'EOF'
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
EOF
    echo -e "${GREEN}Settings file created with skill tracking hook!${NC}"
    exit 0
fi

# Backup existing settings
BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
cp "$SETTINGS_FILE" "$BACKUP_FILE"
echo -e "${YELLOW}Backed up existing settings to: $BACKUP_FILE${NC}"

# Check if hooks.Skill already exists
if jq -e '.hooks.Skill' "$SETTINGS_FILE" > /dev/null 2>&1; then
    # Check if our hook is already installed
    if jq -e '.hooks.Skill[] | select(.hooks[].command | contains("skill-tracking.jsonl"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}Skill tracking hook is already installed!${NC}"
        echo ""
        echo "Current hook configuration:"
        jq '.hooks.Skill' "$SETTINGS_FILE"
        exit 0
    fi

    echo -e "${YELLOW}Adding skill tracking hook to existing Skill hooks...${NC}"

    # Add our hook to existing Skill hooks array
    jq '.hooks.Skill += [{
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> ~/.claude/skill-tracking.jsonl"
        }]
    }]' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
else
    echo -e "${YELLOW}Creating hooks.Skill configuration...${NC}"

    # Check if hooks object exists
    if jq -e '.hooks' "$SETTINGS_FILE" > /dev/null 2>&1; then
        # Add Skill to existing hooks
        jq '.hooks.Skill = [{
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> ~/.claude/skill-tracking.jsonl"
            }]
        }]' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
    else
        # Create hooks object with Skill
        jq '. + {hooks: {Skill: [{
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": "echo \"{\\\"timestamp\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"session\\\":\\\"$CLAUDE_SESSION_ID\\\",\\\"skill\\\":\\\"$CLAUDE_SKILL\\\",\\\"args\\\":${CLAUDE_SKILL_ARGS:-null},\\\"cwd\\\":\\\"$PWD\\\"}\" >> ~/.claude/skill-tracking.jsonl"
            }]
        }]}}' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
    fi
fi

echo ""
echo -e "${GREEN}Skill tracking hook installed successfully!${NC}"
echo ""
echo "The hook will log skill invocations to:"
echo "  $TRACKING_FILE"
echo ""
echo "You can now run the dashboard with:"
echo "  claude-skills-dashboard"
echo ""
echo "To verify the installation, check your settings:"
echo "  cat $SETTINGS_FILE | jq '.hooks.Skill'"
