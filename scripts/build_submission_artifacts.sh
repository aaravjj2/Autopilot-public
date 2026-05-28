#!/usr/bin/env bash
# Build hackathon/submission artifact package: screenshots, API proofs, pitch assets, video.
set -euo pipefail

APEX_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ART="$APEX_DIR/artifacts/submission"
FRONTEND="$APEX_DIR/autopilot-local/frontend"
PYTHON="${APEX_PYTHON:-python}"

log() { echo "[submission] $*"; }

mkdir -p "$ART/screenshots" "$ART/video" "$ART/pitch" "$ART/docs"

log "Recording demo (Playwright video + screenshots)..."
cd "$FRONTEND"
APEX_PYTHON="$PYTHON" npx playwright test \
  --config=playwright.demo.config.ts \
  --project=demo

# Playwright writes video under test-results; copy newest webm to package root
VIDEO_SRC="$(find "$ART/video" "$FRONTEND/test-results" -name '*.webm' -type f 2>/dev/null | head -1 || true)"
if [[ -n "${VIDEO_SRC:-}" ]]; then
  cp "$VIDEO_SRC" "$ART/APEX_Autopilot_Demo.webm"
  log "WebM demo: $ART/APEX_Autopilot_Demo.webm"
  if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -i "$ART/APEX_Autopilot_Demo.webm" \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$ART/APEX_Autopilot_Demo.mp4" 2>/dev/null \
    && log "MP4 demo: $ART/APEX_Autopilot_Demo.mp4" \
    || log "WARN: ffmpeg MP4 conversion failed (WebM still included)"
  fi
else
  log "WARN: No .webm found — run demo test manually"
fi

log "Copying pitch assets..."
for f in \
  "$APEX_DIR/APEX_Autopilot_Pitch_Deck.pdf" \
  "$APEX_DIR/APEX_Autopilot_Pitch_Deck.pptx" \
  "$APEX_DIR/presentation.html" \
  "$APEX_DIR/docs/pitch/APEX_Autopilot_Pitch_Brief_and_Speech.md"; do
  [[ -f "$f" ]] && cp "$f" "$ART/pitch/" || true
done

log "Writing manifest..."
cat > "$ART/MANIFEST.md" <<EOF
# APEX Autopilot — Submission Artifact Package

Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Contents

| Path | Description |
|------|-------------|
| \`APEX_Autopilot_Demo.mp4\` | Product walkthrough (MP4, if ffmpeg available) |
| \`APEX_Autopilot_Demo.webm\` | Product walkthrough (Playwright recording) |
| \`screenshots/\` | UI captures (overview, arb radar, autopilot, risk, …) |
| \`api-health.json\` | Live \`/health\` response |
| \`api-arb-sample.json\` | Arb opportunity count + sample rows |
| \`api-proposals-sample.json\` | Proposals count + sample |
| \`pitch/\` | PDF, PPTX, HTML deck, spoken brief |
| \`SUBMISSION_COPY.md\` | Devpost form text |
| \`DEMO_SCRIPT.md\` | Narration script for video |

## Upload checklist (Devpost)

1. **Video demo link** — upload \`APEX_Autopilot_Demo.mp4\` to YouTube/Drive or host raw MP4
2. **Image gallery** — use \`screenshots/01-overview.png\`, \`02-arb-radar.png\`, \`04-autopilot.png\` (3:2 crop if needed)
3. **Try it out** — https://github.com/aaravjj2/Autopilot-public
4. **Built with** — see \`SUBMISSION_COPY.md\`

## Regenerate

\`\`\`bash
bash start_all.sh
bash scripts/build_submission_artifacts.sh
\`\`\`
EOF

# Zip for one-click upload
ZIP="$APEX_DIR/APEX_Autopilot_Submission_Artifacts.zip"
rm -f "$ZIP"
(cd "$APEX_DIR/artifacts" && zip -r "$ZIP" submission -x 'submission/video/test-results/*')
log "Zip: $ZIP"
log "Done."
