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

> [!warning] Both splits leak near-identical images between train and val
> `build_dataset.py` splits image by image, but most sources are not independent images:
> - Roboflow exports (BharatPotHole, PothRGBD, CuratedRGB, Roboflow-YOLOv8, part of `dataset/`) hold **3 augmented copies of each photo** (`<name>_jpg.rf.<hash>.jpg`). In `_upload_PotholesCombined`, 612 val images have a copy in train.
> - BharatPotHole is **frames of 85 dashcam clips** (1,342 originals × 3 copies); `dataset/` `G*.JPG` are GoPro sequences; PothRGBD captures are seconds apart.
> - 24 label files mix polygon and box lines. Ultralytics then reads every line as a polygon, which turns the box lines into wrong boxes.
>
> `scripts/build_clean_split.py` fixes all three for training (below).

## Leak-free split (`scripts/build_clean_split.py`)

Re-splits `_upload_PotholesCombined` (both splits pooled) into `datasets/clean_split/{train,val,test}`, 80 / 10 / 10 per source. Whole **groups** go to one split. A group joins images that share file contents, a Roboflow original, a drive (BharatPotHole clips < 2 min apart, GoPro frames < 20 numbers apart, PothRGBD captures < 60 s apart) or a near-duplicate (256-bit dHash, flip-aware, distance ≤ 22; random road pairs are ≥ 43).

- Images are relative symlinks into the pool. Labels are rewritten as clean boxes (polygons → boxes, clipped to [0, 1], degenerate and duplicate boxes dropped).
- Refuses to build if any image is byte-identical to a file under `cincinnati/` or is named `SR*`.
- Verifies no group link crosses splits, then writes `data.yaml` (absolute `path`, with `test:`) and `split_manifest.json` (counts, groups, label fixes).
- Also writes `test_unseen_by_night.txt` / `data_unseen_by_night.yaml`: the test images whose whole group is absent from `combined_dataset/train`. Only on this subset can the night models be compared fairly with new runs.
- Deterministic for a given pool and `--seed` (default 0). It needs numpy + Pillow, so run it with the venv.

Build of 2026-10-19: 16,641 → 16,556 images (85 exact duplicates dropped) in 10,581 groups. Train 13,228 / val 1,671 / test 1,657. 208 test images are unseen by the night runs (116 RDD, 51 GoPro, 34 HRP4K, 7 other).

```bash
.venv/bin/python scripts/build_clean_split.py            # -> datasets/clean_split
.venv/bin/python scripts/build_clean_split.py --force    # rebuild
```

## Related

- `docs/BUILDING_THE_DATASET.md`: full per-source credits and licenses
- [[Training]] · [[Models_and_Accuracy]] · [[Known_Issues]]
