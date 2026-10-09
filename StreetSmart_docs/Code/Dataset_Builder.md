---
type: code-doc
component: Dataset builder
source: scripts/build_dataset.py
tags:
  - code
  - dataset
---

# Dataset Builder (`scripts/build_dataset.py`)

## Purpose

Merges independently published pothole datasets into one YOLO-format detection dataset with a single class (`0: pothole`) and a `train` / `val` split. Needs only the standard library.

## How it works

The `Builder` class ingests each source and copies image + label into `<out>/{train,val}/{images,labels}`:

| # | Source dir under `datasets/` | Builder name | Handling | Count in clean build |
| --- | --- | --- | --- | --- |
| 1 | `BharatPotHole/BharatPotHole/{train,valid,test}` | `BharatPotHole` | plain YOLO | 4,196 |
| 2 | `HRP4K/{train,valid,test}` | `HRP4K` | plain YOLO | 2,697 |
| 3 | `A Curated RGB Dataset…/Data Y12 Final/{train,valid}` | `CuratedRGB` | keep class 1 → 0 | 328 |
| 4 | `Pothole-detection-Yolov8/{train,valid,test}` | `Roboflow-YOLOv8` | plain YOLO | 300 |
| 5 | `dataset/{train,valid,test}` (images + labels in the same folder) | `dataset-generic` | plain YOLO | 1,784 |
| 6 | `PData/{images,labels}` | `PData` | **polygon → axis-aligned box** | 996 |
| 7 | `RDD_SPLIT/{train,val}` | `RDD` | keep class 3 (D40 pothole) → 0 | 6,340 |
| 8 | `cincinnati/**` + `labels/*.txt` | `Cincinnati` | **only with `--cincinnati`**; images ≤ 5 KB skipped | — |

Key details:

- **Upstream splits are ignored.** All of a source's pairs are pooled, shuffled with a single `random.Random(seed)`, and the first `int(n × train_ratio)` go to train. The rest go to val.
- `add_yolo_dir(..., cls_map=)` drops any class not in `cls_map` and remaps the kept ones. An image whose labels are all dropped (or empty) is skipped.
- `add_segmentation_dir` turns each polygon (≥ 3 points) into its bounding box.
- **Filename collisions** across sources are resolved by prefixing the later source's stem (`<source>_<stem>`).
- Outputs in `<out>/`: `data.yaml` (relative `path: .`), `build_manifest.json` (seed, ratio, `cincinnati_included`, per-source train/val counts), and `SOURCES.md` (attribution + license table).
- Refuses to write into a non-empty output dir unless `--force` is given.

## Usage

```bash
.venv/bin/python scripts/build_dataset.py                 # publishable build → datasets/combined_dataset
.venv/bin/python scripts/build_dataset.py --out datasets/_upload_PotholesCombined
.venv/bin/python scripts/build_dataset.py --cincinnati --force   # local-only build incl. Cincinnati
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--repo-root` | `.` | Everything else resolves against it |
| `--sources-dir` | `<repo-root>/datasets` | Where the upstream datasets are |
| `--out` | `<sources-dir>/combined_dataset` | Output dir |
| `--cincinnati` | off | Include Cincinnati 311 pairs (**never for publishing**) |
| `--cincinnati-images` / `--cincinnati-labels` | `cincinnati` / `labels` | Cincinnati roots |
| `--train-ratio` | `0.85` | Train fraction per source |
| `--seed` | `42` | Shuffle seed |
| `--force` | off | Allow a non-empty output dir |

## Datasets currently on disk

| Dataset | Images (train / val) | Cincinnati | Built by | Used for |
| --- | --- | --- | --- | --- |
| `datasets/combined_dataset` | 19,547 (16,468 / 3,079) | **yes** | an **earlier** version of the merge script (no `build_manifest.json`) | 50-epoch runs, night sweep, RF-DETR |
| `datasets/_upload_PotholesCombined` (`datasets/data_nocincinnati.yaml`) | 16,641 (14,139 / 2,502) | no | `build_dataset.py`, seed 42, 2026-09-03 | clean fine-tunes; staging dir for the HuggingFace upload |

> [!warning] The two splits are not compatible
> Because `combined_dataset` was split by an older script, **954 of the clean val images are in `combined_dataset/train`**. Never evaluate a model trained on `combined_dataset` on the full clean val split. Use the held-out subset in [[Models_and_Accuracy]].

## Related

- `docs/BUILDING_THE_DATASET.md`: full per-source credits and licenses
- [[Training]] · [[Models_and_Accuracy]] · [[Known_Issues]]
