#!/bin/bash
# Render narration with edge-tts and mux it into the final video.
# Total target duration: ~69s (matches /tmp/aetherlens_final.mp4)
#
# Strategy: render each section separately so timing maps cleanly to clip
# boundaries, then concat with silence padding to match.

set -e
VOICE="${VOICE:-en-US-AndrewMultilingualNeural}"
AUDIO_DIR=/tmp/aetherlens_audio
mkdir -p "$AUDIO_DIR"
rm -f "$AUDIO_DIR"/*.mp3 "$AUDIO_DIR"/*.wav

source venv/bin/activate

render() {
    local name="$1" text="$2"
    edge-tts --voice "$VOICE" --rate "-5%" --text "$text" --write-media "$AUDIO_DIR/${name}.mp3" 2>/dev/null
    local dur=$(ffprobe -hide_banner -v error -show_entries format=duration -of csv=p=0 "$AUDIO_DIR/${name}.mp3")
    printf "  %-15s %5.2fs  %s\n" "$name" "$dur" "$text"
}

echo "=== Render narration sections (voice=$VOICE) ==="

# Opening slide (target 4s)
render "00_open" \
  "I spend six hours on my phone every day. I can't tell you a single thing I did."

# Album (target 10s)
render "01_album" \
  "AetherLens fixes that. All day, my phone captures one screen every fifteen seconds. By evening — hundreds of them."

# Dedup (target 24s)
render "02_dedup" \
  "Three levels of dedup. First, a pixel hash drops the obvious duplicates as they come in. Then Gemma-4 takes over for the borderline cases — same screen, or just a similar layout? At the end of the day, Gemma-4 picks the most diverse moments from each app, and writes a one-sentence summary."

# Storyboard (target 15s)
render "03_storyboard" \
  "Your day, distilled. Seven curated highlights per app. Each one with a real Gemma-4 caption — written by the model itself, not a template."

# Settings (target 12s)
render "04_settings" \
  "Two-point-four gigabytes of Gemma-4-E2B — the fastest model in the family that fits on a phone. No cloud. No upload. No analytics."

# Closing (target 3s)
render "05_close" \
  "Just the phone in your pocket."

echo ""
echo "=== Pad each clip with silence to match video segment durations ==="
# Targets (in seconds, must match build_final_video.sh)
declare -A TARGETS=(
  [00_open]=4
  [01_album]=10.566667
  [02_dedup]=24.066667
  [03_storyboard]=15.166667
  [04_settings]=12.2
  [05_close]=3
)

for key in 00_open 01_album 02_dedup 03_storyboard 04_settings 05_close; do
  audio="$AUDIO_DIR/${key}.mp3"
  target="${TARGETS[$key]}"
  cur=$(ffprobe -hide_banner -v error -show_entries format=duration -of csv=p=0 "$audio")
  # If audio longer than target, speed-up gently with atempo
  is_longer=$(awk -v a="$cur" -v t="$target" 'BEGIN { print (a > t) ? 1 : 0 }')
  if [ "$is_longer" = "1" ]; then
    ratio=$(awk -v a="$cur" -v t="$target" 'BEGIN { printf "%.4f", a / t }')
    echo "  $key: $cur s -> speed up x$ratio to fit ${target}s"
    ffmpeg -hide_banner -loglevel error -i "$audio" \
      -filter:a "atempo=$ratio" \
      "$AUDIO_DIR/${key}_fit.mp3" -y
  else
    # Shorter -> append silence at the end
    pad=$(awk -v a="$cur" -v t="$target" 'BEGIN { printf "%.4f", t - a }')
    echo "  $key: $cur s -> pad ${pad}s of silence to reach ${target}s"
    ffmpeg -hide_banner -loglevel error -i "$audio" \
      -af "apad=pad_dur=${pad}" -t "$target" \
      "$AUDIO_DIR/${key}_fit.mp3" -y
  fi
done

echo ""
echo "=== Concat all fitted audio to one MP3 ==="
LIST=$(mktemp)
for key in 00_open 01_album 02_dedup 03_storyboard 04_settings 05_close; do
  echo "file '$AUDIO_DIR/${key}_fit.mp3'" >> "$LIST"
done
ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" -c copy /tmp/aetherlens_narration.mp3 -y
rm "$LIST"

NARR_DUR=$(ffprobe -hide_banner -v error -show_entries format=duration -of csv=p=0 /tmp/aetherlens_narration.mp3)
echo "Narration duration: ${NARR_DUR}s"

echo ""
echo "=== Mux narration onto video ==="
ffmpeg -hide_banner -loglevel error \
  -i /tmp/aetherlens_final.mp4 -i /tmp/aetherlens_narration.mp3 \
  -c:v copy -c:a aac -b:a 192k -shortest \
  /tmp/aetherlens_final_voiced.mp4 -y

ls -lh /tmp/aetherlens_final_voiced.mp4
ffprobe -hide_banner /tmp/aetherlens_final_voiced.mp4 2>&1 | grep -E "Duration|Stream"
echo ""
echo "Final voiced video: /tmp/aetherlens_final_voiced.mp4"
