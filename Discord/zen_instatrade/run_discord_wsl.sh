#!/usr/bin/env bash
# Run the Discord service from a WSL terminal (development)
set -euo pipefail

# Activate project venv if present
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "./.venv/bin/activate" ]; then
  source ./.venv/bin/activate
fi

# Optional: set DISCORD env vars in your shell or use keys.env
# Example: export DISCORD_BOT_TOKEN=...

python run_discord_service.py
