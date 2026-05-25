#!/bin/bash
# Drive the phone via ADB: open each demo app, scroll & capture 20 frames,
# save directly into /sdcard/AetherLens/raw/ in the format the Storyboard
# tab expects (<pkg>_<YYYYMMDD>_<HHMMSS>.png).

set -e
TARGET="${1:-ZA2232T6XT}"
ADB="adb -s $TARGET"
RAW_DIR="/sdcard/AetherLens/raw"
DATE="$(date +%Y%m%d)"
FRAMES_PER_APP=20

# App list: pkg / launch_intent_action / scroll_strategy
# scroll: "v" (vertical fling) or "h" (horizontal fling) or "n" (none)
APPS=(
  "com.amazon.mShop.android.shopping|v"
  "com.android.chrome|v"
  "com.google.android.calendar|v"
  "com.google.android.youtube|v"
  "com.zhiliaoapp.musically|v"
  "com.google.android.apps.photos|v"
  "com.google.android.apps.maps|n"
  "com.google.android.apps.messaging|v"
  "com.android.settings|v"
  "com.google.android.contacts|v"
)

echo "=== Staging demo data on $TARGET ==="
$ADB shell "mkdir -p $RAW_DIR"

# Get screen size
SCREEN=$($ADB shell wm size | grep -oE '[0-9]+x[0-9]+' | tail -1)
W=$(echo $SCREEN | cut -dx -f1)
H=$(echo $SCREEN | cut -dx -f2)
MID_X=$((W / 2))
SCROLL_DOWN_Y1=$((H * 3 / 4))
SCROLL_DOWN_Y2=$((H / 4))
echo "Screen: ${W}x${H}"

idx=0
for entry in "${APPS[@]}"; do
    PKG=$(echo "$entry" | cut -d'|' -f1)
    SCROLL=$(echo "$entry" | cut -d'|' -f2)

    idx=$((idx+1))
    echo ""
    echo "[$idx/${#APPS[@]}] $PKG (scroll=$SCROLL)"

    # Launch via monkey (works without knowing the activity name)
    $ADB shell "monkey -p $PKG -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1 || {
        echo "  [!] launch failed, skipping"
        continue
    }
    sleep 3   # app cold-start

    for n in $(seq 0 $((FRAMES_PER_APP - 1))); do
        # Capture
        TS="$(date +%H%M%S)"
        # Bump seconds to ensure filename uniqueness across the loop
        TS_UNIQ=$(printf "%06d" $(( 10#$TS + n )))
        FNAME="${PKG}_${DATE}_${TS_UNIQ}.png"
        $ADB shell "screencap -p $RAW_DIR/$FNAME"

        # Scroll for next frame (skip after last capture)
        if [ "$n" -lt $((FRAMES_PER_APP - 1)) ]; then
            case "$SCROLL" in
                v)
                    $ADB shell "input swipe $MID_X $SCROLL_DOWN_Y1 $MID_X $SCROLL_DOWN_Y2 200"
                    ;;
                h)
                    $ADB shell "input swipe $((W*3/4)) $((H/2)) $((W/4)) $((H/2)) 200"
                    ;;
                n) ;;
            esac
            sleep 0.5
        fi
        printf "  frame %02d/$FRAMES_PER_APP captured\r" "$n"
    done
    echo ""

    # Return to home before next app
    $ADB shell "input keyevent KEYCODE_HOME"
    sleep 1
done

echo ""
echo "=== Staging complete ==="
$ADB shell "ls $RAW_DIR | awk -F'_[0-9]{8}_' '{print \$1}' | sort | uniq -c"
echo ""
echo "Total: $($ADB shell ls $RAW_DIR | wc -l) files"
