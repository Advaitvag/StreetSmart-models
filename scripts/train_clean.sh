#!/usr/bin/env bash
# Clean YOLO26m run: fresh start, Cincinnati-free, leak-free split.
#
# Fixes the problems of the night / clean-v1 runs (see
# StreetSmart_docs/Code/Training.md):
#
#   * no Cincinnati 311 images (ML-made labels) anywhere;
#   * no inherited weights: starts from stock COCO yolo26m.pt (or a random
#     init with STREETSMART_INIT=scratch), never from a night checkpoint;
#   * trains on datasets/clean_split (scripts/build_clean_split.py, built on
#     first use): Roboflow copies, video clips, capture runs and near-duplicates
#     stay inside one split, so val (model selection) and test (final report)
#     are genuinely unseen;
#   * Ctrl-C / SIGTERM really checkpoints and stops: the old scripts' Python
#     child inherited SIGINT=ignored, so stops ended in SIGKILL. Here the stop
#     is deferred to a batch boundary or just after last.pt is written, never
#     mid-save;
#   * "done" means all EPOCHS (1-based results.csv) plus the test evaluation.
#
#     datasets/_upload_PotholesCombined -> datasets/clean_split
#     yolo26m.pt (COCO) -> runs/clean200-yolo26m (200 epochs, batch 8)
#
# Run it any time; re-running resumes from last.pt. After training, best.pt is
# scored once on the test split and on the test images the night runs never
# saw (with runs/night-yolo26m for comparison) -> runs/<name>/test_metrics.json.
#
#     nohup scripts/train_clean.sh >>runs/streetsmart_clean200.out 2>&1 &
#
# Other recipes (scripts/train_clean_1024.sh) set STREETSMART_* and exec this
# script; STREETSMART_HYP passes extra Ultralytics train args to a fresh run.

set -uo pipefail

REPO="${STREETSMART_REPO:-/home/ad/potholes}"
PY="$REPO/.venv/bin/python"
SPLIT="$REPO/datasets/clean_split"
DATA="$SPLIT/data.yaml"
MODEL="${STREETSMART_MODEL:-yolo26m}"
INIT="${STREETSMART_INIT:-pretrained}" # pretrained (COCO .pt) | scratch (.yaml)
NAME="${STREETSMART_NAME:-clean200-$MODEL}"
EPOCHS="${STREETSMART_EPOCHS:-200}"
BATCH="${STREETSMART_BATCH:-8}" # yolo*m on the 8 GB GPU
IMGSZ="${STREETSMART_IMGSZ:-640}"
DEVICE="${STREETSMART_DEVICE:-0}"
WORKERS="${STREETSMART_WORKERS:-8}"
FRACTION="${STREETSMART_FRACTION:-1.0}" # <1.0 only for smoke tests
HYP="${STREETSMART_HYP:-}"              # extra train args, "key=value ..." (fresh runs only)
COMPARE="${STREETSMART_COMPARE:-$REPO/runs/night-yolo26m/weights/best.pt}"
COMPARE_IMGSZ="${STREETSMART_COMPARE_IMGSZ:-640}" # the size COMPARE was trained at
RUN_DIR="$REPO/runs/$NAME"
APP="StreetSmart Clean Training"
LOG="$REPO/runs/streetsmart_$NAME.log"
METRICS_CSV="$REPO/runs/streetsmart_${NAME}_metrics.csv"

mkdir -p "$REPO/runs"
cd "$REPO" || exit 1

