#!/usr/bin/env bash
# Setup Git Authentication for Autopilot
# Run this to complete git push setup

echo "=== Autopilot Git Auth Setup ==="
echo ""
echo "Step 1: Add your SSH public key to GitHub"
echo "  Your public key is at: ~/.ssh/id_ed25519.pub"
echo "  Contents:"
cat ~/.ssh/id_ed25519.pub
echo ""
echo "  Go to: https://github.com/settings/keys"
echo "  Click 'New SSH Key' and paste the above."
echo ""
echo "Step 2: Test the SSH connection:"
echo "  ssh -T git@github.com"
echo ""
echo "Step 3: Once authenticated, push all unsynced commits:"
echo "  cd /home/aarav/Aarav/Autopilot"
echo "  git push origin main --tags"
echo ""
echo "=== After push, verify tags are visible at: ==="
echo "  https://github.com/aaravjj2/Autopilot-public/tags"
