#!/usr/bin/env bash
# Overnight training window for the StreetSmart best model.
#
# Runs one long dedicated Ultralytics run (runs/streetsmart-night) that starts
# from the yolo26m combined best.pt and is resumed every night until it reaches
# STREETSMART_EPOCHS. Started at 23:00 by streetsmart-night.timer and stopped at
# 08:30 by streetsmart-night-stop.timer; a self-guard refuses to run outside
# that window (so a missed / delayed trigger never starts after 08:30).
#
# Desktop notifications (notify-send) are sent at start and end; the end
# notification reports every box metric before -> after with its delta. Every
# notification is also appended to the log file.

set -uo pipefail

REPO="${STREETSMART_REPO:-/home/ad/potholes}"
PY="$REPO/.venv/bin/python"
RUN_NAME="${STREETSMART_RUN_NAME:-streetsmart-night}"
RUN_DIR="$REPO/runs/$RUN_NAME"
FRACTION="${STREETSMART_FRACTION:-1.0}"   # <1.0 only for smoke tests
RESULTS="$RUN_DIR/results.csv"
SEED_WEIGHTS="$REPO/models/trained/yolo26m-combined/weights/best.pt"
SEED_RESULTS="$REPO/models/trained/yolo26m-combined/results.csv"
DATA="$REPO/datasets/combined_dataset/data.yaml"
EPOCHS="${STREETSMART_EPOCHS:-600}"
BATCH="${STREETSMART_BATCH:-8}"
IMGSZ="${STREETSMART_IMGSZ:-640}"
DEVICE="${STREETSMART_DEVICE:-0}"
WIN_START="${STREETSMART_WIN_START:-2300}"   # HHMM, inclusive
WIN_END="${STREETSMART_WIN_END:-0830}"       # HHMM, exclusive
APP="StreetSmart Training"
LOG="$RUN_DIR/night_train.log"

mkdir -p "$RUN_DIR"

log()    { printf '%s  %s\n' "$(date -Is)" "$*" >>"$LOG"; }
notify() { # <urgency> <title> <body>
	local urgency="$1" title="$2" body="$3"
	notify-send -a "$APP" -u "$urgency" "$title" "$body" 2>/dev/null || true
	log "[$title] ${body//$'\n'/ | }"
}

# --- time-window guard (window wraps past midnight) --------------------------
now=$((10#$(date +%H%M)))
ws=$((10#$WIN_START))
we=$((10#$WIN_END))
if ((now < ws && now >= we)); then
	log "outside ${WIN_START}-${WIN_END} window (now=$(date +%H:%M)); not starting"
	exit 0
fi

# --- prerequisites ----------------------------------------------------------
[[ -x "$PY" ]]      || { notify critical "night training aborted" "venv python missing: $PY"; exit 1; }
[[ -f "$DATA" ]]    || { notify critical "night training aborted" "dataset yaml missing: $DATA"; exit 1; }
[[ -f "$SEED_WEIGHTS" ]] || { notify critical "night training aborted" "seed weights missing: $SEED_WEIGHTS"; exit 1; }

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

resuming=0
[[ -f "$RUN_DIR/weights/last.pt" ]] && resuming=1

# --- already finished? -----------------------------------------------------
if ((resuming)); then
	m="$(read_metrics "$RESULTS" || true)"
	if [[ -n "$m" ]]; then
		ep="${m%% *}"
		if ((ep >= EPOCHS - 1)); then
			notify normal "night training: nothing to do" \
				"run reached epoch ${ep}/${EPOCHS} — training complete, disable the timer"
			exit 0
		fi
	fi
fi

# --- start notification --------------------------------------------------
start_src="$RESULTS"
((resuming)) || start_src="$SEED_RESULTS"
sE=0; sP=""; sR=""; s50=""; s5095=""
START_M="$(read_metrics "$start_src" || true)"
[[ -n "$START_M" ]] && read -r seedE sP sR s50 s5095 <<<"$START_M"
((resuming)) && sE="${seedE:-0}"   # fresh start begins at epoch 0
if [[ -n "$START_M" ]]; then
	notify normal "night training started" \
"$( ((resuming)) && echo "resuming run ${RUN_NAME}" || echo "baseline: yolo26m best.pt" )
epoch ${sE}/${EPOCHS}
precision ${sP}   recall ${sR}
mAP50 ${s50}   mAP50-95 ${s5095}"
else
	notify normal "night training started" \
"$( ((resuming)) && echo "resuming run ${RUN_NAME}" || echo "fresh start from yolo26m best.pt" )
epoch ${sE}/${EPOCHS} (no baseline metrics found)"
fi

t0=$(date +%s)

# --- train (call Ultralytics directly: clean SIGINT save on the 08:30 stop,
#     and resume targets this exact run rather than the newest run on disk) ---
STREETSMART_RESUME="$resuming" "$PY" - <<PY &
import os
from ultralytics import YOLO

run_dir = r"$RUN_DIR"
last = os.path.join(run_dir, "weights", "last.pt")
if os.environ.get("STREETSMART_RESUME") == "1" and os.path.exists(last):
    YOLO(last).train(resume=last)
else:
    YOLO(r"$SEED_WEIGHTS").train(
        data=r"$DATA",
        epochs=$EPOCHS,
        imgsz=$IMGSZ,
        batch=$BATCH,
        device="$DEVICE",
        project=os.path.join(r"$REPO", "runs"),
        name="$RUN_NAME",
        exist_ok=True,
        patience=0,   # disable early stopping for the long run
        seed=0,
        fraction=$FRACTION,
    )
PY
child=$!
trap 'log "stop signal received -> SIGINT $child"; kill -INT "$child" 2>/dev/null' INT TERM
wait "$child"; rc=$?
while kill -0 "$child" 2>/dev/null; do wait "$child"; rc=$?; done
trap - INT TERM

t1=$(date +%s)
dt=$((t1 - t0))
elapsed="$(printf '%dh%02dm' $((dt / 3600)) $(((dt % 3600) / 60)))"

# --- end notification: every metric, before -> after (Δ) ----------------
delta() { awk -v a="$1" -v b="$2" 'BEGIN { if (a == "") print "n/a"; else printf "%+.4f", b - a }'; }
END_M="$(read_metrics "$RESULTS" || true)"
if [[ -n "$END_M" ]]; then
	read -r eE eP eR e50 e5095 <<<"$END_M"
	notify normal "night training ended" \
"epoch ${sE} -> ${eE} / ${EPOCHS}   (${elapsed}, exit ${rc})
precision   ${sP:-n/a} -> ${eP}   (Δ $(delta "${sP}" "$eP"))
recall      ${sR:-n/a} -> ${eR}   (Δ $(delta "${sR}" "$eR"))
mAP50       ${s50:-n/a} -> ${e50}   (Δ $(delta "${s50}" "$e50"))
mAP50-95    ${s5095:-n/a} -> ${e5095}   (Δ $(delta "${s5095}" "$e5095"))"
else
	notify critical "night training ended" \
		"no results.csv produced (exit ${rc}, ${elapsed}) — check: journalctl --user -u streetsmart-night"
fi

exit 0
