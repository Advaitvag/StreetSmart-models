#!/usr/bin/env bash
# Training script for continuing YOLO26s and YOLO26m training on the clean pothole
# dataset (excluding ML-auto-labeled Cincinnati 311 data).
#
# Continues training for 100 epochs per model, starting from the best night-trained
# checkpoints:
#
#     runs/night-yolo26s/weights/best.pt -> runs/clean-yolo26s (100 epochs)
#     runs/night-yolo26m/weights/best.pt -> runs/clean-yolo26m (100 epochs)
#
# Can be started interactively or in the background at any time (no time-window
# restriction, no systemd requirement). Gracefully catches SIGINT/SIGTERM to
# checkpoint the running model, and automatically resumes upon restart.

set -uo pipefail

REPO="${STREETSMART_REPO:-/home/ad/potholes}"
PY="$REPO/.venv/bin/python"
DATA="${STREETSMART_DATA:-$REPO/datasets/data_nocincinnati.yaml}"
read -ra MODELS <<<"${STREETSMART_MODELS:-yolo26s yolo26m}"
EPOCHS="${STREETSMART_EPOCHS:-100}"
BATCH_S="${STREETSMART_BATCH_S:-16}" # yolo*s
BATCH_M="${STREETSMART_BATCH_M:-8}"  # yolo*m  (8 GB GPU)
IMGSZ="${STREETSMART_IMGSZ:-640}"
DEVICE="${STREETSMART_DEVICE:-0}"
FRACTION="${STREETSMART_FRACTION:-1.0}"
APP="StreetSmart Clean Training"
LOG="$REPO/runs/streetsmart_clean_train.log"
METRICS_CSV="$REPO/runs/streetsmart_clean_metrics.csv"
SUMMARY_MARK="$REPO/runs/.clean_train_summary_sent"

mkdir -p "$REPO/runs"

log() { printf '%s  %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
notify() { # <urgency> <title> <body>
  notify-send -a "$APP" -u "$1" "$2" "$3" 2>/dev/null || true
  log "[$2] ${3//$'\n'/ | }"
}

# Append-only session history
record() { # <model> <event start|end> <epoch> <prec> <rec> <mAP50> <mAP50-95> <elapsed_s> <exit>
  [[ -f "$METRICS_CSV" ]] ||
    echo "timestamp,model,event,epoch,precision,recall,mAP50,mAP50-95,elapsed_s,exit" >"$METRICS_CSV"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$(date -Is)" "$1" "$2" "${3:-}" "${4:-}" "${5:-}" "${6:-}" "${7:-}" "${8:-}" "${9:-}" >>"$METRICS_CSV"
}

[[ -x "$PY" ]] || {
  notify critical "clean training aborted" "venv python missing: $PY"
  exit 1
}
[[ -f "$DATA" ]] || {
  notify critical "clean training aborted" "dataset yaml missing: $DATA"
  exit 1
}

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

run_dir() { printf '%s/runs/clean-%s' "$REPO" "$1"; }
batch_for() { case "$1" in *s) echo "$BATCH_S" ;; *) echo "$BATCH_M" ;; esac }

# Determine initial checkpoint for fine-tuning without Cincinnati
initial_weights_for() {
  local m="$1"
  local night_best="$REPO/runs/night-$m/weights/best.pt"
  local night_last="$REPO/runs/night-$m/weights/last.pt"
  local stock="$REPO/$m.pt"

  if [[ -f "$night_best" ]]; then
    echo "$night_best"
  elif [[ -f "$night_last" ]]; then
    echo "$night_last"
  elif [[ -f "$stock" ]]; then
    echo "$stock"
  else
    echo "$m.pt"
  fi
}

is_done() { # <model>
  local rd
  rd="$(run_dir "$1")"
  [[ -f "$rd/.done" ]] && return 0
  local m
  m="$(read_metrics "$rd/results.csv" || true)"
  [[ -n "$m" ]] || return 1
  ((${m%% *} >= EPOCHS - 1))
}

all_done() {
  local m
  for m in "${MODELS[@]}"; do is_done "$m" || return 1; done
  return 0
}

summary() {
  local body="final clean metrics  ·  mAP50-95 / mAP50 (epoch)" m x
  for m in "${MODELS[@]}"; do
    x="$(read_metrics "$(run_dir "$m")/results.csv" || true)"
    if [[ -n "$x" ]]; then
      read -r e _ _ m50 m5095 <<<"$x"
      body+=$'\n'"$(printf '%-9s %s / %s  (ep %s)' "$m" "$m5095" "$m50" "$e")"
    else
      body+=$'\n'"$m: no results"
    fi
  done
  notify normal "clean training complete" "$body"
}

# --- nothing left to do? ---------------------------------------------------
if all_done; then
  if [[ -f "$SUMMARY_MARK" ]]; then
    log "clean training already complete; nothing to do"
  else
    summary
    touch "$SUMMARY_MARK"
  fi
  exit 0
fi

log "Starting StreetSmart clean training (excluding Cincinnati data)"
log "Dataset: $DATA"
log "Models: ${MODELS[*]} (Target epochs: $EPOCHS per model)"

