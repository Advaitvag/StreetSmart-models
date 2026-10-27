---
type: code-doc
component: Training
source: train.py, scripts/night_train.sh, scripts/train_nocincinnati.sh, systemd/, queue_yolo26*.sh
tags:
  - code
  - training
---

# Training

## Purpose

Train Ultralytics YOLO detectors on the combined pothole dataset. There are three entry points, each for a different job:

| Entry point | Use for | Produced |
| --- | --- | --- |
| `train.py` | One-off / experimental runs | `runs/<model>-<dataset>/` by default |
| `scripts/night_train.sh` (+ systemd timers) | Unattended long runs that compare architectures | `runs/night-{yolo11s,yolo26s,yolo26m,yolo11m}/` |
| `scripts/train_nocincinnati.sh` | Fine-tuning the night models on Cincinnati-free data | `runs/clean-{yolo26s,yolo26m}/` |
| `scripts/train_clean.sh` | **Clean run**: fresh YOLO26m, 200 epochs, Cincinnati-free leak-free split, final test score | `runs/clean200-yolo26m/` |
| `queue_yolo26s.sh`, `queue_yolo26m.sh` | *Legacy.* Inline `python -c` launchers that produced the 50-epoch runs in `runs/detect/runs/` | superseded by `train.py` |

## `train.py`

A thin CLI over `YOLO(model).train(**kwargs)`, followed by `model.val()`.

- Default dataset: `datasets/combined_dataset/data.yaml`, resolved against the repo root. The script exits with code 2 if the YAML is missing.
- Default run name: `<model-stem>-<dataset-dir-name>`, under `--project runs`.
- `--set KEY=VALUE` (repeatable) forwards any Ultralytics train argument. Values are typed automatically (`true`/`false` → bool, `none`/`null` → None, then int, then float, else string).
- Exit codes: 0 = ok, 1 = ultralytics missing or training raised an exception, 2 = dataset YAML not found.

| Flag | Default |
| --- | --- |
| `--model` | `yolo26s.pt` (path or Ultralytics name; stock weights auto-download) |
| `--data` | `datasets/combined_dataset/data.yaml` |
| `--epochs` / `--imgsz` / `--batch` / `--patience` | 50 / 640 / 16 / 10 |
| `--device` | `0` |
| `--workers` / `--seed` | 2 / 0 |
| `--amp` / `--no-amp`, `--val` / `--no-val` | AMP on, final val on |
| `--resume`, `--exist-ok` | off |

```bash
.venv/bin/python train.py --model yolo26m.pt --batch 8 --name yolo26m-combined
.venv/bin/python train.py --model yolo26s.pt --data datasets/data_nocincinnati.yaml --epochs 100
.venv/bin/python train.py --model yolo26s.pt --set cos_lr=true --set close_mosaic=15
```

## Night sweep: `scripts/night_train.sh`

Trains a list of models **one after another**, each from stock COCO weights to `STREETSMART_EPOCHS` (300) on `combined_dataset`, with no early stopping (`patience=0`). A model starts only after its predecessor reaches the budget. The current model is interrupted at the end of the nightly window and resumed from `last.pt` the next night.

How one invocation runs:

1. **Window guard.** If the time is outside `WIN_START`–`WIN_END` (default 23:00–08:30), it logs and exits.
2. If every model is done, it sends a one-time summary notification (marker file `runs/.night_sweep_summary_sent`) and exits.
3. For the first unfinished model:
   - Send a "start" notification.
   - Append a `start` row to `runs/streetsmart_night_metrics.csv`.
   - Launch Python in the background: `YOLO(last.pt).train(resume=...)`, or a fresh `train(...)` from `<model>.pt`.
4. SIGINT/SIGTERM is trapped and forwarded as **SIGINT** to the Python child, so Ultralytics writes `last.pt` before exiting.
5. Afterwards it reads the last row of the run's `results.csv`, appends an `end` row, and notifies with before → after (Δ) for precision, recall, mAP50 and mAP50-95.
6. "Done" means a `.done` marker exists or the last epoch is ≥ `EPOCHS − 1`. If done, it touches `.done` and continues with the next model the same night. Otherwise it stops.

