# Building the combined pothole dataset

`scripts/build_dataset.py` merges eight public YOLO-format pothole datasets
into one `train` / `val` split with a single class (`0: pothole`).

- Segmentation polygons (PothRGBD) are converted to axis-aligned boxes.
- Multi-class sources (Curated RGB, RDD2022) are filtered to their pothole
  class and remapped to `0`.
- The split is a per-source shuffle with `train_ratio = 0.85`, `seed = 42`.
- File-stem collisions across sources are resolved by prefixing the later
  file with its source name (no silent overwrite).

## 1. Prerequisites

- Python 3.9+ (standard library only — no third-party packages needed).
- The eight source datasets downloaded into one directory (default:
  `./datasets`).

## 2. Expected layout

```
datasets/
├── BharatPotHole/BharatPotHole/{train,valid,test}/{images,labels}
├── HRP4K/{train,valid,test}/{images,labels}
├── A Curated RGB Dataset for Real-Time Road Damage De/Data Y12 Final/{train,valid}/{images,labels}
├── Pothole-detection-Yolov8/{train,valid,test}/{images,labels}
├── dataset/{train,valid,test}/          # images and .txt labels co-located
├── PData/{images,labels}/               # polygon segmentation labels
└── RDD_SPLIT/{train,val}/{images,labels}   # 5 classes; class 3 (D40) == pothole
```

## 3. Build

Publishable dataset (this is what is uploaded to HuggingFace):

```bash
python scripts/build_dataset.py
```

Writes `datasets/combined_dataset/` containing:

| File / dir | Contents |
| --- | --- |
| `train/images`, `train/labels` | ~85% of each source |
| `val/images`, `val/labels` | ~15% of each source |
| `data.yaml` | Ultralytics config (`nc: 1`, `names: {0: pothole}`) |
| `build_manifest.json` | per-source counts, seed, ratio, timestamp |
| `SOURCES.md` | the credits table below |

Useful flags: `--sources-dir`, `--out`, `--train-ratio`, `--seed`, `--force`
(write into a non-empty output dir).

### Local training build (maintainer only)

The maintainer's own runs additionally fold in Cincinnati 311 pothole
imagery, which is **not redistributable** and therefore **not** part of the
published dataset:

```bash
python scripts/build_dataset.py --cincinnati \
    --cincinnati-images cincinnati --cincinnati-labels labels
```

## 4. Sources & credits

The combined dataset is released under **CC BY-SA 4.0**. The PothRGBD
component is MIT-licensed (compatible with redistribution here). Where an
upstream README states a different original license, it is noted for
compliance.

| Source | Attribution | License |
| --- | --- | --- |
| Roboflow "Pothole" raw (`dataset/`) | Atikur Rahman Chitholian ([Potholes-Detection](https://github.com/chitholian/Potholes-Detection)) | CC BY-SA 4.0 *(orig. ODbL v1.0)* |
| Roboflow "Potholes Detection" (`Pothole-detection-Yolov8/`) | Roboflow Universe workspace `project-ssayl`, project `potholes-detection-d4rma` | CC BY-SA 4.0 *(orig. CC BY 4.0)* |
| PothRGBD (`PData/`) | M. Yurdakul & Ş. Taşdemir, *An Enhanced YOLOv8 Model for Real-Time and Accurate Pothole Detection and Measurement*, 2025 — [arXiv:2505.04207](https://arxiv.org/abs/2505.04207) | MIT |
| RDD2022 (`RDD_SPLIT/`, class `D40` only) | D. Arya et al., Road Damage Detection Challenge / RDD2022 | CC BY-SA 4.0 |
| BharatPotHole | BharatPotHole dataset authors | CC BY-SA 4.0 |
| A Curated RGB Dataset for Real-Time Road Damage Detection | dataset authors (Mendeley Data) | CC BY-SA 4.0 |
| HRP4K | HRP4K dataset authors | CC BY-SA 4.0 |
| Cincinnati 311 pothole imagery | City of Cincinnati / CAGIS open records | Not redistributed — excluded from the published dataset |

If you redistribute the combined dataset, keep this attribution table and
license it under CC BY-SA 4.0.
