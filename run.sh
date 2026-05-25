#!/bin/bash

# AetherLens Deployment Script
# This script installs the AetherLens Screen Memory app and verifies connectivity.

APK_PATH="dashboard/app-debug.apk"
PACKAGE_NAME="com.gemma.videomemory"

echo "===================================================="
echo "       AETHER LENS - APP DEPLOYMENT TOOL           "
echo "===================================================="

# Check if APK exists
if [ ! -f "$APK_PATH" ]; then
    echo "[!] Error: APK not found at $APK_PATH"
    exit 1
fi

# 1. Build the APK from source
echo "[*] Building AetherLens Mobile App from source..."
cd mobile_app
./gradlew assembleDebug
if [ $? -ne 0 ]; then
    echo "[!] Error: Gradle build failed. Check your Android SDK configuration."
    exit 1
fi
cd ..

# 2. Refresh the dashboard APK
echo "[*] Updating dashboard APK..."
NEW_APK="mobile_app/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$NEW_APK" ]; then
    cp "$NEW_APK" "$APK_PATH"
    echo "[+] Dashboard APK refreshed."
else
    echo "[!] Error: New APK not found at $NEW_APK"
    exit 1
fi

# 3. Verify device connection
echo "[*] Checking for Android devices..."
DEVICE_COUNT=$(timeout 5s adb devices | grep -v "List" | grep "device" | wc -l)

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo "[!] Error: No Android device detected. Please connect via USB/WiFi."
    exit 1
fi

# 2. Install the APK
echo "[*] Installing AetherLens Screen Memory ($APK_PATH)..."
# -r: replace existing
# -t: allow test packages
# -g: grant all permissions
# -d: allow version code downgrade
INSTALL_RESULT=$(timeout 20s adb install -r -t -g -d "$APK_PATH")

if [[ $INSTALL_RESULT == *"Success"* ]]; then
    echo "[+] Installation Successful!"
else
    echo "[!] Installation Failed: $INSTALL_RESULT"
    # Don't exit yet, sometimes adb returns non-zero but succeeds
fi

# 3. Verify installation using multiple methods
echo "[*] Verifying package $PACKAGE_NAME..."
# Method 1: pm list
INSTALLED=$(timeout 5s adb shell pm list packages | grep "$PACKAGE_NAME")

# Method 2: path check
if [ -z "$INSTALLED" ]; then
    INSTALLED=$(timeout 5s adb shell pm path "$PACKAGE_NAME")
fi

if [ -z "$INSTALLED" ]; then
    echo "[!] Warning: Package $PACKAGE_NAME not explicitly listed. Attempting force-start..."
    # Attempt to start the activity - if it starts, it's there
    START_RESULT=$(timeout 5s adb shell am start -n "$PACKAGE_NAME/.MainActivity" 2>&1)
    if [[ $START_RESULT == *"Starting"* ]]; then
        echo "[+] Success: App launched successfully despite being hidden from list."
    else
        echo "[!] Error: App launch failed: $START_RESULT"
        echo "[*] Searching for similar packages..."
        timeout 5s adb shell pm list packages | grep -E "gemma|memory|lens"
        exit 1
    fi
else
    echo "[+] Verified: $PACKAGE_NAME is present on device."
    echo "[*] Launching AetherLens..."
    timeout 5s adb shell am start -n "$PACKAGE_NAME/.MainActivity"
fi

# 4. Instructions for user
echo ""
echo "----------------------------------------------------"
echo "🚀 NEXT STEPS TO ACTIVATE RECORDING:"
echo "----------------------------------------------------"
echo "1. On your phone, look for the app: 'AetherLens'"
echo "2. Open it and follow the prompts to:"
echo "   a. Enable 'Accessibility Service' -> 'AetherLens Screen Memory'"
echo "   b. Grant 'All Files Access' to save memories locally."
echo "3. Once active, your daily recap will update automatically!"
echo "----------------------------------------------------"
echo "Done."
