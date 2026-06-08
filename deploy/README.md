# Deploy

**GitHub (recommended):** push to `main` — CI builds Docker images via
`.github/workflows/ci.yml`. Registry publish uses GitHub Secrets
(`DOCKER_USERNAME`, `DOCKER_PASSWORD`); no API keys belong in the repo.

**Local systemd** unit files for APEX services. Install:

```bash
# Replace %U with your username in each file, then:
sudo cp deploy/apex-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now apex-scheduler
sudo systemctl enable --now apex-discord-bot
sudo systemctl enable --now apex-dashboard

# Log rotation is handled by journald by default.
# To check status:
systemctl status apex-*
```