# --- walk the pipeline ----------------------------------------------------
for i in "${!MODELS[@]}"; do
  m="${MODELS[$i]}"
  pos="$((i + 1))/${#MODELS[@]}"

  if is_done "$m"; then
    log "$m already complete ($pos), skipping"
    continue
  fi

  RUN_DIR="$(run_dir "$m")"
  mkdir -p "$RUN_DIR"
  batch="$(batch_for "$m")"
  base_weights="$(initial_weights_for "$m")"
  resuming=0

  [[ -f "$RUN_DIR/weights/last.pt" ]] && resuming=1

  sE=0
  sP=""
  sR=""
  s50=""
  s5095=""
  if ((resuming)); then
    bm="$(read_metrics "$RUN_DIR/results.csv" || true)"
    [[ -n "$bm" ]] && read -r sE sP sR s50 s5095 <<<"$bm"
    notify normal "clean training: $m" \
      "resuming ($pos)   epoch ${sE}/${EPOCHS}   batch ${batch}
precision ${sP}   recall ${sR}
mAP50 ${s50}   mAP50-95 ${s5095}"
  else
    notify normal "clean training: $m" \
      "fine-tuning from ${base_weights##*/} ($pos)
epoch 0/${EPOCHS}   batch ${batch}"
  fi
  record "$m" start "$sE" "$sP" "$sR" "$s50" "$s5095" "" ""

  t0=$(date +%s)

  STREETSMART_RESUME="$resuming" \
    STREETSMART_RUNDIR="$RUN_DIR" \
    STREETSMART_BASE="$base_weights" \
    STREETSMART_NAME="clean-$m" \
    STREETSMART_BATCH="$batch" \
    STREETSMART_DATA="$DATA" \
    STREETSMART_EPOCHS="$EPOCHS" \
    STREETSMART_IMGSZ="$IMGSZ" \
    STREETSMART_DEVICE="$DEVICE" \
    STREETSMART_PROJECT="$REPO/runs" \
    STREETSMART_FRACTION="$FRACTION" \
    "$PY" - <<'PY' &
import os
from ultralytics import YOLO

rundir = os.environ["STREETSMART_RUNDIR"]
last = os.path.join(rundir, "weights", "last.pt")
if os.environ["STREETSMART_RESUME"] == "1" and os.path.exists(last):
    print(f"Resuming clean training from {last}")
    YOLO(last).train(resume=last)
else:
    base = os.environ["STREETSMART_BASE"]
    print(f"Fine-tuning clean training initialized from {base}")
    YOLO(base).train(
        data=os.environ["STREETSMART_DATA"],
        epochs=int(os.environ["STREETSMART_EPOCHS"]),
        imgsz=int(os.environ["STREETSMART_IMGSZ"]),
        batch=int(os.environ["STREETSMART_BATCH"]),
        device=os.environ["STREETSMART_DEVICE"],
        project=os.environ["STREETSMART_PROJECT"],
        name=os.environ["STREETSMART_NAME"],
        exist_ok=True,
        patience=0,   # no early stopping
        seed=0,
        fraction=float(os.environ["STREETSMART_FRACTION"]),
    )
PY
  child=$!
  trap 'log "stop signal -> SIGINT '"$m"' ('"$child"')"; kill -INT "$child" 2>/dev/null' INT TERM
  wait "$child"
  rc=$?
  while kill -0 "$child" 2>/dev/null; do
    wait "$child"
    rc=$?
  done
  trap - INT TERM

  dt=$(($(date +%s) - t0))
  elapsed="$(printf '%dh%02dm' $((dt / 3600)) $(((dt % 3600) / 60)))"

  em="$(read_metrics "$RUN_DIR/results.csv" || true)"
  if [[ -n "$em" ]]; then
    read -r eE eP eR e50 e5095 <<<"$em"
    record "$m" end "$eE" "$eP" "$eR" "$e50" "$e5095" "$dt" "$rc"
    notify normal "clean training: $m ended" \
      "epoch ${sE} -> ${eE} / ${EPOCHS}   (${elapsed}, exit ${rc})
precision   ${sP:-n/a} -> ${eP}   (Δ $(delta "${sP}" "$eP"))
recall      ${sR:-n/a} -> ${eR}   (Δ $(delta "${sR}" "$eR"))
mAP50       ${s50:-n/a} -> ${e50}   (Δ $(delta "${s50}" "$e50"))
mAP50-95    ${s5095:-n/a} -> ${e5095}   (Δ $(delta "${s5095}" "$e5095"))"
  else
    record "$m" end "" "" "" "" "" "$dt" "$rc"
    notify critical "clean training: $m ended" \
      "no results.csv (exit ${rc}, ${elapsed})"
  fi

  if is_done "$m"; then
    touch "$RUN_DIR/.done"
    log "$m clean training complete ($pos) — advancing"
  else
    log "$m paused before ${EPOCHS} epochs ($pos) — run again to resume"
    break
  fi
done

if all_done && [[ ! -f "$SUMMARY_MARK" ]]; then
  summary
  touch "$SUMMARY_MARK"
fi
exit 0