log() { printf '%s  %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
notify() { # <urgency> <title> <body>
  notify-send -a "$APP" -u "$1" "$2" "$3" 2>/dev/null || true
  log "[$2] ${3//$'\n'/ | }"
}

# Append-only session history
record() { # <event start|end> <epoch> <prec> <rec> <mAP50> <mAP50-95> <elapsed_s> <exit>
  [[ -f "$METRICS_CSV" ]] ||
    echo "timestamp,model,event,epoch,precision,recall,mAP50,mAP50-95,elapsed_s,exit" >"$METRICS_CSV"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$(date -Is)" "$NAME" "$1" "${2:-}" "${3:-}" "${4:-}" "${5:-}" "${6:-}" "${7:-}" "${8:-}" >>"$METRICS_CSV"
}

[[ -x "$PY" ]] || {
  notify critical "clean training aborted" "venv python missing: $PY"
  exit 1
}

if [[ ! -f "$DATA" ]]; then
  log "building leak-free split -> $SPLIT"
  "$PY" scripts/build_clean_split.py --repo-root "$REPO" | tee -a "$LOG" || {
    notify critical "clean training aborted" "scripts/build_clean_split.py failed"
    exit 1
  }
fi

# read_metrics <results.csv> -> "epoch precision recall mAP50 mAP50-95" (last row)
read_metrics() {
  [[ -f "$1" ]] || return 1
  "$PY" - "$1" <<'PY' 2>/dev/null
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
if not rows:
    sys.exit(1)
r = {k.strip(): v for k, v in rows[-1].items()}
def g(k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return float("nan")
epoch = int(float(next(iter(r.values()))))
print(f"{epoch} {g('metrics/precision(B)'):.4f} {g('metrics/recall(B)'):.4f} "
      f"{g('metrics/mAP50(B)'):.4f} {g('metrics/mAP50-95(B)'):.4f}")
PY
}

delta() { awk -v a="$1" -v b="$2" 'BEGIN { if (a == "") print "n/a"; else printf "%+.4f", b - a }'; }

# results.csv epochs are 1-based: the run is trained once the last row says EPOCHS
trained() {
  local m
  m="$(read_metrics "$RUN_DIR/results.csv" || true)"
  [[ -n "$m" ]] && ((${m%% *} >= EPOCHS))
}

# run_child <python heredoc on stdin>: run it in the background, forward the
# first INT/TERM as SIGINT, wait for it to finish checkpointing.
run_child() {
  stopping=0
  "$PY" - <&0 & # explicit <&0: async commands otherwise read /dev/null
  child=$!
  trap 'if ((!stopping)); then stopping=1; log "stop signal -> SIGINT $NAME ($child), finishing current batch"; kill -INT "$child" 2>/dev/null; fi' INT TERM
  wait "$child"
  rc=$?
  while kill -0 "$child" 2>/dev/null; do
    wait "$child"
    rc=$?
  done
  trap - INT TERM
  return "$rc"
}

if [[ -f "$RUN_DIR/.done" ]]; then
  log "$NAME already complete; results in $RUN_DIR/test_metrics.json"
  exit 0
fi

# --- train ------------------------------------------------------------------
if ! trained; then
  mkdir -p "$RUN_DIR"
  cp "$SPLIT/split_manifest.json" "$RUN_DIR/split_manifest.json"
  resuming=0
  [[ -f "$RUN_DIR/weights/last.pt" ]] && resuming=1

  sE=0 sP="" sR="" s50="" s5095=""
  if ((resuming)); then
    bm="$(read_metrics "$RUN_DIR/results.csv" || true)"
    [[ -n "$bm" ]] && read -r sE sP sR s50 s5095 <<<"$bm"
    notify normal "clean training: $NAME" \
      "resuming   epoch ${sE}/${EPOCHS}   batch ${BATCH}
precision ${sP}   recall ${sR}
mAP50 ${s50}   mAP50-95 ${s5095}"
  else
    notify normal "clean training: $NAME" \
      "fresh ${MODEL} (${INIT}) on clean_split
epoch 0/${EPOCHS}   batch ${BATCH}   imgsz ${IMGSZ}${HYP:+
${HYP}}"
  fi
  record start "$sE" "$sP" "$sR" "$s50" "$s5095" "" ""
  t0=$(date +%s)

  STREETSMART_RESUME="$resuming" \
    STREETSMART_RUNDIR="$RUN_DIR" \
    STREETSMART_MODEL="$MODEL" \
    STREETSMART_INIT="$INIT" \
    STREETSMART_NAME="$NAME" \
    STREETSMART_DATA="$DATA" \
    STREETSMART_EPOCHS="$EPOCHS" \
    STREETSMART_BATCH="$BATCH" \
    STREETSMART_IMGSZ="$IMGSZ" \
    STREETSMART_DEVICE="$DEVICE" \
    STREETSMART_WORKERS="$WORKERS" \
    STREETSMART_PROJECT="$REPO/runs" \
    STREETSMART_FRACTION="$FRACTION" \
    STREETSMART_HYP="$HYP" \
    run_child <<'PY'
import os
import signal
import yaml
from ultralytics import YOLO

# A background child of a non-interactive shell starts with SIGINT ignored.
# Record the request instead and stop at a safe point, never inside a save.
stop = []
def request_stop(signum, _frame):
    stop.append(signum)
signal.signal(signal.SIGINT, request_stop)
signal.signal(signal.SIGTERM, request_stop)

def maybe_stop(_trainer):
    if stop:
        raise KeyboardInterrupt(f"stop requested (signal {stop[0]})")

def with_stop(model):
    model.add_callback("on_train_batch_end", maybe_stop)
    model.add_callback("on_model_save", maybe_stop)  # right after last.pt
    return model

e = os.environ
last = os.path.join(e["STREETSMART_RUNDIR"], "weights", "last.pt")
# "cos_lr=true mixup=0.1" -> {"cos_lr": True, "mixup": 0.1}; a resume reuses last.pt's args
hyp = {k: yaml.safe_load(v) for k, v in (a.split("=", 1) for a in e["STREETSMART_HYP"].split())}
try:
    if e["STREETSMART_RESUME"] == "1" and os.path.exists(last):
        print(f"Resuming from {last}")
        with_stop(YOLO(last)).train(resume=last)
    else:
        scratch = e["STREETSMART_INIT"] == "scratch"
        base = e["STREETSMART_MODEL"] + (".yaml" if scratch else ".pt")
        print(f"Fresh run from {base} ({'random init' if scratch else 'COCO weights'})")
        with_stop(YOLO(base)).train(
            data=e["STREETSMART_DATA"],
            epochs=int(e["STREETSMART_EPOCHS"]),
            imgsz=int(e["STREETSMART_IMGSZ"]),
            batch=int(e["STREETSMART_BATCH"]),
            device=e["STREETSMART_DEVICE"],
            workers=int(e["STREETSMART_WORKERS"]),
            project=e["STREETSMART_PROJECT"],
            name=e["STREETSMART_NAME"],
            exist_ok=True,
            pretrained=not scratch,
            patience=0,   # train the full budget; best.pt is picked on the clean val
            seed=0,
            fraction=float(e["STREETSMART_FRACTION"]),
            **hyp,
        )
except KeyboardInterrupt as err:
    print(f"Stopped: {err}. Re-run the script to resume from {last}")
    raise SystemExit(130)
PY
  rc=$?

  dt=$(($(date +%s) - t0))
  elapsed="$(printf '%dh%02dm' $((dt / 3600)) $(((dt % 3600) / 60)))"
  em="$(read_metrics "$RUN_DIR/results.csv" || true)"
  if [[ -n "$em" ]]; then
    read -r eE eP eR e50 e5095 <<<"$em"
    record end "$eE" "$eP" "$eR" "$e50" "$e5095" "$dt" "$rc"
    notify normal "clean training: $NAME ended" \
      "epoch ${sE} -> ${eE} / ${EPOCHS}   (${elapsed}, exit ${rc})
precision   ${sP:-n/a} -> ${eP}   (Δ $(delta "${sP}" "$eP"))
recall      ${sR:-n/a} -> ${eR}   (Δ $(delta "${sR}" "$eR"))
mAP50       ${s50:-n/a} -> ${e50}   (Δ $(delta "${s50}" "$e50"))
mAP50-95    ${s5095:-n/a} -> ${e5095}   (Δ $(delta "${s5095}" "$e5095"))"
  else
    record end "" "" "" "" "" "$dt" "$rc"
    notify critical "clean training: $NAME ended" "no results.csv (exit ${rc}, ${elapsed})"
  fi

  if ! trained; then
    log "$NAME paused before ${EPOCHS} epochs — run again to resume"
    exit "$rc"
  fi
fi

# --- final evaluation on data no run has selected on --------------------------
log "evaluating $RUN_DIR/weights/best.pt on the test split"
STREETSMART_RUNDIR="$RUN_DIR" \
  STREETSMART_SPLIT="$SPLIT" \
  STREETSMART_COMPARE="$COMPARE" \
  STREETSMART_COMPARE_IMGSZ="$COMPARE_IMGSZ" \
  STREETSMART_IMGSZ="$IMGSZ" \
  STREETSMART_DEVICE="$DEVICE" \
  run_child <<'PY'
import json
import os
from pathlib import Path
from ultralytics import YOLO

e = os.environ
rundir, split = Path(e["STREETSMART_RUNDIR"]), Path(e["STREETSMART_SPLIT"])
unseen = split / "data_unseen_by_night.yaml"

imgsz, cmp_imgsz = int(e["STREETSMART_IMGSZ"]), int(e["STREETSMART_COMPARE_IMGSZ"])

def score(weights, data, part, label, sz=imgsz):
    b = YOLO(weights).val(data=str(data), split=part, imgsz=sz,
                          batch=max(1, 16 * 640**2 // sz**2), conf=0.001, iou=0.7,
                          device=e["STREETSMART_DEVICE"],
                          plots=False, project=str(rundir), name=f"eval_{label}",
                          exist_ok=True).box
    f1 = 2 * b.mp * b.mr / (b.mp + b.mr) if b.mp + b.mr else 0.0
    return {"precision": round(b.mp, 4), "recall": round(b.mr, 4), "f1": round(f1, 4),
            "mAP50": round(b.map50, 4), "mAP50-95": round(b.map, 4)}

best = rundir / "weights" / "best.pt"
out = {"weights": str(best), "protocol": f"imgsz {imgsz}, conf 0.001, iou 0.7",
       "test": score(best, split / "data.yaml", "test", "test")}
if unseen.exists():
    n = sum(1 for _ in open(split / "test_unseen_by_night.txt"))
    out["test_unseen_by_night"] = {"images": n,
                                   rundir.name: score(best, unseen, "val", "unseen")}
    if Path(e["STREETSMART_COMPARE"]).exists():
        cmp_name = Path(e["STREETSMART_COMPARE"]).parent.parent.name
        out["test_unseen_by_night"][cmp_name] = score(e["STREETSMART_COMPARE"], unseen, "val",
                                                      f"unseen_{cmp_name}", cmp_imgsz)
        out["test_unseen_by_night"]["compare_imgsz"] = cmp_imgsz
(rundir / "test_metrics.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
PY
rc=$?
if ((rc != 0)) || [[ ! -f "$RUN_DIR/test_metrics.json" ]]; then
  notify critical "clean training: $NAME" "test evaluation failed (exit ${rc}); re-run to retry"
  exit 1
fi

t="$("$PY" -c 'import json,sys; t=json.load(open(sys.argv[1]))["test"]; print(f"P {t["precision"]}  R {t["recall"]}  mAP50 {t["mAP50"]}  mAP50-95 {t["mAP50-95"]}")' "$RUN_DIR/test_metrics.json")"
notify normal "clean training complete: $NAME" "test split (never trained or selected on)
$t"
touch "$RUN_DIR/.done"
exit 0
