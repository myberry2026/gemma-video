# AetherLens Android Screen Memory Logger

A premium, high-fidelity local background screenshot sequence and app-switch logging application for Android. Built with native Kotlin on top of Android's accessibility layer, it enables seamless, low-overhead mobile screen memory capture designed to feed directly into the Gemma-4 reasoning pipeline.

> [!NOTE]
> This native app transitions our workflow from the ADB-based mockup engine to a true, autonomous on-device screen capture solution!

---

## 🛠️ Key Architectural Features

- **Accessibility Service Integration**: Uses the official Android `AccessibilityService` (`takeScreenshot` API introduced in Android 11 / API 30) to bypass system security prompts and record screenshots silently in the background.
- **Dynamic App State Detection**: Monitors the Android windowing state (`TYPE_WINDOW_STATE_CHANGED` events). When you switch apps (e.g. from WhatsApp to Chrome), it dynamically logs the package name and immediately fires a highlight screen capture.
- **Periodic Storyboard Capture**: Runs a highly optimized background execution handler that captures a storyboard frame every **5 seconds** for active user context mapping.
- **Hardware-to-Software Bitmap Conversion**: Decodes raw Android `HardwareBuffer` objects and wraps them into standard compressed `ARGB_8888` software bitmaps for asynchronous disk storage, preventing memory leakage or GPU stalls.
- **Zero Cloud Footprint**: Saves captures directly and securely to the device's local folder at `/sdcard/AetherLens/`.

---

## 📂 Project Structure

```
mobile_app/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── AndroidManifest.xml (Declares BIND_ACCESSIBILITY_SERVICE & permissions)
│   │       ├── java/com/gemma/videomemory/
│   │       │   ├── MainActivity.kt (Modern slate-dark companion control UI)
│   │       │   └── MemoryBridgeService.kt (Native capture & logging engine)
│   │       └── res/
│   │           ├── layout/activity_main.xml (Premium layout featuring glowing status)
│   │           ├── xml/accessibility_service_config.xml (Declares canTakeScreenshot & canRetrieveWindowContent flags)
│   │           └── values/strings.xml (Service descriptions & text)
└── README.md
```

---

## ⚙️ Compilation & Installation

### Step 1: Open in Android Studio
1. Import the `/home/winterandchaiyun/shared/gemma-video/mobile_app` project directory.
2. Ensure you are using Android SDK 30+ (Android 11) or higher.

### Step 2: Build and Install via CLI
You can also compile and install the debug package using ADB and Gradle:
```bash
# Build the project
./gradlew assembleDebug

# Sideload the APK to the active Android device
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## 🔒 Required Permissions & Activation

To ensure secure background operation, the Android system requires two permissions:

1. **Accessibility Service Activation**:
   - Open your phone's **Settings** -> **Accessibility** -> **Installed Services**.
   - Locate and turn on **AetherLens Screen Memory**.
2. **All Files Access**:
   - The app will automatically prompt you to grant `MANAGE_APP_ALL_FILES_ACCESS_PERMISSION`.
   - Toggle the switch to **Allow access to manage all files** so the service can write screen images to `/sdcard/AetherLens/`.

---

## 🚀 Linking to the Gemma-4 Analysis Server

When running the AetherLens companion app on your phone, you can pull screenshots to the host machine for Gemma-4 analysis using this simple adb-watch loop:

```bash
# Periodic sync loop to fetch newly captured frames and feed them to daily_recap
adb pull /sdcard/AetherLens/ dashboard/images/
```

The captured files follow the structure `Memory_[package_name]_[trigger]_[timestamp].png`, allowing the Python companion script to group them into app storyboards, request **Gemma-4-e2b** keyframe selections, and render the gorgeous dark-mode recap dashboard!
