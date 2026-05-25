#!/bin/bash
# Voice-aligned final video using ElevenLabs (George, eleven_v3).
# Mirrors build_voiced_video.sh but routes TTS through ElevenLabs HTTP API.

set -e

SLIDE_OPEN=/tmp/slide_opening.png
SLIDE_CLOSE=/tmp/slide_closing.png
SEG_ALBUM=/tmp/aetherlens_segments/02_album_trimmed.mp4
SEG_DEDUP=/tmp/dedup_explainer.mp4
SEG_STORY=/tmp/aetherlens_segments/01_scroll.mp4
SEG_SETTINGS=/tmp/aetherlens_segments/03_settings.mp4

DIR=/tmp/aetherlens_voiced_eleven
mkdir -p "$DIR"
rm -f "$DIR"/*

source venv/bin/activate

# === Render narration via ElevenLabs ===
render_eleven() {
    local name="$1" text="$2"
    python3 -c "
import urllib.request, json, sys
api_key = '${ELEVEN_API_KEY}'
voice_id = '${ELEVEN_VOICE_ID:-JBFqnCBsd6RMkjVDRZzb}'
model_id = '${ELEVEN_MODEL_ID:-eleven_v3}'
url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
payload = {
    'text': '''$text''',
    'model_id': model_id,
    'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75},
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'xi-api-key': api_key,
        'Content-Type': 'application/json',
        'accept': 'audio/mpeg',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=120) as r:
    open('$DIR/${name}.mp3', 'wb').write(r.read())
"
    ffprobe -v error -show_entries format=duration -of csv=p=0 "$DIR/${name}.mp3"
}

# Pull API key + voice from env or from ELEVEN_LABS.md
: "${ELEVEN_API_KEY:?Set ELEVEN_API_KEY in your shell before running (never commit it)}"
export ELEVEN_VOICE_ID="${ELEVEN_VOICE_ID:-JBFqnCBsd6RMkjVDRZzb}"
export ELEVEN_MODEL_ID="${ELEVEN_MODEL_ID:-eleven_v3}"

echo "===== ElevenLabs voice=$ELEVEN_VOICE_ID model=$ELEVEN_MODEL_ID ====="

echo ""
echo "[1/3] Render TTS narration"
dur_open=$(render_eleven "00_open"      "AetherLens captures your screen all day through Android'\''s accessibility tree. Then Gemma-4-E2B turns hundreds of screenshots into a curated visual diary — all on your phone. No cloud. No laptop.")
dur_album=$(render_eleven "01_album"    "Just install and forget — it auto-captures one screen every fifteen seconds. By evening, hundreds pile up. This is the Album tab, your raw memory.")
dur_dedup=$(render_eleven "02_dedup"    "Three levels of dedup. As each frame arrives, a pixel hash drops the obvious duplicates. Gemma-4 then catches the borderline cases — same screen, or just a similar layout? At the end of the day, Gemma-4 picks the most diverse moments from each app, and writes a one-sentence summary.")
dur_story=$(render_eleven "03_storyboard" "This is the Storyboard tab — your day, distilled. Seven curated highlights per app, picked by Gemma-4 for diversity. Each one comes with a real Gemma-4 caption, written by the model itself.")
dur_set=$(render_eleven "04_settings"  "In Settings, hit Trigger Manual Recap anytime — or just let it run. Gemma-4-E2B is the fastest model in the family that fits on a phone. No cloud. No laptop. Everything on your phone.")
dur_close=$(render_eleven "05_close"   "Just the phone in your pocket.")

printf "  %-15s %s s\n"  "00_open"      "$dur_open"
printf "  %-15s %s s\n"  "01_album"     "$dur_album"
printf "  %-15s %s s\n"  "02_dedup"     "$dur_dedup"
printf "  %-15s %s s\n"  "03_storyboard" "$dur_story"
printf "  %-15s %s s\n"  "04_settings"  "$dur_set"
printf "  %-15s %s s\n"  "05_close"     "$dur_close"

# === Stitch each segment ===
TAIL=0.4

make_slide_clip() {
    local name="$1" slide="$2" audio_dur="$3"
    local total=$(awk -v a="$audio_dur" -v t="$TAIL" 'BEGIN { printf "%.3f", a + t }')
    ffmpeg -hide_banner -loglevel error \
        -loop 1 -i "$slide" -i "$DIR/${name}.mp3" \
        -filter_complex "[1:a]apad=pad_dur=$TAIL[a]" \
        -map 0:v -map "[a]" \
        -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
        -c:a aac -b:a 192k -ar 48000 \
        -t "$total" \
        "$DIR/${name}.mp4" -y
}

make_clip_voiced() {
    local name="$1" video="$2" audio_dur="$3"
    local video_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video")
    local target=$(awk -v a="$audio_dur" -v v="$video_dur" -v t="$TAIL" 'BEGIN {
        need = a + t
        if (need > v) print need
        else print v
    }')
    local extend=$(awk -v tar="$target" -v v="$video_dur" 'BEGIN {
        e = tar - v
        if (e < 0.05) e = 0
        printf "%.3f", e
    }')
    local audio_pad=$(awk -v tar="$target" -v a="$audio_dur" 'BEGIN {
        p = tar - a
        if (p < 0) p = 0
        printf "%.3f", p
    }')
    printf "  %-15s  video %.2fs  audio %.2fs  -> target %.2fs (+freeze %ss, +silence %ss)\n" \
        "$name" "$video_dur" "$audio_dur" "$target" "$extend" "$audio_pad"

    if (( $(echo "$extend > 0" | bc -l) )); then
        ffmpeg -hide_banner -loglevel error \
            -i "$video" -i "$DIR/${name}.mp3" \
            -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=$extend[v];[1:a]apad=pad_dur=$audio_pad[a]" \
            -map "[v]" -map "[a]" \
            -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
            -c:a aac -b:a 192k -ar 48000 \
            -t "$target" \
            "$DIR/${name}.mp4" -y
    else
        ffmpeg -hide_banner -loglevel error \
            -i "$video" -i "$DIR/${name}.mp3" \
            -filter_complex "[1:a]apad=pad_dur=$audio_pad[a]" \
            -map 0:v -map "[a]" \
            -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
            -c:a aac -b:a 192k -ar 48000 \
            -t "$target" \
            "$DIR/${name}.mp4" -y
    fi
}

echo ""
echo "[2/3] Build voiced clips"
make_slide_clip "00_open"       "$SLIDE_OPEN"   "$dur_open"
make_clip_voiced "01_album"     "$SEG_ALBUM"    "$dur_album"
make_clip_voiced "02_dedup"     "$SEG_DEDUP"    "$dur_dedup"
make_clip_voiced "03_storyboard" "$SEG_STORY"   "$dur_story"
make_clip_voiced "04_settings"  "$SEG_SETTINGS" "$dur_set"
make_slide_clip "05_close"      "$SLIDE_CLOSE"  "$dur_close"

echo ""
echo "[3/3] Concat"
LIST=$(mktemp)
for n in 00_open 01_album 02_dedup 03_storyboard 04_settings 05_close; do
    echo "file '$DIR/${n}.mp4'" >> "$LIST"
done
ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" -c copy \
    /tmp/aetherlens_final_eleven.mp4 -y
rm "$LIST"

echo ""
ls -lh /tmp/aetherlens_final_eleven.mp4
ffprobe -hide_banner /tmp/aetherlens_final_eleven.mp4 2>&1 | grep -E "Duration|Stream"
echo ""
echo "Done: /tmp/aetherlens_final_eleven.mp4"
