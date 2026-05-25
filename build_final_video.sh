#!/bin/bash
# Assemble the final demo video:
#  opening slide (4s) → Album (10s) → Dedup (24s) → Storyboard (15s) → Settings (12s) → closing slide (3s)
# Then mux edge-tts narration on top.

set -e

SLIDE_OPEN=/tmp/slide_opening.png
SLIDE_CLOSE=/tmp/slide_closing.png
SEG_ALBUM=/tmp/aetherlens_segments/02_album.mp4
SEG_DEDUP=/tmp/dedup_explainer.mp4
SEG_STORY=/tmp/aetherlens_segments/01_scroll.mp4
SEG_SETTINGS=/tmp/aetherlens_segments/03_settings.mp4

OUT_DIR=/tmp/aetherlens_final
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.mp4

echo "=== Convert opening slide to 4s MP4 (silent, 30fps, h264) ==="
ffmpeg -hide_banner -loglevel error \
  -loop 1 -i "$SLIDE_OPEN" -t 4 \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
  "$OUT_DIR/00_open.mp4" -y

echo "=== Convert closing slide to 3s MP4 ==="
ffmpeg -hide_banner -loglevel error \
  -loop 1 -i "$SLIDE_CLOSE" -t 3 \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
  "$OUT_DIR/05_close.mp4" -y

echo "=== Re-encode every clip to consistent 30fps + same codec params ==="
for spec in \
  "01_album:$SEG_ALBUM" \
  "02_dedup:$SEG_DEDUP" \
  "03_storyboard:$SEG_STORY" \
  "04_settings:$SEG_SETTINGS"
do
  name="${spec%%:*}"
  src="${spec#*:}"
  ffmpeg -hide_banner -loglevel error -i "$src" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -an \
    "$OUT_DIR/${name}.mp4" -y
done

echo ""
echo "=== Segment durations ==="
for f in "$OUT_DIR"/*.mp4; do
  d=$(ffprobe -hide_banner -v error -show_entries format=duration -of csv=p=0 "$f")
  printf "  %-25s %s s\n" "$(basename $f)" "$d"
done

echo ""
echo "=== Concat into final ==="
LIST=$(mktemp)
for f in $(ls "$OUT_DIR"/*.mp4 | sort); do
  echo "file '$f'" >> "$LIST"
done
ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" -c copy \
  /tmp/aetherlens_final.mp4 -y
rm "$LIST"

ls -lh /tmp/aetherlens_final.mp4
ffprobe -hide_banner /tmp/aetherlens_final.mp4 2>&1 | grep -E "Duration|Stream #0:0"
echo ""
echo "Final video (no audio yet): /tmp/aetherlens_final.mp4"
