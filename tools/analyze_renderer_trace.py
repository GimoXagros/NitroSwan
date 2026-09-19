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
    incomplete = []
    tile_owner = {}
    counts = {"ws_rows": 0, "vblank_rows": 0, "palette_drops": 0,
              "ring_drops_max": 0}
    previous_seq = None
    previous_epoch = None
    for record, row in enumerate(rows, 1):
        required = ('seq', 'ws_frame', 'obj_dirty_tiles', 'obj_seed_bytes',
                    'palette_drops', 'obj_ready_frame', 'sprite_latch_frame',
                    'obj_ready_tile_gen', 'obj_published_frame', 'oam_frame',
                    'obj_published_tile_gen')
        try:
            for key in required:
                number(row, key)
            seq = number(row, 'seq')
            epoch = int(row.get('epoch', '0'), 0)
            drops = int(row.get('ring_drops', '0'), 0)
            event = row['event']
        except (KeyError, TypeError, ValueError):
            incomplete.append({'record': record, 'kind': 'malformed-record'})
            continue
        if previous_seq is not None and seq != previous_seq + 1:
            incomplete.append({'record': record, 'kind': 'sequence-gap-or-new-session'})
            tile_owner.clear()
        if epoch != previous_epoch:
            tile_owner.clear()
        previous_seq, previous_epoch = seq, epoch
        counts['ring_drops_max'] = max(counts['ring_drops_max'], drops)
        event = row["event"]
        frame = number(row, "ws_frame")
        dirty = number(row, "obj_dirty_tiles")
        seed = number(row, "obj_seed_bytes")
        if event == "W":
            counts["ws_rows"] += 1
            # Drops belong to a completed WS frame, not each host replay.
            counts["palette_drops"] += number(row, "palette_drops")
            ready = number(row, "obj_ready_frame")
            latch = number(row, "sprite_latch_frame")
            tile_generation = number(row, "obj_ready_tile_gen")
            if latch == 0xFFFFFFFF:
                incomplete.append({'record': record, 'kind': 'latch-not-observed'})
            if ready != frame or (latch != 0xFFFFFFFF and latch != frame):
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
            if published == 0:
                continue  # renderer quiesced; no completed frame to compare
            if oam == 0xFFFFFFFF:
                incomplete.append({'record': record, 'kind': 'oam-source-not-observed'})
            elif published != oam:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "oam-frame-mismatch"})
            if dirty and tile_generation not in tile_owner:
                incomplete.append({'record': record, 'kind': 'missing-tile-owner-record'})
            elif dirty and tile_owner[tile_generation] != published:
                findings.append({"seq": number(row, "seq"),
                                 "kind": "dirty-tile-owner-mismatch"})
        else:
            findings.append({"seq": number(row, "seq"),
                             "kind": "unknown-event"})
    if not counts['ws_rows'] or not counts['vblank_rows']:
        incomplete.append({'kind': 'missing-clock-domain'})
    if counts['ring_drops_max'] or counts['palette_drops']:
        incomplete.append({'kind': 'dropped-events'})
    return {"status": 'FAIL' if findings else 'BLOCKED' if incomplete else 'PASS',
            "counts": counts, "findings": findings, 'incomplete': incomplete}


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
