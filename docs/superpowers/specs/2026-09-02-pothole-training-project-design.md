# Pothole Detection — Training & Dataset Packaging Project

**Date:** 2026-09-02
**Status:** Approved (brainstorming)

## Goal

Turn the ad-hoc pothole-detection workspace at `/home/ad/potholes` into a
reproducible project:

- A **standalone training script** (`train.py`) that replaces the inline
  `python -c` blocks in `queue_yolo26*.sh`.
- A **standalone dataset-building script** (`scripts/build_dataset.py`) that
  reproduces `datasets/combined_dataset/` from the 8 upstream sources.
- **Docs** describing how to build the dataset, with per-source credits and
  licenses.
- A **git repo** (LFS for weights) containing the code, an organized `models/`
  tree, and the `runs/` training outputs (videos excluded).
- A **project venv** (`.venv`, Python 3.12, torch cu128 + ultralytics).

Publishing targets (later, not in this task):
- **HuggingFace** — the combined dataset (Cincinnati images excluded),
  `build_dataset.py`, and `docs/BUILDING_THE_DATASET.md`.
- **GitHub** — everything in the repo. No remote is added and nothing is
  pushed in this task.

## Decisions

| Question | Decision |
| --- | --- |
| Training backends | Ultralytics YOLO only (detect + seg). No RF-DETR in `train.py`. |
| Dataset build logic | Provided by user (heredoc script); productionize it. |
| Large model files | Git LFS for `*.pt/*.pth/*.ckpt`. Drop RF-DETR `last.ckpt` + `checkpoint_9/19/29.ckpt` (~1.9 GB). Keep `checkpoint_best_*`. |
| venv | `.venv` from `miniconda3/envs/comfy/bin/python3.12`; `torch==2.10.0` + `torchvision==0.25.0` (cu128 index), `ultralytics==8.4.9`, `huggingface_hub`. |
| Cincinnati images | **Not** published. `build_dataset.py` makes Cincinnati opt-in (`--cincinnati`, default off). Default build = HF-publishable. |
| Paths in scripts | Relative only. Sources resolved against `--repo-root` (default `.`). |
| Repo root | `/home/ad/potholes` with a strict `.gitignore`. |
| Licenses | Per-source, from each source's own README: `dataset/` = ODbL v1.0; `Pothole-detection-Yolov8/`, BharatPotHole, Curated RGB = CC BY 4.0; PothRGBD/PData = MIT; RDD2022 = CC BY-SA 4.0; HRP4K = unknown, assume CC BY-SA 4.0. Project-added files = CC BY-SA 4.0. |

## Repo layout

```
potholes/
├── .venv/                       (gitignored)
├── .gitignore                   ignores .venv, datasets/, cincinnati/, labels/,
│                                *.mp4, stock yolo*.pt, *.pdf, *.zip
├── .gitattributes               LFS: *.pt *.pth *.ckpt *.png *.jpg *.jpeg *.JPG
├── README.md
├── requirements.txt
├── train.py
├── scripts/
│   └── build_dataset.py
├── docs/
│   ├── BUILDING_THE_DATASET.md
│   └── superpowers/specs/2026-09-02-pothole-training-project-design.md
├── models/
│   ├── pretrained/
│   │   └── pothole_yolov8_best.pt
│   └── trained/
│       ├── yolov8s-combined/    best.pt, args.yaml, results.csv, results.png, *_curve.png
│       ├── yolo26s-combined/    "
│       ├── yolo26m-combined/    "
│       ├── pothrgbd-seg/        best.pt, args.yaml, results.csv, results.png, Mask*_curve.png
│       └── rfdetr-base/         checkpoint_best_ema.pth, metrics.csv, training_config.json
└── runs/                        existing outputs, videos removed, heavy RF-DETR ckpts removed
```

Not in git (stay on disk only): `datasets/`, `cincinnati/`, `labels/`,
`*.mp4`, stock `yolo12n.pt`/`yolo26*.pt`, `2505.04207v1.pdf`.

## `train.py`

Single file, stdlib + `ultralytics` only. `argparse` CLI:

| Flag | Default | Notes |
| --- | --- | --- |
| `--model` | `yolo26s.pt` | path or ultralytics name |
| `--data` | `datasets/combined_dataset/data.yaml` | |
| `--epochs` | `50` | |
| `--imgsz` | `640` | |
| `--batch` | `16` | |
| `--patience` | `10` | |
| `--device` | `0` | |
| `--project` | `runs` | |
| `--name` | derived from model stem + data stem | |
| `--workers` | `2` | |
| `--seed` | `0` | |
| `--amp / --no-amp` | `--amp` | |
| `--resume` | off | |
| `--val / --no-val` | `--val` | run `model.val()` after training |
| `--set KEY=VALUE` | repeatable | passthrough to `model.train()` |

Behavior: resolve config, print it, `YOLO(model).train(**cfg)`, optional
`model.val()`, exit non-zero on exception. No conda `sys.path` hacks, no
`pgrep` queue logic.

## `scripts/build_dataset.py`

