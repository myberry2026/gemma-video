#!/bin/bash
# Record 3 short segments and concat into final demo.
# Workaround: screenrecord truncates around 20s on Edge 2025 / Android 16
# (even with longer --time-limit), so we keep each segment ≤16s.

set -e
TARGET="${1:-ZA2232T6XT}"
ADB="adb -s $TARGET"
OUT_DIR=/tmp/aetherlens_segments
FINAL=/tmp/aetherlens_demo_full.mp4
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.mp4 "$FINAL"

# Coordinates
TAB_STORY=(203 2566); TAB_SETTINGS=(1017 2566)
AMAZON_THUMB=(234 1059)
CLOSE_PREVIEW=(180 124)
MID_X=610

# 60Hz workaround
$ADB shell "settings put system peak_refresh_rate 60.0"
$ADB shell "settings put system min_refresh_rate 60.0"
$ADB shell "settings put system show_touches 1" || true
$ADB shell "svc power stayon usb"

# Reset to a known state
$ADB shell "am force-stop com.gemma.videomemory"
sleep 1
$ADB shell "am start -n com.gemma.videomemory/.MainActivity" > /dev/null
sleep 3
$ADB shell "am start-foreground-service -n com.gemma.videomemory/.llm.LlmService" > /dev/null
sleep 1
$ADB shell "input tap ${TAB_STORY[0]} ${TAB_STORY[1]}"
sleep 1.5

record_segment() {
    local name="$1"
    local seconds="$2"
    shift 2
    local actions="$@"

    echo ""
    echo "=== Segment $name (${seconds}s) ==="
    $ADB shell "rm -f /sdcard/seg.mp4"
    $ADB shell "screenrecord --time-limit $seconds --bit-rate 8000000 /sdcard/seg.mp4" &
    local pid=$!
    sleep 0.5
    # Run actions function name
    "$actions"
    wait $pid
    $ADB pull /sdcard/seg.mp4 "$OUT_DIR/$name.mp4"
}

# --- Segment 1: scroll through all apps (~16s) ---
segment_a() {
    sleep 2
    # scroll down 4x
    $ADB shell "input swipe $MID_X 2200 $MID_X 1000 1000"
    sleep 1.2
    $ADB shell "input swipe $MID_X 2200 $MID_X 1000 1000"
    sleep 1.2
    $ADB shell "input swipe $MID_X 2200 $MID_X 1000 1000"
    sleep 1.2
    $ADB shell "input swipe $MID_X 2200 $MID_X 1000 1000"
    sleep 1.5
    # scroll back up
    $ADB shell "input swipe $MID_X 1000 $MID_X 2200 500"
    sleep 0.6
    $ADB shell "input swipe $MID_X 1000 $MID_X 2200 500"
    sleep 0.6
    $ADB shell "input swipe $MID_X 1000 $MID_X 2200 500"
    sleep 1.5
}
record_segment "01_scroll" 16 segment_a

# --- Segment 2: fullscreen preview (~10s) ---
segment_b() {
    sleep 1
    $ADB shell "input tap ${AMAZON_THUMB[0]} ${AMAZON_THUMB[1]}"
    sleep 4
    $ADB shell "input tap ${CLOSE_PREVIEW[0]} ${CLOSE_PREVIEW[1]}"
    sleep 2
}
record_segment "02_fullscreen" 10 segment_b

# --- Segment 3: Settings tab (~14s) ---
segment_c() {
    sleep 1
    $ADB shell "input tap ${TAB_SETTINGS[0]} ${TAB_SETTINGS[1]}"
    sleep 3
    $ADB shell "input swipe $MID_X 2000 $MID_X 1000 800"
    sleep 3
    $ADB shell "input swipe $MID_X 2000 $MID_X 1000 800"
    sleep 3
    # back to storyboard
    $ADB shell "input tap ${TAB_STORY[0]} ${TAB_STORY[1]}"
    sleep 2
}
record_segment "03_settings" 14 segment_c

$ADB shell "settings put system show_touches 0" || true

# --- Concat ---
echo ""
echo "=== Concat segments ==="
LIST=$(mktemp)
for f in "$OUT_DIR"/*.mp4; do
    echo "file '$f'" >> "$LIST"
done
ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" -c copy "$FINAL" -y
rm "$LIST"

ls -lh "$FINAL"
ffprobe -hide_banner "$FINAL" 2>&1 | grep -E "Duration|Stream #0:0" | head -2

echo ""
echo "===================================================="
echo " Final video: $FINAL"
echo " Segments preserved at: $OUT_DIR/"
echo "===================================================="
