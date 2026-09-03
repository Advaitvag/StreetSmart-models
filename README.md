# Pothole Detection

Training code, trained models, and dataset tooling for single-class
(`pothole`) object detection built on a combined dataset of eight public
sources.

## Layout

| Path | What |
| --- | --- |
| `train.py` | Standalone Ultralytics YOLO training CLI. |
| `scripts/build_dataset.py` | Rebuilds the combined dataset from its sources. |
| `docs/BUILDING_THE_DATASET.md` | Build steps + per-source credits/licenses. |
| `models/pretrained/` | Externally-supplied starting weights. |
| `models/trained/` | Best weights + metrics from each training run. |
| `runs/` | Raw Ultralytics / RF-DETR run output (videos excluded). |
| `requirements.txt` | torch cu128 + ultralytics + huggingface_hub. |

Not tracked in git (kept locally): `datasets/`, `cincinnati/`, `labels/`,
demo `*.mp4`, stock `yolo*.pt` weights.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import torch; print(torch.cuda.is_available())"   # -> True
```

Weights and training plots are stored with **Git LFS** — run
`git lfs install` once after cloning.

> The venv is created from a Python 3.12 interpreter (system Python is 3.14,
> which is ahead of the current torch wheels). Any 3.12 interpreter works.

## Training

```bash
# YOLO26s, defaults (50 epochs, imgsz 640, batch 16), writes runs/yolo26s-combined_dataset/
.venv/bin/python train.py --model yolo26s.pt

# YOLO26m with a smaller batch
.venv/bin/python train.py --model yolo26m.pt --batch 8 --name yolo26m-combined

# Segmentation
.venv/bin/python train.py --model yolo11n-seg.pt --data datasets/PData/data.yaml

# Forward an arbitrary Ultralytics arg
.venv/bin/python train.py --model yolo26s.pt --set cos_lr=true --set close_mosaic=15
```

`--help` lists every flag. Paths passed to `--model` / `--data` resolve
against the repo root, so the script works from any working directory.

### Overnight training sweep

`scripts/night_train.sh` + the `systemd/streetsmart-night*` user timers train
`yolo11s -> yolo26s -> yolo11m -> yolo26m` back-to-back on `combined_dataset`,
every night from 23:00 to 08:30. Each model starts from stock COCO weights, runs
to 300 epochs (resumed across nights), and only begins once its predecessor
finishes. `notify-send` at every start/end with per-metric deltas; per-epoch
history in `runs/night-<model>/results.csv`, session history in
`runs/streetsmart_night_metrics.csv`. See
[`docs/NIGHT_TRAINING.md`](docs/NIGHT_TRAINING.md).

## Dataset

The combined dataset (~19.5k images, single `pothole` class) and the build
script are published to HuggingFace; the imagery itself is **not** in this
repo. See [`docs/BUILDING_THE_DATASET.md`](docs/BUILDING_THE_DATASET.md) for
how to reconstruct it and for source attribution.

Cincinnati 311 imagery used in local training runs is not redistributable
and is excluded from the published dataset.

## Models

| `models/trained/` | From | Base | Task |
| --- | --- | --- | --- |
| `yolov8s-combined/` | `runs/detect/runs/combined_pothole/` | YOLOv8s | detect |
| `yolo26s-combined/` | `runs/detect/runs/combined_yolo26s/` | YOLO26s | detect |
| `yolo26m-combined/` | `runs/detect/runs/combined_yolo26m/` | YOLO26m | detect |
| `pothrgbd-seg/` | `runs/pothrgbd_seg/` | YOLOv8n-seg | segment |
| `rfdetr-base/` | `runs/rfdetr_base/` (best EMA checkpoint) | RF-DETR base | detect |

## Licenses

- Code: MIT (`LICENSE`).
- Combined dataset: aggregate of independently-licensed sources — ODbL v1.0,
  CC BY 4.0, CC BY-SA 4.0 and MIT depending on the source; project-added files
  (split layout, `data.yaml`, manifests) under CC BY-SA 4.0. Full per-source
  table in `docs/BUILDING_THE_DATASET.md`.
