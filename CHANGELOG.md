# Changelog - Gemma Video

## [2026-05-22]
### Added
- **On-Device Model Downloader**: Added `ModelDownloader` class and UI to `MainActivity` to support downloading Gemma-4 models directly from Hugging Face on the mobile device.
### Fixed
- **Mobile App Stability**: Fixed a persistent `NoSuchMethodError` crash in `MemoryBridgeService` by switching the Ktor server engine from `CIO` to `Netty` and aligning coroutine dependencies to version `1.8.1`.
- **Netty Resource Conflicts**: Resolved duplicate `META-INF` files in the APK build by configuring packaging options in `build.gradle`.
- **Android 14+ Stability**: Fixed `MissingForegroundServiceTypeException` crash in `LlmService` by implementing required Foreground Service types and permissions.

## [2026-05-22]
### Fixed
- **Python Environment**: Recreated and stabilized the virtual environment using `virtualenv` to ensure `numpy`, `cv2`, and `Pillow` are correctly installed for video analysis.
- **Verifier Script**: Fixed a function name mismatch in `verifier.py` (`select_diverse_7_from_pool`) to enable Level 3 diversity testing.
### Verified
- **System Operational Status**: Confirmed 100% PRD compliance via `verifier.py`.
- **End-to-End Demo**: Successfully executed `manual_trigger.sh`, performing automated ADB capture and Gemma-4 curation (with fallback) across 10+ apps.
- **Dashboard Accessibility**: Verified that the Glassmorphic Dashboard is fully operational at `http://localhost:9080`.

## [Unreleased]

### Added
- Local ADB installation in WSL2 to replace the dependency on Windows-hosted ADB.
### Added
- **Remote Curation API**: The mobile app now exposes a `/refine` endpoint to trigger 20->7 narrative curation remotely.
- **Dashboard Refinement Control**: Added a "REFINE" button to the glassmorphic dashboard for on-demand AI curation.
- **20->7 On-Device Curation**: Implemented native Kotlin logic for narrative-driven highlight extraction.
- **Local Model Stabilization**: Modified `LlmInferenceManager.kt` to synchronize vision and text backends, enabling functional fallback to CPU/NPU on devices with limited GPU delegate support.
- **Embedded LLM Server Persistence**: Exported `LlmService` in `AndroidManifest.xml` to allow external orchestration and easier debugging of the on-device AI server.
- **On-Device Model Verification**: Confirmed full multimodal capability of Gemma-4-E2B-it on Android using NPU and CPU backends.
...
## [Unreleased] - 2026-05-22\n### Fixed\n- Cleaned up git repository by untracking non-source files and adding a robust .gitignore.
