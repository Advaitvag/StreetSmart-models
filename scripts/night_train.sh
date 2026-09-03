#!/usr/bin/env bash
# Overnight training sweep for the StreetSmart model comparison.
#
# Trains four detectors on datasets/combined_dataset, in order, each from its
# stock COCO-pretrained weights to STREETSMART_EPOCHS epochs:
#
#     yolo11s -> yolo26s -> yolo11m -> yolo26m
#
# A model only starts once its predecessor has reached the epoch budget. Each
# model gets its own run dir (runs/night-<model>) and is resumed night after
# night; when the whole window is used up the current model is checkpointed
# (SIGINT) and resumes the next night. When all four are done a summary
# notification ranks their final mAP.
#
# Started 23:00 by streetsmart-night.timer, stopped 08:30 by
# streetsmart-night-stop.timer. A self-guard refuses to run outside that
# window so a missed / delayed trigger never starts after 08:30.

set -uo pipefail

REPO="${STREETSMART_REPO:-/home/ad/potholes}"
PY="$REPO/.venv/bin/python"
DATA="$REPO/datasets/combined_dataset/data.yaml"
read -ra MODELS <<<"${STREETSMART_MODELS:-yolo11s yolo26s yolo11m yolo26m}"
EPOCHS="${STREETSMART_EPOCHS:-300}"
BATCH_S="${STREETSMART_BATCH_S:-16}"   # yolo*s
BATCH_M="${STREETSMART_BATCH_M:-8}"    # yolo*m  (8 GB GPU)
IMGSZ="${STREETSMART_IMGSZ:-640}"
DEVICE="${STREETSMART_DEVICE:-0}"
FRACTION="${STREETSMART_FRACTION:-1.0}"        # <1.0 only for smoke tests
WIN_START="${STREETSMART_WIN_START:-2300}"     # HHMM, inclusive
WIN_END="${STREETSMART_WIN_END:-0830}"         # HHMM, exclusive
APP="StreetSmart Training"
LOG="$REPO/runs/streetsmart_night.log"
METRICS_CSV="$REPO/runs/streetsmart_night_metrics.csv"
SUMMARY_MARK="$REPO/runs/.night_sweep_summary_sent"

mkdir -p "$REPO/runs"

log()    { printf '%s  %s\n' "$(date -Is)" "$*" >>"$LOG"; }
notify() { # <urgency> <title> <body>
	notify-send -a "$APP" -u "$1" "$2" "$3" 2>/dev/null || true
	log "[$2] ${3//$'\n'/ | }"
}

# Append-only session history (per-epoch history lives in each run's results.csv,
# which Ultralytics keeps appending to across resumes).
record() { # <model> <event start|end> <epoch> <prec> <rec> <mAP50> <mAP50-95> <elapsed_s> <exit>
	[[ -f "$METRICS_CSV" ]] || \
		echo "timestamp,model,event,epoch,precision,recall,mAP50,mAP50-95,elapsed_s,exit" >"$METRICS_CSV"
	printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
		"$(date -Is)" "$1" "$2" "${3:-}" "${4:-}" "${5:-}" "${6:-}" "${7:-}" "${8:-}" "${9:-}" >>"$METRICS_CSV"
}

