# Overnight training sweep

A pair of systemd **user** timers train four detectors back-to-back on
`datasets/combined_dataset`, every night between **23:00 and 08:30**, each from
its stock COCO-pretrained weights:

```
yolo11s  ->  yolo26s  ->  yolo11m  ->  yolo26m
```

A model only starts once its predecessor has reached the epoch budget
(`STREETSMART_EPOCHS`, default **300**). Each model has its own run directory
`runs/night-<model>/` and is resumed night after night; when the window runs
out the current model is checkpointed (`SIGINT` -> `last.pt`) and resumes the
next night. When all four are done a summary notification ranks their final
mAP, and later nights become no-ops.

## How it works

- `streetsmart-night.timer` -> `streetsmart-night.service` at **23:00** runs
  `scripts/night_train.sh`.
- `streetsmart-night-stop.timer` -> `streetsmart-night-stop.service` at
  **08:30** runs `systemctl --user stop streetsmart-night.service`
  (`KillSignal=SIGINT`, so Ultralytics checkpoints before exit).
- `night_train.sh`:
  1. **Window guard** — exits immediately outside 23:00–08:30, so a delayed or
     manual trigger never starts after 08:30. The timer has no `Persistent=`,
     so a run missed while the machine was off is not caught up.
  2. Walks the model list in order. For the first not-yet-finished model it
     sends a **start** notification, trains (fresh from `<model>.pt`, or
     `resume` of `runs/night-<model>/weights/last.pt`), then sends an **end**
     notification with every box metric `before -> after (Δ)`:
     ```
     night training: yolo26s ended
     epoch 140 -> 205 / 300   (9h12m, exit 0)
     precision   0.7412 -> 0.7690   (Δ +0.0278)
     recall      0.6001 -> 0.6233   (Δ +0.0232)
     mAP50       0.6810 -> 0.7050   (Δ +0.0240)
     mAP50-95    0.3720 -> 0.3985   (Δ +0.0265)
     ```
  3. If that model reached the budget it advances to the next one **the same
     night** (if the window is still open); otherwise it stops and resumes
     next night.
  4. When every model is complete, a one-time **sweep complete** notification:
     ```
     final metrics  ·  mAP50-95 / mAP50 (epoch)
     yolo11s    0.3xxx / 0.6xxx  (ep 300)
     yolo26s    0.3xxx / 0.7xxx  (ep 300)
     yolo11m    0.4xxx / 0.7xxx  (ep 300)
     yolo26m    0.4xxx / 0.7xxx  (ep 300)
     ```

## What is tracked

| Where | Content |
| --- | --- |
| `runs/night-<model>/results.csv` | **Full per-epoch history** for that model. Ultralytics appends to it on every resume, so the whole training curve across all nights is preserved (also `results.png` and the PR/F1 curve PNGs, regenerated each epoch). |
| `runs/streetsmart_night_metrics.csv` | Append-only **session history**: one row per start and per end — `timestamp,model,event,epoch,precision,recall,mAP50,mAP50-95,elapsed_s,exit`. The night-by-night trajectory in one file. |
| `runs/streetsmart_night.log` | Human-readable log of every notification. |
| journal | `journalctl --user -u streetsmart-night` — full Ultralytics stdout. |

## Install

```bash
cd ~/potholes
cp systemd/streetsmart-night*.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now streetsmart-night.timer streetsmart-night-stop.timer
systemctl --user list-timers 'streetsmart-*'
```

## Notes / limits

- **Linger is off** (by choice): timers fire only while you are logged in, and
  logging out mid-run stops training (it resumes fine next night). `notify-send`
  always reaches the desktop this way. `loginctl enable-linger $USER` lets it
  run while logged out (desktop notifications then usually won't show; the CSVs
  and log still update).
- Machine **waking from suspend before 08:30** runs the missed 23:00 start for
  the rest of the window; after 08:30 the guard blocks it.
- Batch sizes: `yolo*s` = 16, `yolo*m` = 8 (8 GB GPU). Override per class with
  `STREETSMART_BATCH_S` / `STREETSMART_BATCH_M`.
- Other tunables (`systemctl --user edit streetsmart-night.service`):
  `STREETSMART_EPOCHS`, `STREETSMART_MODELS` (space-separated order),
  `STREETSMART_IMGSZ`, `STREETSMART_DEVICE`, `STREETSMART_WIN_START`,
  `STREETSMART_WIN_END`, `STREETSMART_REPO`.
- **Re-run one model from scratch**: `rm -rf runs/night-<model>` (and delete
  `runs/.night_sweep_summary_sent`), then let the timer pick it up.
- Manual run: `systemctl --user start streetsmart-night.service` (still
  window-guarded), or bypass the guard for a quick test:
  `STREETSMART_WIN_START=0000 STREETSMART_WIN_END=0000 STREETSMART_MODELS=yolo11n \
  STREETSMART_EPOCHS=2 STREETSMART_FRACTION=0.03 scripts/night_train.sh`
- Watch: `journalctl --user -u streetsmart-night -f`.
