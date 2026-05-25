#!/bin/bash
# Drive the phone via adb and record screen via screenrecord.
# Output: /tmp/aetherlens_demo.mp4 (host).

set -e
TARGET="${1:-ZA2232T6XT}"
ADB="adb -s $TARGET"
DURATION=50
DEVICE_MP4="/sdcard/aetherlens_demo.mp4"
HOST_MP4="/tmp/aetherlens_demo.mp4"

# Coordinates (from uiautomator dump)
TAB_STORYBOARD_X=203; TAB_STORYBOARD_Y=2566
TAB_SETTINGS_X=1017;  TAB_SETTINGS_Y=2566
AMAZON_THUMB_X=234;   AMAZON_THUMB_Y=1059
CLOSE_PREVIEW_X=180;  CLOSE_PREVIEW_Y=124
MID_X=610

echo "=== Prep ==="
$ADB shell "rm -f $DEVICE_MP4"
$ADB shell "settings put system show_touches 1" || true
$ADB shell "svc power stayon usb"

# Make sure we're on Storyboard tab at the top
$ADB shell "input tap $TAB_STORYBOARD_X $TAB_STORYBOARD_Y"
sleep 1
$ADB shell "input swipe $MID_X 800 $MID_X 2200 300"
sleep 0.5
$ADB shell "input swipe $MID_X 800 $MID_X 2200 300"
sleep 1.5

echo "=== Recording for ${DURATION}s ==="
# Start screenrecord in background. The adb shell call blocks until
# screenrecord exits (after DURATION). Run as background of host shell.
$ADB shell "screenrecord --time-limit $DURATION --bit-rate 12000000 $DEVICE_MP4" &
REC_PID=$!

# Allow screenrecord ~0.6s to initialize before first action
sleep 1

# --- Timeline (target ~45s) ---

# 0-4s: rest on Storyboard top (Amazon card)
sleep 4

# 4-13s: slow scroll showing more apps
$ADB shell "input swipe $MID_X 2200 $MID_X 1000 1200"
sleep 1.5
$ADB shell "input swipe $MID_X 2200 $MID_X 1000 1200"
sleep 1.5
$ADB shell "input swipe $MID_X 2200 $MID_X 1000 1200"
sleep 1.5
$ADB shell "input swipe $MID_X 2200 $MID_X 1000 1200"
sleep 1.5

# 13-15s: rest after scroll
sleep 2

# 15-19s: scroll back to top
$ADB shell "input swipe $MID_X 800 $MID_X 2200 300"
sleep 0.7
$ADB shell "input swipe $MID_X 800 $MID_X 2200 300"
sleep 0.7
$ADB shell "input swipe $MID_X 800 $MID_X 2200 300"
sleep 1.5

# 19-23s: tap Amazon thumbnail → fullscreen
$ADB shell "input tap $AMAZON_THUMB_X $AMAZON_THUMB_Y"
sleep 4

# 23-26s: close fullscreen
$ADB shell "input tap $CLOSE_PREVIEW_X $CLOSE_PREVIEW_Y"
sleep 3

# 26-30s: tap Settings tab
$ADB shell "input tap $TAB_SETTINGS_X $TAB_SETTINGS_Y"
sleep 4

# 30-37s: scroll Settings tab to show controls
$ADB shell "input swipe $MID_X 2000 $MID_X 1000 1000"
sleep 3
$ADB shell "input swipe $MID_X 2000 $MID_X 1000 1000"
sleep 3

# 37-42s: tap Storyboard tab back
$ADB shell "input tap $TAB_STORYBOARD_X $TAB_STORYBOARD_Y"
sleep 5

# Wait for screenrecord to finish naturally
wait $REC_PID

echo "=== Pulling MP4 ==="
$ADB pull $DEVICE_MP4 $HOST_MP4
$ADB shell "settings put system show_touches 0" || true

echo ""
echo "===================================================="
echo " DONE"
echo " Video saved at: $HOST_MP4"
echo " Size:           $(ls -lh $HOST_MP4 | awk '{print $5}')"
echo " Duration:       ~${DURATION}s"
echo "===================================================="