| Env var | Default |
| --- | --- |
| `STREETSMART_REPO` | `/home/ad/potholes` |
| `STREETSMART_MODELS` | `yolo11s yolo26s yolo26m yolo11m` |
| `STREETSMART_EPOCHS` | `300` |
| `STREETSMART_BATCH_S` / `_BATCH_M` | `16` for `*s`, `8` for everything else |
| `STREETSMART_IMGSZ` / `_DEVICE` / `_FRACTION` | `640` / `0` / `1.0` (`<1` only for smoke tests) |
| `STREETSMART_WIN_START` / `_WIN_END` | `2300` / `0830` (HHMM) |

**systemd user units** (`systemd/`, install to `~/.config/systemd/user/`):

| Unit | Role |
| --- | --- |
| `streetsmart-night.timer` | Daily 23:00 → starts the service. No `Persistent=`, so missed nights are not caught up. |
| `streetsmart-night.service` | Runs `night_train.sh`. `KillSignal=SIGINT`, `KillMode=mixed`, `TimeoutStopSec=300`, `Nice=10`. Only starts if the dataset YAML exists. |
| `streetsmart-night-stop.timer` → `streetsmart-night-stop.service` | `systemctl --user stop streetsmart-night.service`. The file currently fires at **11:30**, not 08:30 (see [[Known_Issues]]). |

**Status as of 2026-10-08:** all four night models have a `.done` marker (300 epochs each), and no StreetSmart timers are active.

Outputs:

- `runs/night-<model>/results.csv`: per-epoch history, appended across resumes
- `runs/streetsmart_night_metrics.csv`: one row per session start/end
- `runs/streetsmart_night.log`: notification log
- Full stdout: `journalctl --user -u streetsmart-night`

See also `docs/NIGHT_TRAINING.md` (install, monitor, reset instructions).

## Clean fine-tuning: `scripts/train_nocincinnati.sh`

Same structure as the night script (notifications, metrics CSV, SIGINT checkpointing, resume, `.done` markers), with these differences:

- **No time window.** It can be started any time, interactively or in the background.
- Dataset: `datasets/data_nocincinnati.yaml` → `datasets/_upload_PotholesCombined` (no Cincinnati).
- Models: `yolo26s yolo26m`, 100 epochs each, `patience=0`.
- Starting weights: `runs/night-<model>/weights/best.pt`, falling back to `last.pt`, then stock `<model>.pt`.
- Outputs: `runs/clean-<model>/`, `runs/streetsmart_clean_metrics.csv`, `runs/streetsmart_clean_train.log`.

**Status:** `clean-yolo26s` finished 100 epochs. `clean-yolo26m` was stopped at epoch 43 (2026-09-17). Run the script again to resume it.

> [!warning] Don't trust these runs' logged val metrics
> Their val split overlaps the night models' training data, so the logged mAP peaks at epoch 1 and then falls. Held-out evaluation shows these fine-tunes score slightly *below* their night starting points. See [[Models_and_Accuracy]].

## Problems with the night and clean-v1 runs

1. **Cincinnati in training and selection.** The night runs trained on `combined_dataset`, which has Cincinnati 311 images with ML-made labels in both train and val. So `best.pt` was also picked partly against those labels.
2. **Leaky splits.** Augmented copies, clip frames and capture runs sit on both sides of every split (see [[Dataset_Builder]]). Logged val mAP is inflated and the `best.pt` pick is unreliable.
3. **clean-v1 isn't clean.** `train_nocincinnati.sh` starts from night weights, which already saw Cincinnati and 954 of its val images.
4. **The held-out eval set leaks too.** The recipe in [[Models_and_Accuracy]] removes only byte-identical images. 834 of its 1,548 images (54%) still have an augmented copy, a frame of the same clip or a near-duplicate in the training data.
5. **Stops never checkpointed.** A background command of a non-interactive bash starts with SIGINT *ignored*, and Python keeps it ignored. The trap's `kill -INT` did nothing, so every stop ended in SIGKILL after `TimeoutStopSec`: 32 starts but only 22 end rows in `streetsmart_night_metrics.csv`, and repeated "stop signal" log lines. Resume still worked from the last epoch's `last.pt`, but the partial epoch was lost, and a kill during a save could corrupt `last.pt`.
6. **Off-by-one "done".** `results.csv` epochs are 1-based, but `is_done` accepted `EPOCHS − 1`. A run stopped after epoch 299 of 300 counted as finished.

