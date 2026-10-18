"""Recover original JSON labels with bounded, resumable HTTP range reads.

Uses the archive index saved by inspect_original_labels.py. Does not download images
or turn genuinely missing fields into negatives. Old unknown holes remain unknown.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import struct
import threading
import time
import zlib
import requests
import truststore
truststore.inject_into_ssl()
from labels import defect_label, grade_label

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "data/audit/original"
URL = "https://zenodo.org/records/13788681/files/clothing_v3.zip"


def match_source(row, lookup):
    stem = Path(row["source_image_path"]).stem
    suffix = re.search(r"_station([123])$", stem)
    station = suffix.group(1) if suffix else None
    if suffix:
        stem = stem[:suffix.start()]
    name = stem.replace("front_", "labels_", 1) + ".json"
    matches = lookup.get(name, [])
    if station:
        matches = [m for m in matches if m["name"].startswith(f"station{station}/")]
    elif len(matches) > 1:
        matches = [m for m in matches if m["name"].startswith("station1/")]
    return matches[0] if len(matches) == 1 else None


def unpack_annotation(info, block, start):
    position = info["offset"] - start
    header = struct.unpack_from("<4s5H3I2H", block, position)
    signature, _, flags, method, _, _, crc, _, _, name_len, extra_len = header
    if signature != b"PK\x03\x04" or method not in (0, 8) or flags & 1:
        raise ValueError("Invalid or unsupported ZIP annotation header")
    name_start = position + 30
    name = block[name_start:name_start + name_len].decode("utf-8")
    if name != info["name"]:
        raise ValueError(f"Archive index/header mismatch: {name}")
    data_start = name_start + name_len + extra_len
    compressed = block[data_start:data_start + info["compressed_size"]]
    decoded = zlib.decompress(compressed, -15) if method == 8 else compressed
    if flags & 8:
        footer = data_start + info["compressed_size"]
        if block[footer:footer+4] == b"PK\x07\x08":
            footer += 4
        crc = struct.unpack_from("<I", block, footer)[0]
    if len(decoded) != info["size"] or zlib.crc32(decoded) & 0xFFFFFFFF != crc:
        raise ValueError(f"Annotation CRC/size mismatch: {name}")
    return json.loads(decoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--requests-per-second", type=float, default=3)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    manifest_path = ROOT / "data/audit/manifest.jsonl"
    rows = list(map(json.loads, manifest_path.read_text().splitlines()))
    index_path = ORIGINAL / "annotation-files.json"
    lookup = defaultdict(list)
    for info in json.loads(index_path.read_text()):
        if info["name"].endswith(".json"):
            lookup[Path(info["name"]).name].append(info)
    needed = defaultdict(list)
    unmatched = []
    for row in rows:
        labels = row["labels"]
        date = row["source_image_path"][6:16]
        # Before introduction of the hole field, an unknown hole is left unknown.
        # This excludes uncertainty, and never infers a clean example from a date.
        required = labels["stains"] is None or (labels["holes"] is None and date > "2022_11_17")
        if not required:
            continue
        info = match_source(row, lookup)
        if info is None:
            unmatched.append(row["row_id"])
        else:
            needed[info["name"]].append(row)
    infos = sorted([i for group in lookup.values() for i in group if i["name"] in needed], key=lambda i: i["offset"])
    clusters = []
    for info in infos:
        start = info["offset"]
        end = start + 30 + len(info["name"].encode()) + info["compressed_size"] + 100
        if clusters and start - clusters[-1][1] <= 1024:
            clusters[-1][1] = max(clusters[-1][1], end)
            clusters[-1][2].append(info)
        else:
            clusters.append([start, end, [info]])
    budget = sum(end-start for start, end, _ in clusters)
    if budget > 64 * 1024 * 1024:
        raise ValueError("Planned reads exceed 64 MiB")
    print(json.dumps({"rows_needing_source": sum(map(len, needed.values())), "ranges": len(clusters),
                      "planned_bytes": budget, "unmatched": len(unmatched)}), flush=True)
    if args.plan_only:
        return
    cache = ORIGINAL / "ranges"
    cache.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    next_request = [0.]
    local = threading.local()

    def fetch(cluster):
        start, end, annotations = cluster
        path = cache / f"{start}-{end}.bin"
        if path.exists():
            data = path.read_bytes()
        else:
            if not hasattr(local, "session"):
                local.session = requests.Session()
            for attempt in range(5):
                with lock:
                    delay = max(0., next_request[0] - time.monotonic())
                    next_request[0] = max(next_request[0], time.monotonic()) + 1 / args.requests_per_second
                if delay:
                    time.sleep(delay)
                try:
                    with local.session.get(URL, headers={"Range": f"bytes={start}-{end-1}"}, stream=True, timeout=(15, 45)) as response:
                        if response.status_code in (429, 500, 502, 503, 504):
                            pause = max(2 ** attempt, min(float(response.headers.get("Retry-After", 0)), 55))
                            with lock:
                                next_request[0] = max(next_request[0], time.monotonic() + pause)
                            continue
                        if response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
                            raise ValueError(f"Partial read refused: HTTP {response.status_code}")
                        data = response.raw.read(end-start)
                    if len(data) != end-start:
                        raise ValueError("Truncated partial response")
                    break
                except requests.RequestException:
                    if attempt == 4:
                        raise
            else:
                raise RuntimeError("Source server retry budget exhausted")
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
        records = []
        for info in annotations:
            original = unpack_annotation(info, data, start)
            for row in needed[info["name"]]:
                grade_matches = all(grade_label(original.get(k)) == grade_label(row["labels"][k]) for k in ("condition", "pilling"))
                if not grade_matches:
                    records.append({"row_id": row["row_id"], "source": info["name"], "status": "grade_mismatch"})
                    continue
                labels = {}
                conflicts = []
                for key in ("stains", "holes"):
                    value = original.get(key)
                    before, after = defect_label(row["labels"][key]), defect_label(value)
                    if before >= 0 and after >= 0 and before != after:
                        conflicts.append(key)
                        labels[key] = None
                    else:
                        labels[key] = value
                records.append({"row_id": row["row_id"], "source": info["name"], "status": "matched",
                                "source_sha256": hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
                                "labels": labels, "conflicts": conflicts})
        return records

    all_records, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, cluster): cluster for cluster in clusters}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                all_records.extend(future.result())
            except Exception as exc:
                cluster = futures[future]
                errors.append({"range": cluster[:2], "error": f"{type(exc).__name__}: {exc}"[:250]})
            if done % 25 == 0 or done == len(clusters):
                print(f"Recovered {done}/{len(clusters)} ranges; {len(all_records)} rows; errors={len(errors)}", flush=True)
    all_records.sort(key=lambda r: r["row_id"])
    output = ORIGINAL / "recovered-labels.jsonl"
    temporary = output.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(r) + "\n" for r in all_records))
    temporary.replace(output)
    summary = {"source_url": URL, "planned_bytes": budget, "records": len(all_records),
        "statuses": dict(Counter(r["status"] for r in all_records)), "errors": errors, "unmatched": unmatched,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "overlay_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "policy": "Only source-backed fields override mirror labels; old unknown holes remain unknown. Grade mismatch and binary conflicts are excluded."}
    (ORIGINAL / "recovery-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("errors", "unmatched")}, indent=2), flush=True)
    if errors or unmatched:
        raise SystemExit("Incomplete recovery; resume the same command before treating this overlay as complete")


if __name__ == "__main__":
    main()
