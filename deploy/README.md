# Deploy

Systemd unit files for APEX services. Install:

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
