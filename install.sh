#!/bin/bash
# AetherLens — Build, Install, and Bring-Up
# Builds the APK, installs it on a target device, starts the embedded LLM
# server, and pre-loads gemma-4-E2B with CPU backend (GPU OpenGL is unsupported
# on most Motorola devices we've tested).

set -e

PACKAGE_NAME="com.gemma.videomemory"
SERVICE_NAME="$PACKAGE_NAME/.llm.LlmService"
MAIN_ACTIVITY="$PACKAGE_NAME/.MainActivity"
NEW_APK="mobile_app/app/build/outputs/apk/debug/app-debug.apk"
DASHBOARD_APK="dashboard/app-debug.apk"
MODEL_HOST_PATH="/sdcard/Download/gemma-4-E2B-it.litertlm"
LLM_PORT=8080
BRIDGE_PORT=9085

# ---- Target device ----
TARGET="${1:-}"
if [ -z "$TARGET" ]; then
    DEVICES=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
    COUNT=$(echo "$DEVICES" | grep -c .)
    if [ "$COUNT" -eq 0 ]; then
        echo "[!] No connected adb device. Plug in or pass a serial: ./install.sh <serial>"; exit 1
    fi
    if [ "$COUNT" -gt 1 ]; then
        echo "[*] Multiple devices connected. Pick one:"
        adb devices
        echo "Usage: ./install.sh <serial>"; exit 1
    fi
    TARGET="$DEVICES"
fi
ADB="adb -s $TARGET"
MODEL=$($ADB shell getprop ro.product.model | tr -d '\r')

echo "===================================================="
echo " AETHERLENS — INSTALL & BRING-UP"
echo " Device: $TARGET ($MODEL)"
echo "===================================================="

# ---- 1. Build ----
echo "[1/6] Building APK..."
( cd mobile_app && ./gradlew --no-daemon assembleDebug ) || { echo "[!] Gradle build failed"; exit 1; }
[ -f "$NEW_APK" ] || { echo "[!] APK not found at $NEW_APK"; exit 1; }
cp "$NEW_APK" "$DASHBOARD_APK"
echo "[+] Built and refreshed dashboard APK."

# ---- 2. Install ----
echo "[2/6] Installing on device..."
$ADB install -r -t -g -d "$DASHBOARD_APK"

# ---- 3. Verify model on device ----
echo "[3/6] Verifying model file on device..."
SIZE=$($ADB shell "stat -c %s $MODEL_HOST_PATH 2>/dev/null" | tr -d '\r')
if [ -z "$SIZE" ] || [ "$SIZE" -lt 1000000000 ]; then
    echo "[!] Gemma-4-E2B model missing or too small at $MODEL_HOST_PATH."
    echo "    Push manually: adb push gemma-4-E2B-it.litertlm $MODEL_HOST_PATH"
    exit 1
fi
echo "[+] Model present: $((SIZE/1024/1024)) MB"

# ---- 4. Launch app + start LLM service ----
echo "[4/6] Launching app and starting LLM service..."
$ADB shell am start -n "$MAIN_ACTIVITY" > /dev/null
sleep 2
$ADB shell am start-foreground-service -n "$SERVICE_NAME" > /dev/null

# Wait for the server port to open
echo -n "[*] Waiting for embedded LLM server on :$LLM_PORT..."
for i in $(seq 1 30); do
    RES=$($ADB shell "echo -e 'GET /health HTTP/1.0\r\n\r\n' | nc -w 2 127.0.0.1 $LLM_PORT 2>/dev/null | tail -1")
    if echo "$RES" | grep -q '"status":"ok"'; then
        echo " up."
        break
    fi
    echo -n "."
    sleep 1
done

# ---- 5. Force-load model with CPU backend ----
echo "[5/6] Loading Gemma-4-E2B (backend=cpu)... this takes ~30s"
PAYLOAD="{\"path\":\"$MODEL_HOST_PATH\",\"backend\":\"cpu\"}"
LEN=$(printf '%s' "$PAYLOAD" | wc -c)
LOAD_RES=$($ADB shell "printf 'POST /models/load HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: $LEN\r\n\r\n%s' '$PAYLOAD' | nc -w 120 127.0.0.1 $LLM_PORT" | tail -1)
if echo "$LOAD_RES" | grep -q '"success":true'; then
    echo "[+] Model loaded."
else
    echo "[!] Load response: $LOAD_RES"
    echo "    (If this is empty, the FGS pre-load may already be in progress — check /health again.)"
fi

# ---- 6. Final health check ----
echo "[6/6] Final health check..."
HEALTH=$($ADB shell "echo -e 'GET /health HTTP/1.0\r\n\r\n' | nc -w 3 127.0.0.1 $LLM_PORT | tail -1")
echo "[ health ] $HEALTH"

echo ""
echo "===================================================="
echo " READY"
echo "===================================================="
echo " • Embedded LLM server: device localhost:$LLM_PORT"
echo " • Memory bridge:       device localhost:$BRIDGE_PORT"
echo " • Open app:            adb -s $TARGET shell am start -n $MAIN_ACTIVITY"
echo " • Test text:"
echo "     adb -s $TARGET shell \"printf 'POST /v1/chat/completions HTTP/1.0\\r\\nContent-Type: application/json\\r\\nContent-Length: 130\\r\\n\\r\\n{\\\"model\\\":\\\"gemma-4-E2B-it\\\",\\\"messages\\\":[{\\\"role\\\":\\\"user\\\",\\\"content\\\":\\\"Say hi.\\\"}],\\\"max_tokens\\\":80}' | nc -w 60 127.0.0.1 $LLM_PORT\""
echo "===================================================="
