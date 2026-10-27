#!/usr/bin/env python3
"""Re-split the Cincinnati-free pothole dataset into leak-free train/val/test.

``build_dataset.py`` splits image-by-image, which leaks near-identical images
across splits:

* Roboflow exports contain 3 augmented copies of each photo
  (``<name>_jpg.rf.<hash>.jpg``); copies land on both sides of the split.
* BharatPotHole is frames from 85 dashcam clips; GoPro (``G0010033.JPG``)
  and PothRGBD (``20250227_135438_color``) are capture sequences seconds
  apart; HRP4K / RDD / CuratedRGB contain re-shot scenes.

This script reads the Cincinnati-free pool (default
``datasets/_upload_PotholesCombined``, both of its splits), groups every image
with its copies / clip / capture run / near-duplicates (union-find), and
assigns whole groups to ``train`` / ``val`` / ``test``, stratified per source.
``val`` is for model selection during training; ``test`` is touched only by
the final evaluation.

Groups are formed from:

1. identical file contents (MD5),
2. the same Roboflow original (filename before ``.rf.``),
3. the same drive: BharatPotHole clips < 2 min apart, GoPro frames < 20
   numbers apart, PothRGBD captures < 60 s apart,
4. near-duplicates: 256-bit dHash (flip-aware) Hamming distance <=
   ``--near-dup`` (22 by default; random road pairs sit at >= 43).

Exact duplicate files are kept once. Labels are rewritten as clean boxes
(polygon lines -> boxes, coordinates clipped to [0, 1], degenerate boxes
dropped); images are relative symlinks into the pool.

Cincinnati 311 imagery is refused: the build aborts if any pool image is
byte-identical to a file under ``--cincinnati-images`` or is named ``SR*``.

If ``--night-train`` exists (default ``datasets/combined_dataset/train/images``,
the training images of the night / clean runs), the test images whose whole
group is absent from it are listed in ``test_unseen_by_night.txt`` with
``data_unseen_by_night.yaml`` -- the subset on which old and new models can be
compared fairly.

Needs numpy and Pillow (both in the project venv). All paths are relative to
``--repo-root``.

Example::

    .venv/bin/python scripts/build_clean_split.py          # -> datasets/clean_split
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = ("train", "val", "test")

# Upstream directories (same layout as build_dataset.py), used only to tell
# which source each pool image came from, by file content.
SOURCE_DIRS = {
    "BharatPotHole": "BharatPotHole",
    "HRP4K": "HRP4K",
    "CuratedRGB": "A Curated RGB Dataset for Real-Time Road Damage De",
    "Roboflow-YOLOv8": "Pothole-detection-Yolov8",
    "dataset-generic": "dataset",
    "PData": "PData",
    "RDD": "RDD_SPLIT",
}

RF_RE = re.compile(r"^(.+?)\.rf\.[0-9a-f]+$")
BHARAT_RE = re.compile(r"^(?:(\d{14})_\d+|signal-(\d{4}-\d\d-\d\d-\d{6})(?:_\d+)?)_frame_\d+")
GOPRO_RE = re.compile(r"^G(\d{3})(\d{4})$")
PDATA_RE = re.compile(r"^(\d{8}_\d{6})_color")


def list_images(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*")
                  if p.suffix.lower() in IMAGE_EXTS and p.is_file())


def md5_of(path: Path) -> tuple[str, str]:
    return str(path), hashlib.md5(path.read_bytes()).hexdigest()


def fingerprint(path: Path) -> tuple[str, str, bytes, bytes]:
    """MD5 plus a 256-bit difference hash of the image and of its mirror."""
    with Image.open(path) as im:
        im.draft("L", (128, 128))
        g = np.asarray(im.convert("L").resize((17, 16), Image.BILINEAR),
                       dtype=np.int16)
    d = np.packbits((g[:, 1:] > g[:, :-1]).ravel()).tobytes()
    gf = g[:, ::-1]
    df = np.packbits((gf[:, 1:] > gf[:, :-1]).ravel()).tobytes()
    return str(path), md5_of(path)[1], d, df


def as_words(hashes: list[bytes]) -> np.ndarray:
    return np.frombuffer(b"".join(hashes), dtype=np.uint64).reshape(len(hashes), 4)


def stem_of(path: Path) -> str:
    """Original upstream stem: drops the Roboflow ``.rf.<hash>`` suffix."""
    m = RF_RE.match(path.stem)
    return m.group(1) if m else path.stem


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def family_keys(paths: list[Path], sources: list[str]) -> list[list[str]]:
    """Sequence / copy keys per image; images sharing a key share a group."""
    keys: list[list[str]] = [[] for _ in paths]
    drive_times: dict[str, list[tuple[float, int]]] = defaultdict(list)
    gopro: dict[str, list[tuple[int, int]]] = defaultdict(list)

    for i, (p, src) in enumerate(zip(paths, sources)):
        stem = stem_of(p)
        if stem != p.stem:
            keys[i].append(f"rf:{src}:{stem}")
        if m := BHARAT_RE.match(stem):
            if m.group(1):
                t = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
            else:
                t = datetime.strptime(m.group(2), "%Y-%m-%d-%H%M%S")
            drive_times["bharat"].append((t.timestamp(), i))
        elif m := GOPRO_RE.match(stem):
            gopro[m.group(1)].append((int(m.group(2)), i))
        elif m := PDATA_RE.match(stem):
            t = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
            drive_times["pdata"].append((t.timestamp(), i))

    # (series, max gap): consecutive members closer than the gap share a run
    runs = [("bharat", drive_times["bharat"], 120),
            ("pdata", drive_times["pdata"], 60)]
    runs += [(f"gopro{seq}", members, 20) for seq, members in gopro.items()]
    for name, members, gap in runs:
        members.sort()
        run, prev = 0, None
        for t, i in members:
            if prev is not None and t - prev > gap:
                run += 1
            keys[i].append(f"run:{name}:{run}")
            prev = t
    return keys


def near_dup_pairs(a: np.ndarray, b: np.ndarray, b_flip: np.ndarray,
                   threshold: int, same: bool) -> list[tuple[int, int]]:
    """Index pairs (i in a, j in b) whose dHash distance <= threshold."""
    pairs: list[tuple[int, int]] = []
    for i in range(len(a)):
        lo = i + 1 if same else 0
        d = np.minimum(np.bitwise_count(b[lo:] ^ a[i]).sum(1),
                       np.bitwise_count(b_flip[lo:] ^ a[i]).sum(1))
        pairs.extend((i, lo + int(j)) for j in np.nonzero(d <= threshold)[0])
    return pairs


def clean_label(text: str) -> tuple[list[str], Counter]:
    """Return clean ``0 cx cy w h`` lines and a tally of what was fixed."""
    fixes: Counter = Counter()
    out: list[str] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        coords = [float(x) for x in parts[1:]]
        if len(coords) > 4:  # polygon
            fixes["polygon_to_box"] += 1
            xs, ys = coords[0::2], coords[1::2]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        elif len(coords) == 4:
            cx, cy, w, h = coords
            x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        else:
            fixes["malformed_dropped"] += 1
            continue
        c = [min(max(v, 0.0), 1.0) for v in (x0, x1, y0, y1)]
        if c != [x0, x1, y0, y1]:
            fixes["clipped"] += 1
        x0, x1, y0, y1 = c
        if x1 - x0 <= 1e-4 or y1 - y0 <= 1e-4:
            fixes["degenerate_dropped"] += 1
            continue
        box = (f"0 {(x0 + x1) / 2:.6f} {(y0 + y1) / 2:.6f} "
               f"{x1 - x0:.6f} {y1 - y0:.6f}")
        if box in out:
            fixes["duplicate_dropped"] += 1
            continue
        out.append(box)
    return out, fixes


def assign_splits(groups: dict[int, list[int]], sources: list[str],
                  val_frac: float, test_frac: float,
                  seed: int) -> dict[int, str]:
    """Greedy per-source fill of test, then val, by image count."""
    rng = random.Random(seed)
    by_source: dict[str, list[int]] = defaultdict(list)
    for root, members in groups.items():
        by_source[Counter(sources[i] for i in members).most_common(1)[0][0]].append(root)

    split_of: dict[int, str] = {}
    for src in sorted(by_source):
        roots = sorted(by_source[src])
        rng.shuffle(roots)
        total = sum(len(groups[r]) for r in roots)
        want = {"test": test_frac * total, "val": val_frac * total}
        have = {"test": 0, "val": 0}
        for r in roots:
            n = len(groups[r])
            for split in ("test", "val"):
                # take the group if it brings the split closer to its target
                if abs(have[split] + n - want[split]) < abs(have[split] - want[split]):
                    split_of[r] = split
                    have[split] += n
                    break
            else:
                split_of[r] = "train"
    return split_of


def build(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    rel = lambda p: Path(p) if Path(p).is_absolute() else repo / p  # noqa: E731
    pool, out = rel(args.pool), rel(args.out)
    sources_dir, cin_dir = rel(args.sources_dir), rel(args.cincinnati_images)
    night_dir = rel(args.night_train)

    if out.exists() and any(out.iterdir()) and not args.force:
        print(f"error: {out} exists and is not empty (use --force).")
        return 1

    images = list_images(pool / "train" / "images") + list_images(pool / "val" / "images")
    if not images:
        print(f"error: no images under {pool}/{{train,val}}/images")
        return 1
    print(f"pool: {len(images)} images in {pool}")

    with Pool(args.workers) as workers:
        fp = workers.map(fingerprint, images, chunksize=64)
        upstream = {name: list_images(sources_dir / d) for name, d in SOURCE_DIRS.items()}
        src_md5 = {}
        for name, files in upstream.items():
            for _, md5 in workers.map(md5_of, files, chunksize=64):
                src_md5.setdefault(md5, name)
        cin_md5 = {m for _, m in workers.map(md5_of, list_images(cin_dir), chunksize=64)}
        night_files = list_images(night_dir)
        night_fp = workers.map(fingerprint, night_files, chunksize=64) if night_files else []

    # -- Cincinnati guard ------------------------------------------------------
    cin_hits = [p for p, (_, m, _, _) in zip(images, fp)
                if m in cin_md5 or re.match(r"^SR\d", p.name)]
    if cin_hits:
        print(f"error: {len(cin_hits)} pool images are Cincinnati 311 imagery, "
              f"e.g. {cin_hits[0]} -- refusing to build.")
        return 1
    print(f"cincinnati check: 0 of {len(images)} match {len(cin_md5)} Cincinnati "
          f"files or SR* names")

    # -- drop exact duplicate files ---------------------------------------------
    keep: dict[str, int] = {}
    for i, (_, m, _, _) in enumerate(fp):
        keep.setdefault(m, i)
    idx = sorted(keep.values())
    paths = [images[i] for i in idx]
    md5s = [fp[i][1] for i in idx]
    dh, dhf = as_words([fp[i][2] for i in idx]), as_words([fp[i][3] for i in idx])
    sources = [src_md5.get(m, "unknown") for m in md5s]
    print(f"exact duplicates removed: {len(images) - len(paths)}")

    # -- groups --------------------------------------------------------------------
    keys = family_keys(paths, sources)
    uf = UnionFind(len(paths))
    first: dict[str, int] = {}
    for i, ks in enumerate(keys):
        for k in ks:
            uf.union(i, first.setdefault(k, i))
    near = near_dup_pairs(dh, dh, dhf, args.near_dup, same=True)
    for i, j in near:
        uf.union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(paths)):
        groups[uf.find(i)].append(i)
    sizes = sorted((len(g) for g in groups.values()), reverse=True)
    print(f"groups: {len(groups)} from {len(paths)} images "
          f"({len(near)} near-duplicate pairs); largest {sizes[:5]}")

    split_of = assign_splits(groups, sources, args.val_frac, args.test_frac, args.seed)
    split = [split_of[uf.find(i)] for i in range(len(paths))]

    # -- verify: no copy, run or near-duplicate link crosses splits -------------
    cross = sum(split[i] != split[j] for i, j in near)
    owner: dict[str, str] = {}
    for i, ks in enumerate(keys):
        for k in ks:
            cross += owner.setdefault(k, split[i]) != split[i]
    if cross:
        print(f"error: {cross} group links cross splits (bug)")
        return 1

    # -- test images never seen by the night / clean-v1 runs --------------------
    # A test group counts as seen if any member shares contents, a copy/run key
    # or a near-duplicate with a night training image. Run keys are recomputed
    # over pool + night images together so their run numbers line up.
    unseen: list[int] = []
    if night_fp:
        night_md5 = {m for _, m, _, _ in night_fp}
        night_paths = [Path(p) for p, *_ in night_fp]
        night_src = [src_md5.get(m, "unknown") for _, m, _, _ in night_fp]
        joint = family_keys(paths + night_paths, sources + night_src)
        night_keys = {k for ks in joint[len(paths):] for k in ks}
        test_idx = [i for i in range(len(paths)) if split[i] == "test"]
        seen = {uf.find(i) for i in test_idx
                if md5s[i] in night_md5 or night_keys.intersection(joint[i])}
        n_dh = as_words([h for _, _, h, _ in night_fp])
        n_dhf = as_words([h for _, _, _, h in night_fp])
        for a, _ in near_dup_pairs(dh[test_idx], n_dh, n_dhf, args.near_dup, same=False):
            seen.add(uf.find(test_idx[a]))
        unseen = [i for i in test_idx if uf.find(i) not in seen]

    # -- write ---------------------------------------------------------------------
    if out.exists() and args.force:
        for s in SPLITS:
            shutil.rmtree(out / s, ignore_errors=True)
    for s in SPLITS:
        (out / s / "images").mkdir(parents=True, exist_ok=True)
        (out / s / "labels").mkdir(parents=True, exist_ok=True)

    fixes: Counter = Counter()
    counts: dict[str, Counter] = defaultdict(Counter)
    boxes: Counter = Counter()
    names_used: set[str] = set()
    out_paths: list[Path] = []
    for p, src, s in zip(paths, sources, split):
        lbl = p.parent.parent / "labels" / f"{p.stem}.txt"
        lines, f = clean_label(lbl.read_text() if lbl.is_file() else "")
        fixes += f
        name = p.name if p.name not in names_used else f"{src}_{p.name}"
        names_used.add(name)
        dst = out / s / "images" / name
        os.symlink(os.path.relpath(p.resolve(), dst.parent), dst)
        (out / s / "labels" / f"{Path(name).stem}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else ""))
        counts[src][s] += 1
        boxes[s] += len(lines)
        out_paths.append(dst)

    yaml_head = ("# Leak-free, Cincinnati-free pothole split "
                 "(scripts/build_clean_split.py)\n"
                 f"path: {out}\n")
    names = "\nnc: 1\nnames:\n  0: pothole\n"
    (out / "data.yaml").write_text(
        yaml_head + "train: train/images\nval: val/images\ntest: test/images\n" + names)
    if night_fp:
        (out / "test_unseen_by_night.txt").write_text(
            "".join(f"./test/images/{out_paths[i].name}\n" for i in unseen))
        (out / "data_unseen_by_night.yaml").write_text(
            "# Test images whose whole group is absent from "
            f"{night_dir.relative_to(repo) if night_dir.is_relative_to(repo) else night_dir}\n"
            f"path: {out}\n"
            "train: test_unseen_by_night.txt\nval: test_unseen_by_night.txt\n" + names)

    totals = {s: sum(c[s] for c in counts.values()) for s in SPLITS}
    manifest = {
        "built": datetime.now(timezone.utc).isoformat(),
        "pool": str(pool.relative_to(repo)) if pool.is_relative_to(repo) else str(pool),
        "seed": args.seed,
        "val_frac": args.val_frac,
        "test_frac": args.test_frac,
        "near_dup_threshold_bits_of_256": args.near_dup,
        "pool_images": len(images),
        "exact_duplicates_removed": len(images) - len(paths),
        "groups": len(groups),
        "largest_groups": sizes[:10],
        "near_duplicate_pairs": len(near),
        "cross_split_links": cross,
        "cincinnati_matches": 0,
        "totals": totals,
        "boxes": dict(boxes),
        "per_source": {k: dict(v) for k, v in sorted(counts.items())},
        "label_fixes": dict(fixes),
        "test_unseen_by_night": len(unseen) if night_fp else None,
        "test_unseen_by_night_per_source": (
            dict(Counter(sources[i] for i in unseen)) if night_fp else None),
    }
    (out / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print("\n" + "=" * 60)
    print(f"{'source':<18s} {'train':>6s} {'val':>6s} {'test':>6s}")
    for src, c in sorted(counts.items()):
        print(f"{src:<18s} {c['train']:>6d} {c['val']:>6d} {c['test']:>6d}")
    print(f"{'TOTAL':<18s} {totals['train']:>6d} {totals['val']:>6d} {totals['test']:>6d}")
    print(f"label fixes: {dict(fixes)}")
    if night_fp:
        print(f"test images unseen by night training data: {len(unseen)} "
              f"of {totals['test']}")
    print(f"\nwrote data.yaml, split_manifest.json -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--repo-root", default=".",
                   help="Project root; all other paths resolve against it.")
    p.add_argument("--pool", default="datasets/_upload_PotholesCombined",
                   help="Cincinnati-free dataset to re-split (its train + val).")
    p.add_argument("--sources-dir", default="datasets",
                   help="Upstream datasets, for per-source stratification.")
    p.add_argument("--cincinnati-images", default="cincinnati",
                   help="Cincinnati image root, used only to refuse matches.")
    p.add_argument("--night-train", default="datasets/combined_dataset/train/images",
                   help="Training images of earlier runs, for the "
                        "unseen-by-night test subset (skipped if missing).")
    p.add_argument("--out", default="datasets/clean_split")
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--test-frac", type=float, default=0.10)
    p.add_argument("--near-dup", type=int, default=22,
                   help="Max dHash Hamming distance (of 256 bits) for a "
                        "near-duplicate.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    p.add_argument("--force", action="store_true",
                   help="Rebuild into a non-empty output directory.")
    return p


if __name__ == "__main__":
    raise SystemExit(build(build_parser().parse_args()))