ws=$((10#$WIN_START))
we=$((10#$WIN_END))
in_window() { local n; n=$((10#$(date +%H%M))); ! ((n < ws && n >= we)); }

if ! in_window; then
	log "outside ${WIN_START}-${WIN_END} window (now=$(date +%H:%M)); not starting"
	exit 0
fi

[[ -x "$PY" ]]   || { notify critical "night sweep aborted" "venv python missing: $PY"; exit 1; }
[[ -f "$DATA" ]] || { notify critical "night sweep aborted" "dataset yaml missing: $DATA"; exit 1; }

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

run_dir()  { printf '%s/runs/night-%s' "$REPO" "$1"; }
batch_for() { case "$1" in *s) echo "$BATCH_S" ;; *) echo "$BATCH_M" ;; esac; }

is_done() { # <model>
	local rd; rd="$(run_dir "$1")"
	[[ -f "$rd/.done" ]] && return 0
	local m; m="$(read_metrics "$rd/results.csv" || true)"
	[[ -n "$m" ]] || return 1
	((${m%% *} >= EPOCHS - 1))
}

all_done() {
	local m
	for m in "${MODELS[@]}"; do is_done "$m" || return 1; done
	return 0
}

summary() {
	local body="final metrics  ·  mAP50-95 / mAP50 (epoch)" m x
	for m in "${MODELS[@]}"; do
		x="$(read_metrics "$(run_dir "$m")/results.csv" || true)"
		if [[ -n "$x" ]]; then
			read -r e _ _ m50 m5095 <<<"$x"
			body+=$'\n'"$(printf '%-9s %s / %s  (ep %s)' "$m" "$m5095" "$m50" "$e")"
		else
			body+=$'\n'"$m: no results"
		fi
	done
	notify normal "night sweep complete" "$body"
}

# --- nothing left to do? ---------------------------------------------------
if all_done; then
	if [[ -f "$SUMMARY_MARK" ]]; then
		log "sweep already complete; nothing to do"
	else
		summary
		touch "$SUMMARY_MARK"
	fi
	exit 0
fi

# --- walk the pipeline ----------------------------------------------------
for i in "${!MODELS[@]}"; do
	m="${MODELS[$i]}"
	pos="$((i + 1))/${#MODELS[@]}"

	if is_done "$m"; then
		log "$m already complete ($pos), skipping"
		continue
	fi
	if ! in_window; then
		log "window closed before starting $m ($pos); stopping for tonight"
		break
	fi

	RUN_DIR="$(run_dir "$m")"
	mkdir -p "$RUN_DIR"
	batch="$(batch_for "$m")"
	resuming=0
	[[ -f "$RUN_DIR/weights/last.pt" ]] && resuming=1

	sE=0; sP=""; sR=""; s50=""; s5095=""
	if ((resuming)); then
		bm="$(read_metrics "$RUN_DIR/results.csv" || true)"
		[[ -n "$bm" ]] && read -r sE sP sR s50 s5095 <<<"$bm"
		notify normal "night training: $m" \
"resuming ($pos)   epoch ${sE}/${EPOCHS}   batch ${batch}
precision ${sP}   recall ${sR}
mAP50 ${s50}   mAP50-95 ${s5095}"
	else
		notify normal "night training: $m" \
"fresh from stock ${m}.pt ($pos)
epoch 0/${EPOCHS}   batch ${batch}"
	fi
	record "$m" start "$sE" "$sP" "$sR" "$s50" "$s5095" "" ""

	t0=$(date +%s)

	STREETSMART_RESUME="$resuming" \
	STREETSMART_RUNDIR="$RUN_DIR" \
	STREETSMART_STOCK="${m}.pt" \
	STREETSMART_NAME="night-$m" \
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
    YOLO(last).train(resume=last)
else:
    YOLO(os.environ["STREETSMART_STOCK"]).train(
        data=os.environ["STREETSMART_DATA"],
        epochs=int(os.environ["STREETSMART_EPOCHS"]),
        imgsz=int(os.environ["STREETSMART_IMGSZ"]),
        batch=int(os.environ["STREETSMART_BATCH"]),
        device=os.environ["STREETSMART_DEVICE"],
        project=os.environ["STREETSMART_PROJECT"],
        name=os.environ["STREETSMART_NAME"],
        exist_ok=True,
        patience=0,   # no early stopping for the long run
        seed=0,
        fraction=float(os.environ["STREETSMART_FRACTION"]),
    )
PY
	child=$!
	trap 'log "stop signal -> SIGINT '"$m"' ('"$child"')"; kill -INT "$child" 2>/dev/null' INT TERM
	wait "$child"; rc=$?
	while kill -0 "$child" 2>/dev/null; do wait "$child"; rc=$?; done
	trap - INT TERM

	dt=$(($(date +%s) - t0))
	elapsed="$(printf '%dh%02dm' $((dt / 3600)) $(((dt % 3600) / 60)))"

	em="$(read_metrics "$RUN_DIR/results.csv" || true)"
	if [[ -n "$em" ]]; then
		read -r eE eP eR e50 e5095 <<<"$em"
		record "$m" end "$eE" "$eP" "$eR" "$e50" "$e5095" "$dt" "$rc"
		notify normal "night training: $m ended" \
"epoch ${sE} -> ${eE} / ${EPOCHS}   (${elapsed}, exit ${rc})
precision   ${sP:-n/a} -> ${eP}   (Δ $(delta "${sP}" "$eP"))
recall      ${sR:-n/a} -> ${eR}   (Δ $(delta "${sR}" "$eR"))
mAP50       ${s50:-n/a} -> ${e50}   (Δ $(delta "${s50}" "$e50"))
mAP50-95    ${s5095:-n/a} -> ${e5095}   (Δ $(delta "${s5095}" "$e5095"))"
	else
		record "$m" end "" "" "" "" "" "$dt" "$rc"
		notify critical "night training: $m ended" \
			"no results.csv (exit ${rc}, ${elapsed}) — journalctl --user -u streetsmart-night"
	fi

	if is_done "$m"; then
		touch "$RUN_DIR/.done"
		log "$m complete ($pos) — advancing"
	else
		log "$m stopped before ${EPOCHS} epochs ($pos) — resume next window"
		break
	fi
done

if all_done && [[ ! -f "$SUMMARY_MARK" ]]; then
	summary
	touch "$SUMMARY_MARK"
fi
exit 0
