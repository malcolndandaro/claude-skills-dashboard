#!/usr/bin/env bash
#
# Claude Skills Dashboard - One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/malcolndandaro/claude-skills-dashboard/main/setup.sh | bash
#
# What this script does:
#   1. Checks prerequisites (Python 3.10+, pip)
#   2. Installs the claude-skills-dashboard Python package from GitHub
#
# No hooks or configuration needed — the dashboard reads directly from
# Claude Code's session JSONL files in ~/.claude/projects/.
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

echo ""

# ─── 2. Install the dashboard Python package ─────────────────────────────────

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
echo "  Run the dashboard:"
echo -e "    ${BOLD}claude-skills-dashboard${NC}"
echo ""
echo -e "  ${DIM}No hooks or configuration needed.${NC}"
echo -e "  ${DIM}The dashboard reads directly from Claude Code session files.${NC}"
echo ""
