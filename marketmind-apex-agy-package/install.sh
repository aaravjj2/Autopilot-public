#!/usr/bin/env bash
# install.sh — Install MarketMind × APEX Antigravity package
# Usage: bash install.sh [path/to/Autopilot-main]

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Installing MarketMind × APEX Antigravity package"
echo "   Source : $SCRIPT_DIR"
echo "   Target : $PROJECT_DIR"
echo ""

# Verify target looks like the APEX project
if [ ! -f "$PROJECT_DIR/src/apex/main.py" ] && [ ! -f "$PROJECT_DIR/README.md" ]; then
    echo "⚠  Warning: target directory doesn't look like an APEX project."
    echo "   Expected to find src/apex/main.py. Proceeding anyway."
fi

# Copy .agent/ folder
echo "📁 Copying .agent/ package..."
cp -r "$SCRIPT_DIR/.agent" "$PROJECT_DIR/"
echo "   ✓ .agent/agents/agents.md"
echo "   ✓ .agent/skills/ (8 skills)"
echo "   ✓ .agent/rules/ (3 rules)"
echo "   ✓ .agent/workflows/ (5 workflows)"

# For Claude Code compatibility: also copy to .claude/skills/
if command -v claude &>/dev/null; then
    echo ""
    echo "🔧 Claude Code detected — installing to .claude/skills/ as well..."
    mkdir -p "$PROJECT_DIR/.claude/skills"
    for skill_dir in "$SCRIPT_DIR/.agent/skills"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$PROJECT_DIR/.claude/skills/$skill_name"
    done
    echo "   ✓ .claude/skills/ synced"
fi

# For Gemini CLI compatibility
if command -v gemini &>/dev/null; then
    echo ""
    echo "🔧 Gemini CLI detected — installing to .gemini/skills/ as well..."
    mkdir -p "$PROJECT_DIR/.gemini/skills"
    for skill_dir in "$SCRIPT_DIR/.agent/skills"/*/; do
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$PROJECT_DIR/.gemini/skills/$skill_name"
    done
    echo "   ✓ .gemini/skills/ synced"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. cd $PROJECT_DIR"
echo "  2. agy                        # start Antigravity CLI"
echo "  3. /health-check              # verify your environment"
echo "  4. /build-arb-layer           # scaffold the full arb pipeline"
echo "  5. /add-thesis-stream         # add Claude streaming thesis"
echo "  6. /run-backtest              # build backtest analytics"
echo ""
echo "Skills available: apex-dev, arb-engine, kalshi-api, thesis-card,"
echo "                  risk-stack, backtest, frontend-arb, polymarket"
