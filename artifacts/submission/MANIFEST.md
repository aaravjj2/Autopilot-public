# APEX Autopilot — Submission Artifact Package

Generated: 2026-05-28T21:29:03Z

## Contents

| Path | Description |
|------|-------------|
| `APEX_Autopilot_Demo.mp4` | Product walkthrough (MP4, if ffmpeg available) |
| `APEX_Autopilot_Demo.webm` | Product walkthrough (Playwright recording) |
| `screenshots/` | UI captures (overview, arb radar, autopilot, risk, …) |
| `api-health.json` | Live `/health` response |
| `api-arb-sample.json` | Arb opportunity count + sample rows |
| `api-proposals-sample.json` | Proposals count + sample |
| `pitch/` | PDF, PPTX, HTML deck, spoken brief |
| `SUBMISSION_COPY.md` | Devpost form text |
| `DEMO_SCRIPT.md` | Narration script for video |

## Upload checklist (Devpost)

1. **Video demo link** — upload `APEX_Autopilot_Demo.mp4` to YouTube/Drive or host raw MP4
2. **Image gallery** — use `screenshots/01-overview.png`, `02-arb-radar.png`, `04-autopilot.png` (3:2 crop if needed)
3. **Try it out** — https://github.com/aaravjj2/Autopilot-public
4. **Built with** — see `SUBMISSION_COPY.md`

## Regenerate

```bash
bash start_all.sh
bash scripts/build_submission_artifacts.sh
```
