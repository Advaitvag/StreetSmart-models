---
type: code-doc
component: Android capture app (StreetSmart Capture)
source: branch android-capture-app → android/
tags:
  - code
  - android
---

# Android Capture App (StreetSmart Capture)

> [!info] Branch
> The source is on the local branch **`android-capture-app`** (14 commits, not merged into `main` or pushed). On `main`, `android/` holds only leftover untracked Gradle build output. Check out the branch to work on the app: `git switch android-capture-app`.

## Purpose

A proof of concept that turns a phone into StreetSmart's capture device. It records road video and a GPS track **on the same clock**, so the server can find the GPS position of any frame, and therefore of any detected pothole. A map shows every road recorded. **The phone runs no detection.** Detection stays on the server (D0 decision: post-drive batch processing). The app replaces D0's dashcam (I4) and GPS logger (I5) inputs without changing the D0/D1 interfaces.

## How it works

### Why there is no "GPS per frame"

Phone GNSS gives about 1 fix/s, while video runs at 30 fps. Instead of tagging every frame, the app stores:

- every fix, stamped with Android's `elapsedRealtimeNanos`
- the capture time of each video segment's first frame, on the same clock

A frame's position is interpolated from the two fixes around it.

### Session folder: format `streetsmart-capture/1`

```
Documents/StreetSmart/<session_id = UTC start yyyyMMddTHHmmssZ>/
├── session.json   manifest; rewritten at each segment rotation and at stop
├── track.jsonl    one GNSS fix per line (t_ns, utc_ms, lat, lon, alt_m, acc_m, speed_mps, bearing_deg)
├── seg_000.mp4    H.264, no audio, keyframe every 1 s, ≤ 5 min per segment
└── seg_001.mp4 …
```

`session.json` records:

- `status`: `recording` / `complete` / `interrupted`
- `end_reason`: `user`, `left_screen`, `camera_error`, `thermal`, `storage_low`, `encoder_error`
- `clock`: the camera timestamp source, `realtime`, or `monotonic_converted` with a measured offset on Android 10–12
- the video parameters
- `segments[]`, each with `first_frame_ns` and `frame_count`. **Only segments listed here are valid.**

The full spec is `android/contract/README.md`, with a golden example in `android/contract/example/`.

### Frame → GPS rule

1. Take `T = first_frame_ns + round(pts × 1e9)`, where `pts` is read from the MP4. Do not use `index / fps`, because frame rate drops in low light.
2. Find the fixes `a` and `b` that bracket `T`.
3. The frame is `LOCATION_UNRESOLVED` if there is no such pair, if the gap between them is > 3 s, or if either fix's accuracy is missing or > 20 m.
4. Otherwise interpolate `lat`, `lon` and `utc_ms` linearly.

The reference implementation is `android/tools/resolve_recording.py`. It writes `frames_geo.csv`.

### App architecture (`com.streetsmart.capture`)

| Package | Responsibility |
| --- | --- |
| `ui/` | Jetpack Compose screens: `RecordScreen` (preview, REC/STOP, GPS-accuracy pill, status), `MapScreen` (MapLibre map of every session's route + summary card), `Access` (permissions), `Theme` |
| `recording/` | `RecordingController`: app-scoped lifecycle (`IDLE → STARTING → RECORDING → STOPPING`) and the stop rules (user, leaving the screen, camera/encoder failure, thermal, low storage). `ActiveRecording`: thread-safe owner of one session that appends fixes and keeps `session.json` accurate as segments finish. |
| `camera/` | `CameraSession` (Camera2 preview + encoder surface; EIS disabled to keep the raw geometry), `VideoEncoder` (MediaCodec H.264 → MediaMuxer segments, rotated at keyframes), `CameraChoice` / `CameraSelection` (pick the back camera) |
| `location/` | `LocationRecorder` (raw GPS fixes, ~1 Hz), `FixMapper` (`Location` → `Fix`) |
| `logic/` | Pure, unit-tested rules: `ClockAlignment` (maps camera timestamps onto elapsedRealtime), `Segments` (5-min policy, `seg_%03d.mp4`), `StorageBudget` (needs ≥ 1 GB to start, stops below 300 MB), `GpsStatus`, `Manifests`, `Orientation`, `Times`, `Format` |
| `storage/` | `SessionStore`: MediaStore-backed shared `Documents/StreetSmart/`, visible over USB and kept across uninstall. Marks sessions left `recording` by a dead process as `interrupted`. |
| `track/`, `map/` | Parse `track.jsonl`, build routes, compute distance and summaries, render on MapLibre |
| `contract/` | Kotlin model + JSON codec for the session format |

Stack: Kotlin 2.2, AGP 8.13, Compose BOM 2025.12, kotlinx-serialization, MapLibre Android 11.13. `minSdk 29` (Android 10), `compileSdk`/`targetSdk 36`.

### Tests

- JVM unit tests for every `logic/`, `track/`, `contract/` (golden file) and `recording/` rule
- Instrumented tests for storage and encoder timestamps
- Python unit tests for the resolver
- `tools/emulator_smoke.sh`: an end-to-end test that records about 60 s on an emulator with an injected GPS route, pulls the session and checks it with the resolver

## Usage

Toolchain setup (JDK 21 + Android SDK in user space) is in `android/README.md`. From `android/`, after `. tools/env.sh`:

```bash
./gradlew :app:testDebugUnitTest               # unit tests
python3 -m unittest discover -s tools -v        # resolver tests
./gradlew :app:connectedDebugAndroidTest        # device tests
ANDROID_SERIAL=<serial> ./gradlew :app:installDebug
adb pull /sdcard/Documents/StreetSmart/<session_id> ~/drives/
python3 tools/resolve_recording.py ~/drives/<session_id>   # → frames_geo.csv
```

To record: mount the phone **in landscape**, grant camera and **precise** location, wait for the green `GPS ±N m` pill, then press REC. Leaving the screen stops and saves the recording.

## Known limitations

- After a reinstall, the app can't list sessions an earlier install created (Android storage ownership). The files are still there.
- There is no background recording; the Record screen must stay on.
- Map tiles need internet. Offline, routes are drawn on a plain background.
- The GPS position is the **phone's** position. Projecting it forward to the pothole (using bearing + bounding box + camera geometry) is an open server-side item.

## Related

- Design spec: `docs/superpowers/specs/2026-10-07-android-capture-app-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-07-android-capture-app.md`
- [[Backend_Pipeline]] · [[Overview]]