Productionized version of the user's heredoc. `argparse` CLI:

| Flag | Default |
| --- | --- |
| `--repo-root` | `.` |
| `--sources-dir` | `<repo-root>/datasets` |
| `--out` | `<repo-root>/datasets/combined_dataset` |
| `--cincinnati-images` | `<repo-root>/cincinnati` |
| `--cincinnati-labels` | `<repo-root>/labels` |
| `--cincinnati` | off — include Cincinnati pairs when set |
| `--train-ratio` | `0.85` |
| `--seed` | `42` |

Sources and remaps (unchanged from the provided logic):

1. BharatPotHole — train/valid/test, classes as-is
2. HRP4K — train/valid/test
3. Curated RGB — `cls_map={1: 0}` (pothole only)
4. Roboflow "Potholes Detection" (`Pothole-detection-Yolov8/`) — train/valid/test
5. `dataset/` generic (GoPro frames) — train/valid/test, images+labels co-located
6. PData / PothRGBD — polygon segmentation → axis-aligned bbox
7. RDD2022 (`RDD_SPLIT/`) — keep class `3` only, remap to `0`
8. Cincinnati — only with `--cincinnati`; non-empty labels only, image > 5 KB

Fixes vs. the heredoc:
- Remove the `stats_total_train` `NameError` in the summary.
- All paths relative / CLI-driven; no `/home/ad/...`.
- Basename-collision guard: if two sources yield the same file stem, prefix
  the later one with `<source>_` instead of silently overwriting.
- Emit into `--out`: `data.yaml` (nc=1, names={0: pothole}),
  `build_manifest.json` (per-source train/val counts, seed, ratio, timestamp,
  `cincinnati_included`), and `SOURCES.md` (credits table).
- `--seed` controls a single `random.Random(seed)` instance, not global.

## `docs/BUILDING_THE_DATASET.md`

Prose: prerequisites, expected `datasets/` layout, the one command to run,
what gets written. Plus the credits table:

Licenses are those stated in each source's own README/metadata; where none is
stated, CC BY-SA 4.0 is assumed and marked as such.

| Source | Attribution | License |
| --- | --- | --- |
| Roboflow "Pothole" raw (`dataset/`) | Atikur Rahman Chitholian | ODbL v1.0 |
| Roboflow "Potholes Detection" (`Pothole-detection-Yolov8/`) | Roboflow Universe `project-ssayl` | CC BY 4.0 |
| PothRGBD (`PData/`) | Yurdakul & Taşdemir, 2025 (arXiv:2505.04207) | MIT |
| RDD2022 (`RDD_SPLIT/`) | Arya et al., Road Damage Detection | CC BY-SA 4.0 |
| BharatPotHole | BharatPotHole authors | CC BY 4.0 |
| A Curated RGB Dataset for Real-Time Road Damage Detection | dataset authors (Mendeley Data) | CC BY 4.0 |
| HRP4K | HRP4K authors | CC BY-SA 4.0 (not stated; assumed) |
| Cincinnati 311 pothole imagery | City of Cincinnati / CAGIS | Not redistributed — excluded from the published dataset |

The dataset is an aggregate — each source keeps its own license. The
`dataset/` (Chitholian) portion is ODbL v1.0 and its share-alike terms
continue to apply. Project-added files (split layout, `data.yaml`, manifests,
`build_dataset.py`) are released under CC BY-SA 4.0.

## Models organization (`models/`)

Copied (LFS dedupes identical blobs by hash) from `runs/`:

- `pretrained/pothole_yolov8_best.pt` ← repo-root `pothole_yolov8_best.pt`
- `trained/yolov8s-combined/` ← `runs/detect/runs/combined_pothole/`
- `trained/yolo26s-combined/` ← `runs/detect/runs/combined_yolo26s/`
- `trained/yolo26m-combined/` ← `runs/detect/runs/combined_yolo26m/`
- `trained/pothrgbd-seg/` ← `runs/pothrgbd_seg/`
- `trained/rfdetr-base/` ← `runs/rfdetr_base/checkpoint_best_ema.pth` + `metrics.csv` + `training_config.json`

Each `trained/*` dir gets `best.pt` (or best checkpoint), `args.yaml`/config,
`results.csv`, and the summary `results.png` / curve PNGs. Full raw output
stays under `runs/`.

## Out of scope

- Creating GitHub/HF remotes or uploading anything.
- Rebuilding `datasets/combined_dataset/` (the script is delivered and
  documented; not executed here).
- RF-DETR training code.
- Any change to `queue_yolo26*.sh` (left as-is).

## Verification

- `.venv/bin/python -c "import torch, ultralytics; assert torch.cuda.is_available()"`
- `.venv/bin/python train.py --help` and `scripts/build_dataset.py --help` exit 0.
- `python -m py_compile train.py scripts/build_dataset.py`.
- `git status` clean after initial commit; `git lfs ls-files` lists the weights.
- No absolute paths in `train.py` / `build_dataset.py` (`grep -n "/home/"`).
- `git ls-files` contains no `.mp4`, no `datasets/`, no `cincinnati/`.
