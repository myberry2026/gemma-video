# GEMINI.md - AetherLens / Gemma Video Project

This project, internally named **AetherLens**, is a multimodal AI system that records Android phone screen activity and generates a "Daily Recap" visual diary using Google's **Gemma 4** multimodal models for high-level semantic analysis.

## 🚀 Project Overview

The system automates the lifecycle of "digital memory" capture and reflection:
1.  **Capture**: Background screen recording via a native Android Accessibility Service or automated ADB storyboard scripts.
2.  **Ingestion**: Retrieval of screen logs/videos from the device to a host workstation.
3.  **Processing**: Keyframe extraction using visual difference thresholds (OpenCV) to identify significant session changes.
4.  **Analysis**: Multimodal inference using `gemma-4-E2B-it` to describe and "score" highlights (e.g., summarizing Reddit threads, TikTok videos, or Chat conversations).
5.  **Visualization**: A premium, glassmorphic web dashboard that displays daily activities, storyboard sequences, and AI-generated insights.

## 🏗️ Architecture

-   **Mobile App (`mobile_app/`)**: Native Kotlin app implementing an `AccessibilityService`. It captures screenshots silently every 5 seconds or upon app-switch events.
-   **Backend / Analysis (`video_analysis/`)**:
    -   `daily_recap_pipeline.py`: The main entry point for processing videos/images and running Gemma-4 inference.
    -   `extract_highlights.py`: Core utility for detecting significant visual changes in video streams.
    -   `capture_storyboard.py`: ADB-based automation to simulate user behavior (wake, unlock, scroll, capture) across target apps (TikTok, Amazon, WhatsApp).
-   **Dashboard (`dashboard/`)**: A frontend-only web application (HTML/JS/CSS) featuring a dark-mode Glassmorphism design. It consumes `daily_recap.json`.

## 🛠️ Building and Running

### 1. Requirements
-   **Python Environment**: Conda or Venv with `torch`, `transformers`, `opencv-python`, `pillow`, `huggingface_hub`.
-   **Android Environment**: Android SDK (API 30+), Gradle, ADB.
-   **Hardware**: NVIDIA GPU (recommended for Gemma-4 inference).

### 2. Key Commands

#### Analysis & Pipeline
-   **Run Full Pipeline**:
    ```bash
    python3 video_analysis/daily_recap_pipeline.py --video video_analysis/rec_test.mp4 --run-gemma
    ```
-   **Extract Keyframes Only**:
    ```bash
    python3 video_analysis/extract_highlights.py
    ```

#### Automation & Capture
-   **Run Storyboard Capture**:
    ```bash
    python3 video_analysis/capture_storyboard.py
    ```
-   **Manual ADB Recording (User Hint: Always use 5s timeout)**:
    ```bash
    timeout 5s adb shell screenrecord /sdcard/rec.mp4
    ```

#### Mobile App
-   **Build & Install APK**:
    ```bash
    cd mobile_app && ./gradlew assembleDebug && adb install -r app/build/outputs/apk/debug/app-debug.apk
    ```

#### Web Dashboard
-   **Serve Dashboard Locally**:
    ```bash
    python3 -m http.server 9080 --directory dashboard
    ```
    *Access at http://localhost:9080*

## 📜 Development Conventions

-   **AI Inference**: Always use `torch.bfloat16` and `sdpa` attention implementation for optimal performance on Gemma-4 models.
-   **ADB Safety**: Per project mandates, all `adb` commands should be wrapped in a `timeout` (default 5s) to prevent hanging during remote execution.
-   **UI Design**: The dashboard follows a "Glassmorphism" aesthetic: blurred backgrounds, high saturation accents, and subtle animations.
-   **Data Storage**:
    -   Images: `dashboard/images/`
    -   Structured Data: `dashboard/daily_recap.json`
    -   Android Captures: `/sdcard/AetherLens/`

## 📂 Important Files

-   `video_analysis/daily_recap_pipeline.py`: Orchestrates extraction and Gemma analysis.
-   `video_analysis/source_video_processing_utils.py`: Low-level video handling utilities.
-   `mobile_app/app/src/main/java/com/gemma/videomemory/MemoryBridgeService.kt`: Core Android capture logic.
-   `dashboard/index.html` & `dashboard/style.css`: Dashboard entry point and styling.
-   `CHANGELOG.md`: Tracks project evolution.
-   `PROGRESS.md`: Detailed log of implementation milestones.
