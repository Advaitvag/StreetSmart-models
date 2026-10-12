---
type: code-doc
component: Models & accuracy
source: models/, runs/
tags:
  - code
  - models
  - accuracy
---

# Models and Accuracy

## Purpose

This note lists every trained model in the repo and gives the **official accuracy numbers to report**. They come from an evaluation on Cincinnati-free imagery that no model ever trained on.

> [!important] Reporting rule
> Report accuracy only from the **Cincinnati-free, leak-free held-out set** described below. Do not use these sources:
> - **Cincinnati 311 images.** Their labels were produced by an ML model and may be inaccurate.
> - **The `metrics/*` columns in any `results.csv`, and the end-of-sweep notifications.** Those were scored on validation splits that either contain Cincinnati images or overlap the training data (see [[#Why the logged numbers can't be reported]]).

## Headline result

**Best model: `runs/night-yolo26m/weights/best.pt`**: YOLO26m, 300 epochs, ~20.4 M parameters (fused).

| Metric (held-out, Cincinnati-free, n = 1,548 images) | Value |
| --- | --- |
| mAP@0.5 | **0.808** |
| mAP@0.5:0.95 | **0.567** |
| Precision | 0.888 |
| Recall | 0.726 |
| F1 | 0.799 |
| Inference | ~9.9 ms/img (RTX 5060 Laptop, 640 px, batch 16, PyTorch FP16) |

## All detection models on the held-out set

Evaluated 2026-10-08 with Ultralytics 8.4.9: `imgsz=640`, `conf=0.001`, `iou=0.7` (the standard mAP protocol). Sorted by mAP@0.5:0.95.

| Run (weights = `<run>/weights/best.pt`) | Base | Epochs | Trained on | P | R | F1 | mAP50 | mAP50-95 | ms/img |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `runs/night-yolo26m` | YOLO26m | 300 | combined (incl. Cincinnati) | 0.888 | 0.726 | 0.799 | **0.808** | **0.567** | 9.9 |
| `runs/clean-yolo26m` ¹ | YOLO26m | 300 + 43 | night-yolo26m → Cincinnati-free | 0.866 | 0.734 | 0.794 | 0.807 | 0.539 | 9.9 |
| `runs/night-yolo11m` | YOLO11m | 300 | combined (incl. Cincinnati) | 0.874 | 0.708 | 0.783 | 0.783 | 0.524 | 10.2 |
| `runs/night-yolo26s` | YOLO26s | 300 | combined (incl. Cincinnati) | 0.864 | 0.691 | 0.767 | 0.773 | 0.503 | 4.4 |
| `runs/night-yolo11s` | YOLO11s | 300 | combined (incl. Cincinnati) | 0.863 | 0.684 | 0.763 | 0.755 | 0.484 | 4.0 |
| `runs/clean-yolo26s` | YOLO26s | 300 + 100 | night-yolo26s → Cincinnati-free | 0.837 | 0.692 | 0.758 | 0.762 | 0.476 | 4.3 |
| `runs/detect/runs/combined_yolo26m` = `models/trained/yolo26m-combined` | YOLO26m | 50 | combined (incl. Cincinnati) | 0.806 | 0.630 | 0.707 | 0.713 | 0.398 | 9.6 |
| `runs/detect/runs/combined_yolo26s` = `models/trained/yolo26s-combined` | YOLO26s | 50 | combined (incl. Cincinnati) | 0.748 | 0.616 | 0.675 | 0.678 | 0.365 | 4.0 |
| `runs/detect/runs/combined_pothole` = `models/trained/yolov8s-combined` | YOLOv8s | 50 | combined (incl. Cincinnati) | 0.771 | 0.595 | 0.672 | 0.659 | 0.359 | 4.5 |

¹ `clean-yolo26m` was stopped at epoch 43 of its 100-epoch budget. Its run has no `.done` marker.

What the table shows:

- **The 300-epoch night sweep beats the 50-epoch runs by a wide margin.** YOLO26m gains about +0.17 mAP50-95. The curated `models/trained/` folder still holds only the 50-epoch weights, so it is **not** the best model set.
- **YOLO26 beats YOLO11 at the same size.** Medium models beat small ones at about 2.3× the inference cost.
- **Fine-tuning on Cincinnati-free data alone (`clean-*`) slightly lowered held-out accuracy** compared with the night checkpoints those runs started from. Removing the noisy Cincinnati labels from training did not help, at least with this fine-tuning schedule.

### Models not re-evaluated

| Model | Why | Its logged number (not comparable) |
| --- | --- | --- |
| `models/trained/rfdetr-base` (RF-DETR base, 30 epochs, 560 px) | Needs the `rfdetr` package, which isn't in the venv. It was trained on `combined_dataset`. | mAP50-95 0.356 (EMA 0.372) on combined val |
| `models/trained/pothrgbd-seg` (YOLO11n-seg) | A segmentation model trained and validated **only on PothRGBD** (`datasets/PData`). Its own val split contains no Cincinnati images, so its number is Cincinnati-free, but it covers one source only. | box mAP50-95 0.684, mask mAP50-95 0.677 (epoch 79) |

## Why the logged numbers can't be reported

There are two Cincinnati-free candidates for evaluation, and both leak when used naively.

1. **`datasets/combined_dataset`** (19,547 images; the training set for the night and 50-epoch runs) **contains Cincinnati 311 images in both train and val.** The labels on those images are ML-generated and unreliable.
2. **`datasets/_upload_PotholesCombined`** (= `datasets/data_nocincinnati.yaml`; 16,641 images, seven sources, no Cincinnati) was rebuilt later by `scripts/build_dataset.py` with a **different random split**. An MD5 comparison of image contents shows that **954 of its 2,500 unique val images are in `combined_dataset/train`**. Every night model trained on them, and the clean models start from night weights.
   - This is visible in the clean runs. `clean-yolo26m` logged its *best* val mAP50-95 (0.632) at **epoch 1** and declined to 0.512 by epoch 43; `clean-yolo26s` went 0.576 → 0.521. The early number is inflated by memorized images.

## The held-out evaluation set

Defined as: **the images in `_upload_PotholesCombined/val` whose content (MD5) does not appear in `combined_dataset/train` or `_upload_PotholesCombined/train`.**

- 2,502 val files → 2,500 unique contents → **1,548 held-out images** (954 removed for overlap with combined train, plus 18 exact duplicates of clean-train images).
- No Cincinnati images. Labels come from the original public datasets (see `docs/BUILDING_THE_DATASET.md`).
- Caveats:
  - Model selection (`best.pt`) for the night runs used `combined_dataset/val`, which contains 1,420 of these images. This is a mild *selection* bias, not training leakage. The clean runs selected on their own val, which contains all of them.
  - The overlap filter removes images non-uniformly, so the source mix differs a little from the full val split.

### Reproducing it

Run from the repo root. It takes a few minutes on the GPU.

```bash
H=eval_holdout; mkdir -p $H/images $H/labels
hashes() { (cd "$1" && find . -type f -print0 | xargs -0 md5sum) | awk '{print $1}' | sort -u; }
{ hashes datasets/combined_dataset/train/images; hashes datasets/_upload_PotholesCombined/train/images; } | sort -u > $H/train.md5
(cd datasets/_upload_PotholesCombined/val/images && find . -type f -print0 | xargs -0 md5sum) |
while read -r sum f; do f=${f#./}
  grep -qx "$sum" $H/train.md5 && continue
  ln -s "$PWD/datasets/_upload_PotholesCombined/val/images/$f" $H/images/
  ln -s "$PWD/datasets/_upload_PotholesCombined/val/labels/${f%.*}.txt" $H/labels/
done
printf "path: $PWD/$H\ntrain: images\nval: images\nnc: 1\nnames:\n  0: pothole\n" > $H/data.yaml
ls $H/images | wc -l    # -> 1548

.venv/bin/python - <<'PY'
from ultralytics import YOLO
m = YOLO("runs/night-yolo26m/weights/best.pt")
b = m.val(data="eval_holdout/data.yaml", imgsz=640, batch=16, conf=0.001, iou=0.7, plots=False).box
print(f"P={b.mp:.3f} R={b.mr:.3f} mAP50={b.map50:.3f} mAP50-95={b.map:.3f}")
PY
```

`eval_holdout/` holds only symlinks and should not be committed. It is built from local `datasets/` that aren't in git.

## Model registry

| Location | Content | In git |
| --- | --- | --- |
| `models/pretrained/pothole_yolov8_best.pt` | Externally supplied YOLOv8 pothole weights, used as a reference. | yes (LFS) |
| `models/trained/{yolov8s,yolo26s,yolo26m}-combined/` | Curated copies of the 50-epoch runs: `best.pt`, `args.yaml`, `results.csv`, plots. | yes (LFS) |
| `models/trained/pothrgbd-seg/` | Segmentation model (PothRGBD). | yes (LFS) |
| `models/trained/rfdetr-base/` | RF-DETR best EMA checkpoint + config. | yes (LFS) |
| `runs/night-<model>/` | 300-epoch sweep runs (`yolo11s`, `yolo26s`, `yolo11m`, `yolo26m`), `best.pt` + `last.pt`. **This is where the best model lives.** | yes (LFS) |
| `runs/clean-<model>/` | Cincinnati-free fine-tunes of the night models. | yes (LFS) |
| `runs/detect/runs/*` | Raw Ultralytics output of the 50-epoch runs. | yes (LFS) |
| `/yolo*.pt` (repo root) | Stock COCO weights, auto-downloaded by Ultralytics. | no |

## Related

- [[Training]]: how each run was produced
- [[Dataset_Builder]]: how the datasets are built
- [[Inference]]: running these weights on video
- [[Known_Issues]]
