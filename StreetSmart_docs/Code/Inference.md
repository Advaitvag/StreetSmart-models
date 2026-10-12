---
type: code-doc
component: Inference
source: infer.py
tags:
  - code
  - inference
---

# Inference (`infer.py`)

## Purpose

Runs one or more trained YOLO weight files over videos or images. It saves annotated output and prints a per-model, per-source summary of frames, detections, FPS and wall time. Used to compare models on real dashcam footage.

## How it works

1. **Resolve models.** `--models` takes weight paths and/or the preset `night` (aliases `all-night`, `default`). The preset expands to the four `runs/night-*/weights/best.pt` files. Missing files print a warning and are skipped.
2. **Resolve sources.** `--source` takes files, directories (every file inside) and glob patterns. Results are de-duplicated and kept in order. Default: `datasets/test_videos/*.mp4` (currently two YouTube pothole drive clips).
3. For each model × source, call `model.predict(...)` with `save=True`, `exist_ok=True` and **`stream=True`** by default (a generator, so memory stays flat on long videos), counting frames and `len(r.boxes)`.
4. Output goes to `<project>/<run_name>/`, where `run_name` is `--name`, else the run directory name (e.g. `night-yolo26m`), else the weights file stem.
5. Ultralytics writes MJPG `.avi`. With `--mp4` (the default), each AVI is re-encoded to H.264 MP4 with ffmpeg: `h264_nvenc` first, then a fallback to `libx264`. The AVI is deleted afterwards. If ffmpeg is missing, the AVI is kept.
6. A summary table is printed at the end.

## Usage

```bash
.venv/bin/python infer.py                                             # 4 night models × test videos
.venv/bin/python infer.py --models runs/night-yolo26m/weights/best.pt # best model only
.venv/bin/python infer.py --models night --conf 0.4 --project runs/inference_c40
.venv/bin/python infer.py --source path/to/drive.mp4 --save-txt --save-conf
.venv/bin/python infer.py --set line_width=2 --set show_labels=true   # extra predict() kwargs
```

| Flag | Default |
| --- | --- |
| `--models` | `night` |
| `--source` | `datasets/test_videos/*.mp4` |
| `--conf` / `--iou` / `--imgsz` | 0.25 / 0.45 / 640 |
| `--device` | `0` |
| `--project` / `--name` | `runs/inference` / auto |
| `--save-txt`, `--save-conf` | off |
| `--save-vid` / `--no-save-vid` | on |
| `--mp4` / `--no-mp4` | on |
| `--stream` / `--no-stream` | on |
| `--set KEY=VALUE` | forwarded to `predict()` |

Exit codes: 2 if no valid models or sources are found, 1 if ultralytics is missing, otherwise 0. A failure on a single source is logged and skipped.

> [!note]
> The FPS in the summary includes video decode, drawing and writing, so it is lower than pure model latency. For model latency see [[Models_and_Accuracy]]. "Detections" counts boxes summed over frames, not unique potholes.

## Related

- [[Models_and_Accuracy]]: which weights to use
- [[Backend_Pipeline]]: production inference path (ONNX in Go)