## Clean run: `scripts/train_clean.sh`

One model, one run, fixing all of the above:

- Data: `datasets/clean_split` (built on first use by `scripts/build_clean_split.py`, see [[Dataset_Builder]]). Train for gradients, val for `best.pt` selection, test only for the final score.
- Start: stock COCO `yolo26m.pt`, never a night checkpoint. `STREETSMART_INIT=scratch` uses `yolo26m.yaml` with random init instead.
- 200 epochs, batch 8, 640 px, `patience=0`, seed 0. Otherwise Ultralytics defaults, as in the night runs.
- No time window. Run it any time; re-running resumes from `last.pt`.
- **Stopping works.** The Python child catches SIGINT/SIGTERM and stops at the next batch boundary, or right after `last.pt` is written if validation is running, so it never stops mid-save. It exits 130; run the script again to resume. A second Ctrl-C is harmless.
- Done = 200 epochs **and** the test evaluation. Then `best.pt` is scored (conf 0.001, iou 0.7) on the test split, and on the unseen-by-night subset next to `runs/night-yolo26m/weights/best.pt`. The scores go to `runs/clean200-yolo26m/test_metrics.json` and a notification, and `.done` is written.
- Logs: `runs/streetsmart_clean200-yolo26m.log`, `runs/streetsmart_clean200-yolo26m_metrics.csv`. The split manifest is copied into the run dir.

| Env var | Default |
| --- | --- |
| `STREETSMART_MODEL` / `_INIT` | `yolo26m` / `pretrained` (`scratch` = random init) |
| `STREETSMART_EPOCHS` / `_BATCH` / `_IMGSZ` | `200` / `8` / `640` |
| `STREETSMART_NAME` | `clean200-<model>` |
| `STREETSMART_DEVICE` / `_WORKERS` / `_FRACTION` | `0` / `8` / `1.0` (`<1` only for smoke tests) |
| `STREETSMART_COMPARE` | `runs/night-yolo26m/weights/best.pt` |

```bash
nohup scripts/train_clean.sh >>runs/streetsmart_clean200.out 2>&1 &
kill -INT <script pid>       # stop + checkpoint; run the script again to resume
```

## Run history

| Run dir | Script | Data | Epochs | Batch |
| --- | --- | --- | --- | --- |
| `runs/detect/runs/combined_pothole` | early inline run, fine-tuned from `models/pretrained/pothole_yolov8_best.pt` | combined | 50 (patience 10) | 16 |
| `runs/detect/runs/combined_yolo26s` | `queue_yolo26s.sh` | combined | 50 | 16 |
| `runs/detect/runs/combined_yolo26m` | `queue_yolo26m.sh` | combined | 50 | 8 |
| `runs/rfdetr_base` | RF-DETR (script not in repo) | combined | 30 | 2 × 4 accum, 560 px |
| `runs/pothrgbd_seg` | YOLO11n-seg (script not in repo) | PData only | 100 budget, early-stopped at 94 (patience 15) | 16 |
| `runs/night-*` | `night_train.sh` | combined | 300 | 16 / 8 |
| `runs/clean-*` | `train_nocincinnati.sh` | Cincinnati-free | +100 / +43 | 16 / 8 |

## Related

- [[Dataset_Builder]] · [[Models_and_Accuracy]] · [[Setup]]
