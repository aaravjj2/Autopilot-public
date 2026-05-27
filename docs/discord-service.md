WSL / Local terminal usage
-------------------------

If you prefer running the Discord process from a WSL terminal (no systemd or container):

1. Open a WSL terminal in the repo root.
2. Ensure your Python venv is activated and environment variables are set (or `Discord/zen_instatrade/keys.env`).
3. Run the helper script:

```bash
cd Discord/zen_instatrade
./run_discord_wsl.sh
```

This starts the FastAPI service and the bot in the foreground on the same process.

Notes
-----
- The systemd unit in `deploy/apex-discord-bot.service` is optional — use it only for system-managed hosts. For local development and WSL, the `run_discord_wsl.sh` script is sufficient.
- Ensure `.env` and `trades.db` remain uncommitted; `.gitignore` has been updated to ignore runtime artifacts.
Discord Bot as a Separate Service

Goal

- Run the Discord bot as an independent service (container or systemd unit) and keep the main APEX backend decoupled.

How it works

- The backend (`backend_api.py`) will proxy any `/discord/*` routes to a dedicated Discord service URL defined by the env var `DISCORD_SERVICE_URL` (e.g. `http://discord-bot:8002`).
- If `DISCORD_SERVICE_URL` is unset, the backend will attempt a legacy local import fallback for backwards compatibility.

Run the bot in Docker Compose (recommended)

- `docker-compose.yml` includes a `discord-bot` service using `Dockerfile.discord`.
- To use the compose-managed bot and let the backend proxy to it, set in your environment or `.env`:

```bash
DISCORD_SERVICE_URL=http://discord-bot:8002
# Optional: allow the local start script to also start the bot (default: disabled)
DISCORD_AUTOSTART=0
```

- Then run:

```bash
docker compose up -d discord-bot
```

Run the bot via systemd (deploy)

- There is a systemd unit at `deploy/apex-discord-bot.service` (already present).
- Enable and start it with:

```bash
sudo cp deploy/apex-discord-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now apex-discord-bot
```

Local (dev) run (opt-in)

- The main start script `start_all.sh` no longer starts the bot by default. To start it along with other services, set `DISCORD_AUTOSTART=1` in your environment or `.env` and run:

```bash
DISCORD_AUTOSTART=1 ./start_all.sh
```

Security and keys

- Keep Discord tokens out of the main `.env`. Use `Discord/zen_instatrade/keys.env` (gitignored) or environment variables in your container/orchestrator.
- If tokens were committed accidentally, rotate them immediately.

Backend configuration

- To point the backend at the running bot service, set `DISCORD_SERVICE_URL` to the bot's base URL.
  Example in `.env` for a compose network:

```env
DISCORD_SERVICE_URL=http://discord-bot:8002
```

Notes

- The backend proxy expects the Discord service to expose the same endpoints previously handled internally:
  - `GET /discord/trades?limit=50`
  - `GET /discord/trades/open`
  - `GET /discord/stats`
  - `GET /discord/brain/stats`
  - `GET /discord/brain/config`

- This change keeps the Discord integration isolated and easier to manage, secure, and scale.
