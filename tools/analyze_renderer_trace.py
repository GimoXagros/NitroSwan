#!/usr/bin/env python3
"""Check a WSC_VIDEO_TRACE CSV for completed-frame ownership mismatches."""

import argparse
import csv
import json
from pathlib import Path


OBJ_BANK_BYTES = 16384


def number(row, key):
    return int(row[key], 0)


def analyze(rows):
    findings = []
    tile_owner = {}
    counts = {"ws_rows": 0, "vblank_rows": 0, "palette_drops": 0}
    for row in rows:
        event = row["event"]
        frame = number(row, "ws_frame")
        dirty = number(row, "obj_dirty_tiles")
        seed = number(row, "obj_seed_bytes")
        counts["palette_drops"] += number(row, "palette_drops")
        if event == "W":
            counts["ws_rows"] += 1
            ready = number(row, "obj_ready_frame")
            latch = number(row, "sprite_latch_frame")
            tile_generation = number(row, "obj_ready_tile_gen")
            if ready != frame or latch != frame:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "completion-frame-mismatch"})
            if dirty and seed != OBJ_BANK_BYTES:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "dirty-frame-without-full-seed"})
            if seed == OBJ_BANK_BYTES:
                tile_owner[tile_generation] = frame
        elif event == "V":
            counts["vblank_rows"] += 1
            published = number(row, "obj_published_frame")
            oam = number(row, "oam_frame")
            tile_generation = number(row, "obj_published_tile_gen")
            if published != oam:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "oam-frame-mismatch"})
            if dirty and tile_owner.get(tile_generation) != published:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "dirty-tile-owner-mismatch"})
        else:
            findings.append({"seq": number(row, "seq"),
                             "kind": "unknown-event"})
    return {"status": "PASS" if not findings else "FAIL",
            "counts": counts, "findings": findings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    with args.trace.open(newline="", encoding="utf-8") as source:
        result = analyze(list(csv.DictReader(source)))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
