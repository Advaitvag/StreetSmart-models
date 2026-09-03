# Overnight training window

A pair of systemd **user** timers train the best model every night between
**23:00 and 08:30**, resuming where the previous night stopped.

## How it works

- `streetsmart-night.timer` → `streetsmart-night.service` at **23:00**
  runs `scripts/night_train.sh`.
- `streetsmart-night-stop.timer` → `streetsmart-night-stop.service` at
  **08:30** runs `systemctl --user stop streetsmart-night.service`, which
  sends `SIGINT` so Ultralytics checkpoints `last.pt` before exiting.
- `night_train.sh`:
  1. **Window guard** — exits immediately if the clock is not within
     23:00–08:30, so a delayed or manual trigger never starts after 08:30.
     There is no `Persistent=` on the timer, so a run missed while the
     machine was off is not caught up either.
  2. Sends a **start** notification (`notify-send`) with the current
     `epoch`, precision, recall, mAP50, mAP50-95.
  3. Runs one dedicated Ultralytics run, `runs/streetsmart-night/`:
     - **first night** — starts from `models/trained/yolo26m-combined/weights/best.pt`
       with a budget of `STREETSMART_EPOCHS` (default **600**), early
       stopping disabled.
     - **every later night** — `resume=last.pt` for that same run.
     - when the budget is reached it stops training and the nightly job
       just notifies "nothing to do".
  4. Sends an **end** notification: elapsed time, exit code, and every box
     metric `before -> after` with its delta:
     ```
     epoch 137 -> 189 / 600   (9h27m, exit 0)
     precision   0.7664 -> 0.7810   (Δ +0.0146)
     recall      0.6464 -> 0.6591   (Δ +0.0127)
     mAP50       0.7200 -> 0.7358   (Δ +0.0158)
     mAP50-95    0.4164 -> 0.4302   (Δ +0.0138)
     ```
- Every notification is also appended to
  `runs/streetsmart-night/night_train.log`.

## Install

```bash
cd ~/potholes
cp systemd/streetsmart-night*.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now streetsmart-night.timer streetsmart-night-stop.timer
```

Check:

```bash
systemctl --user list-timers 'streetsmart-*'
```

## Notes / limits

- **Linger is off** (by choice): the timers only fire while you are logged
  into a session, and if you log out mid-run the user manager stops the
  training. `notify-send` always reaches the desktop this way. To let it run
  while logged out: `loginctl enable-linger $USER` (desktop notifications
  will then usually not appear; the logfile still gets every line).
- If the machine **wakes from suspend before 08:30**, systemd fires the
  missed 23:00 start and training runs for the rest of the window. After
  08:30 the guard blocks it.
- Tunables via the service environment (`systemctl --user edit
  streetsmart-night.service`): `STREETSMART_EPOCHS`, `STREETSMART_BATCH`,
  `STREETSMART_IMGSZ`, `STREETSMART_DEVICE`, `STREETSMART_WIN_START`,
  `STREETSMART_WIN_END`, `STREETSMART_REPO`.
- Run once by hand: `systemctl --user start streetsmart-night.service`
  (still subject to the time-window guard), or
  `STREETSMART_WIN_START=0000 STREETSMART_WIN_END=0000 scripts/night_train.sh`
  to bypass the guard for a test.
- Watch it: `journalctl --user -u streetsmart-night -f`.
