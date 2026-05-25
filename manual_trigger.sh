#!/bin/bash

echo "===================================================="
echo "       AETHERLENS MANUAL RECAP TRIGGER             "
echo "===================================================="

# 1. Capture Storyboard (20 frames per app, automated scrolling)
echo "[*] Step 1: Starting Automated Capture (20 frames per app)..."
python3 video_analysis/capture_storyboard.py

# 2. Nightly Scoring & Curation (20 -> 7, Gemma Summaries)
echo "[*] Step 2: Starting Gemma-4 Curation & Analysis (20 -> 7)..."
python3 video_analysis/nightly_scoring.py

echo "[+] Recap generation complete!"
echo "[*] Access the dashboard at http://localhost:9080"
echo "===================================================="
