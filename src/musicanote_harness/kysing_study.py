"""Offline weak-supervision study. Musical frames never depend on lyrics.

This is a source-level research adapter, not a replacement Canonical IR parser.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import heapq
import json
from pathlib import Path
import re
import unicodedata
from xml.etree import ElementTree as ET


CHORD = re.compile(r"[A-G](?:#|b)?(?:m|maj|min|dim|aug|sus|add)?[0-9]*(?:\([^)]*\))?(?:/[A-G](?:#|b)?)?")
MARKERS = {"intro", "ending", "trill", "(in)trill", "instrumental"}


def classify(text):
    value = unicodedata.normalize("NFC", text).strip()
    if "\ufffd" in value:
        return "corrupt"
    if value.casefold() in MARKERS:
        return "marker"
    # A/I etc. can be genuine words; chord-shaped tokens stay ambiguous.
    if CHORD.fullmatch(value):
        return "chord_or_word"
    if any(unicodedata.category(c).startswith("L") for c in value):
        return "lexical"
    return "symbol"


def q(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def extract(root):
    """Exact written timeline; identities depend on source position, never text."""
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    notes, targets, harmonies, warnings = [], [], [], []
    for pi, part in enumerate(root.findall("part")):
        start, divisions = Fraction(0), 1
        for mi, measure in enumerate(part.findall("measure")):
            cursor = previous = extent = Fraction(0)
            for ei, element in enumerate(measure):
                if element.tag == "attributes":
                    divisions = int(element.findtext("divisions", str(divisions)))
                elif element.tag in {"backup", "forward"}:
                    duration = Fraction(element.findtext("duration", "0")) / divisions
                    cursor += duration * (-1 if element.tag == "backup" else 1)
                    extent = max(extent, cursor)
                elif element.tag == "harmony":
                    harmonies.append({"part": pi, "time": q(start + cursor + Fraction(element.findtext("offset", "0")) / divisions), "root_step": element.findtext("root/root-step"), "root_alter": element.findtext("root/root-alter", "0"), "kind": element.findtext("kind"), "status": "source_symbol_not_roman_analysis"})
                elif element.tag == "note":
                    onset = previous if element.find("chord") is not None else cursor
                    duration = Fraction(element.findtext("duration", "0")) / divisions
                    if element.find("grace") is not None:
                        duration = Fraction(0)
                    if element.find("chord") is None:
                        previous = onset
                        cursor += duration
                    extent = max(extent, onset + duration, cursor)
                    pitch = element.find("pitch")
                    if pitch is None:
                        continue
                    step = pitch.findtext("step")
                    midi = Fraction(12 * (int(pitch.findtext("octave")) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]) + Fraction(pitch.findtext("alter", "0"))
                    ref = f"p{pi}/m{mi}/e{ei}"
                    notes.append({"ref": ref, "voice": (pi, element.findtext("voice", "1")), "start": start + onset, "end": start + onset + duration, "pitch": midi, "attack": not any(t.get("type") == "stop" for t in element.findall("tie")), "measure": mi, "position": onset})
                    for lyric in element.findall("lyric"):
                        text = "".join(lyric.itertext()) if lyric.find("text") is None else "".join(x.text or "" for x in lyric.findall("text"))
                        targets.append({"ref": ref, "verse": lyric.get("number", "1"), "category": classify(text), "punctuation": any(c in text for c in ",;:.!?，、；：。！？"), "extend": lyric.find("extend") is not None})
            if extent == 0:
                warnings.append(f"empty measure p{pi}/m{mi}: timing needs review")
            start += extent
    frames = []
    vertical = {}
    active, releases = {}, []
    by_start = defaultdict(list)
    for note in notes:
        by_start[note['start']].append(note)
    for time in sorted(by_start):
        while releases and releases[0][0] <= time:
            _, ref = heapq.heappop(releases)
            active.pop(ref, None)
        for note in by_start[time]:
            if note['end'] > time:
                active[note['ref']] = note
                heapq.heappush(releases, (note['end'], note['ref']))
        vertical[time] = list(active.values())
    voices = defaultdict(list)
    for note in notes:
        voices[note["voice"]].append(note)
    for voice, events in voices.items():
        events.sort(key=lambda n: (n["start"], n["ref"]))
        prior_end = Fraction(0)
        prior_pitch = None
        for note in events:
            if note["attack"]:
                active = vertical[note['start']]
                frames.append({"frame_id": note["ref"], "time": q(note["start"]), "voice": list(voice), "measure_index": note["measure"], "features": {"voice_gap_before": q(max(Fraction(0), note["start"] - prior_end)), "duration": q(note["end"] - note["start"]), "onset_in_measure": q(note["position"]), "pitch_delta": q(note["pitch"] - prior_pitch) if prior_pitch is not None else None, "active_pitch_classes": sorted({str(n["pitch"] % 12) for n in active}), "lowest_pitch": str(min((n["pitch"] for n in active), default=note["pitch"])), "active_note_count": len(active)}})
            prior_end = max(prior_end, note["end"])
            prior_pitch = note["pitch"]
    return frames, targets, harmonies, warnings


def run(manifest, source, output, limit=30):
    entries = json.loads(Path(manifest).read_text(encoding="utf-8"))["files"]
    if limit and len(entries) > limit:
        entries = [entries[round(i * (len(entries)-1) / (limit-1))] for i in range(limit)] if limit > 1 else entries[:1]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results, patterns = [], Counter()
    for entry in entries:
        path = Path(source) / Path(entry["file"]).name
        try:
            raw = path.read_bytes()
            root = ET.fromstring(raw)
            frames, targets, harmonies, warnings = extract(root)
            for parent in root.iter():
                for child in list(parent):
                    if child.tag == "lyric":
                        parent.remove(child)
            stripped_frames, _, stripped_harmony, _ = extract(root)
            if frames != stripped_frames or harmonies != stripped_harmony:
                raise AssertionError("lyric-removal invariance failed")
            by_ref = {f["frame_id"]: f for f in frames}
            cases = []
            for target in targets:
                if target["category"] != "lexical" or target["ref"] not in by_ref:
                    continue
                frame = by_ref[target["ref"]]
                gap_value = frame["features"]["voice_gap_before"]
                gap = Fraction(gap_value["numerator"], gap_value["denominator"])
                pattern = "musical_gap_before" if gap > 0 else "continuous_entry"
                patterns[pattern] += 1
                if target["punctuation"]:
                    patterns["punctuation_on_current_token"] += 1
                cases.append({"frame_id": target["ref"], "pattern": pattern, "punctuation_on_current_token": target["punctuation"], "status": "study_case_not_phrase_label"})
            package = {"version": "0.1.0", "source_sha256": hashlib.sha256(raw).hexdigest(), "musical_feature_frames": frames, "weak_target_observations": targets, "source_harmony_symbols": harmonies, "cases": cases, "warnings": warnings, "lyrics_removal_invariance": True}
            (output / (path.stem + ".json")).write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append({"file": path.name, "frames": len(frames), "categories": dict(Counter(t["category"] for t in targets)), "harmony_symbols": len(harmonies), "cases": len(cases), "warnings": warnings, "invariance": True})
        except Exception as exc:
            results.append({"file": path.name, "error": str(exc)})
    report = {"files": results, "patterns": dict(patterns), "selection": "evenly_spaced_from_external_manifest", "limitations": ["Manifest selection may underrepresent non-space-separated languages", "Voice gap is a musical rest proxy, not measured breathing", "No V/I or phrase ground truth inferred", "Per-part written timing requires Canonical IR alignment validation before training", "Source-position IDs are research references, not durable Canonical IDs"]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    result = run(args.manifest, args.source, args.output, args.limit)
    print(json.dumps({"files": len(result["files"]), "errors": sum("error" in r for r in result["files"]), "patterns": result["patterns"]}, indent=2))
