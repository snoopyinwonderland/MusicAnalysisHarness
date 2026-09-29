"""Measure-context harmony episodes and explainable category evidence.

This is an offline, train-source retrieval prototype, not a calibrated classifier.
Annotation labels categorize reference episodes; query features use score facts only.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .formal_ir import q
from .harmony_case_retrieval import _f, _sounds, load_prepared_package
from .harmony_label_taxonomy import classify_harmony_label

VERSION = "harmony-episodes-0.1.0"


def cosine(a, b):
    norm = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / norm if norm else None


def describe_window(sounds, start, end, anchor):
    rows = [r for r in sounds if r[0] < end and r[1] > start]
    if not rows or end <= start:
        return None
    profile = [0.0] * 12
    attacks = defaultdict(list)
    for onset, release, midi, sid, spelling in rows:
        profile[(midi-anchor) % 12] += float(min(end, release)-max(start, onset))
        if start <= onset < end:
            attacks[onset].append(midi)
    total = sum(profile)
    profile = [v/total for v in profile]
    onsets = sorted(attacks)
    top = [max(attacks[t]) for t in onsets]
    bass = [min(attacks[t]) for t in onsets]
    # Contour describes attack-top geometry, not an asserted melody voice.
    contour = [0.0]*5
    for a, b in zip(top, top[1:]):
        d = b-a
        contour[0 if d < -2 else 1 if d < 0 else 2 if d == 0 else 3 if d <= 2 else 4] += 1
    attack_grid = [0.0]*8
    for t in onsets:
        attack_grid[min(7, int(8*(t-start)/(end-start)))] += 1
    grouped = sum(len(attacks[t]) >= 3 for t in onsets)
    texture = "sustained" if not onsets else (
        "block_chord" if grouped/len(onsets) >= .5 else
        "distributed_pitch_activity" if len(onsets) >= 3 and sum(v > 0 for v in profile) >= 3 else
        "sparse_or_mixed")
    return {"span": {"start": q(start), "end": q(end)}, "pitch_profile": profile,
            "contour": contour, "attack_grid": attack_grid, "texture": texture,
            "bass_path": [(p-anchor) % 12 for p in bass],
            "sounding_event_ids": sorted(r[3] for r in rows),
            "pitch_spellings": sorted({r[4] for r in rows})}


def extract_episode(ir, span, sounds=None):
    sounds = _sounds(ir) if sounds is None else sounds
    start, end = _f(span["start"]), _f(span["end"])
    if end <= start:
        raise ValueError("Episode requires a positive span")
    active = [r for r in sounds if r[0] < end and r[1] > start]
    if not active:
        raise ValueError("Episode contains no pitched sounds")
    onset_rows = [r for r in active if r[0] <= start < r[1]]
    if not onset_rows:
        first = min(r[0] for r in active)
        onset_rows = [r for r in active if r[0] == first]
    anchor = min(r[2] for r in onset_rows)
    measures = sorted({(_f(m["global_start_quarter"]),
                        _f(m["global_start_quarter"])+_f(m["actual_duration_quarter"]))
                       for m in ir.get("measures", [])})
    overlaps = [i for i, (a, b) in enumerate(measures) if a < end and b > start]
    score_end = max(r[1] for r in sounds)
    left = measures[max(0, overlaps[0]-1)][0] if overlaps else max(0, start-4)
    right = measures[min(len(measures)-1, overlaps[-1]+2)][1] if overlaps else min(score_end, end+8)
    following = sorted({end, right, *(b for a, b in measures if end < b < right)})
    stages = [("before", left, start), ("current", start, end)]
    stages += [(f"after_{i}", a, b) for i, (a, b) in enumerate(zip(following, following[1:]))]
    windows = {name: describe_window(sounds, a, b, anchor) for name, a, b in stages}
    return {"version": VERSION, "span": span, "context_span": {"start": q(left), "end": q(right)},
            "anchor_midi": anchor, "windows": windows,
            "policy": "single_anchor_all_windows; original_spelling_preserved; no_query_labels"}


def categorize(annotation):
    components = dict(annotation.get("components", {}))
    raw = annotation.get("raw_fields", {})
    components.update({k: raw[k] for k in ("form", "relativeroot") if raw.get(k)})
    tax = classify_harmony_label(annotation["raw_label"], components)
    # DCML numeral and quality are separate columns. Do not lose diminished quality.
    quality = components.get("form") or tax["quality_marker"] or "unspecified"
    return {"family": tax["family"], "target": components.get("relativeroot") or tax["applied_to"],
            "quality": quality, "inversion": tax["inversion_figure"],
            "global_key": components.get("globalkey"), "local_key": components.get("localkey"),
            "parse_status": tax["parse_status"]}


def reference_arrival(annotation, following):
    """Source-label observation, not proof of voice-leading resolution."""
    category = categorize(annotation)
    target = category["target"]
    if not target:
        return "not_applied"
    if "/" in target:
        return "nested_target_unresolved"
    for index, other in enumerate(following[:3]):
        c = categorize(other)
        if (c["global_key"], c["local_key"]) != (category["global_key"], category["local_key"]):
            return "key_context_changed"
        numeral = other.get("components", {}).get("numeral")
        if numeral == target and not c["target"]:
            return "next_annotated_target" if index == 0 else "delayed_annotated_target"
    return "target_not_observed_in_three_annotations"


def compare_episodes(a, b):
    channels = {}
    weighted = []
    for stage in sorted(set(a["windows"]) | set(b["windows"])):
        x, y = a["windows"].get(stage), b["windows"].get(stage)
        if not x or not y:
            continue
        weight = 2 if stage == "current" else 1
        for field, factor in (("pitch_profile", .75), ("contour", .15), ("attack_grid", .10)):
            value = cosine(x[field], y[field])
            if value is not None:
                channels[f"{stage}.{field}"] = round(value, 6)
                weighted.append((value, weight*factor))
    score = sum(v*w for v, w in weighted)/sum(w for _, w in weighted) if weighted else 0
    return {"score": round(score, 6), "channels": channels,
            "context_stages_compared": sum(k.endswith("pitch_profile") and not k.startswith("current.") for k in channels)}


def judge_episode(query, references, identity, limit=20):
    """Aggregate evidence by type, with one vote per independent work per type."""
    if not identity.get("work_family_id") or not identity.get("annotation_lineage_id"):
        raise ValueError("Query identity is required for leakage-safe comparison")
    groups = defaultdict(list)
    for ref in references:
        d = ref["identity"]
        if d.get("split") != "train" or any(d.get(k) == identity.get(k) for k in
                ("work_family_id", "annotation_lineage_id", "score_id" ) if identity.get(k)):
            continue
        comparison = compare_episodes(query, ref["episode"])
        key = ref["category"]["family"]
        groups[key].append((comparison["score"], ref, comparison))
    alternatives = []
    for family, rows in groups.items():
        independent = {}
        for score, ref, comparison in sorted(rows, key=lambda r: (-r[0], r[1]["case_id"])):
            independent.setdefault(ref["identity"]["work_family_id"], (score, ref, comparison))
        best = list(independent.values())[:3]
        value = sum(r[0] for r in best)/len(best)
        alternatives.append({"family": family, "score": round(value, 6), "independent_works": len(best),
                             "evidence": [{"case_id": r[1]["case_id"], "category": r[1]["category"],
                                           "texture": r[1]["episode"]["windows"]["current"]["texture"],
                                           **r[2]} for r in best]})
    alternatives.sort(key=lambda r: (-r["score"], r["family"]))
    margin = alternatives[0]["score"]-alternatives[1]["score"] if len(alternatives)>1 else 0
    supported = bool(alternatives and alternatives[0]["independent_works"] >= 2 and
                     alternatives[0]["score"] >= .75 and margin >= .05 and
                     all(e["context_stages_compared"] for e in alternatives[0]["evidence"]))
    return {"status": "candidate" if supported else "ambiguous" if alternatives else "abstained",
            "alternatives": alternatives[:limit], "margin": round(margin, 6),
            "score_is_probability": False, "automatic_promotion": False}


def build(source, case_library, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(s) for s in Path(case_library).read_text(encoding="utf-8").splitlines() if s]
    by_ir = defaultdict(list)
    # Holdout episodes are excluded from this experiment.
    for c in cases:
        if c["dataset_identity"]["split"] in {"train", "dev"}:
            by_ir[c["ir_document_id"]].append(c)
    records, errors = [], []
    for folder in sorted(Path(source).rglob("canonical_music_ir.json")):
        ir = json.loads(folder.read_text(encoding="utf-8"))
        selected = by_ir.get(ir["ir_document_id"], [])
        if not selected:
            continue
        package = load_prepared_package(folder.parent)
        annotations = {a["annotation_id"]: a for a in package["annotations"]}
        ordered = sorted((a for a in package["annotations"] if (a.get("target") or {}).get("span")),
                         key=lambda a: _f(a["target"]["span"]["start"]))
        sounds = _sounds(ir)
        for case in selected:
            try:
                annotation = annotations[case["annotation_id"]]
                episode = extract_episode(ir, case["feature"]["span"], sounds)
                following_annotations = [a for a in ordered if
                                         _f(a["target"]["span"]["start"]) >= _f(episode["span"]["end"])]
                category = categorize(annotation)
                category["arrival_observation"] = reference_arrival(annotation, following_annotations)
                start, end = _f(episode["context_span"]["start"]), _f(episode["context_span"]["end"])
                neighbors = [{"annotation_id": a["annotation_id"], "raw_label": a["raw_label"],
                              "target": a["target"]} for a in package["annotations"]
                             if (a.get("target") or {}).get("span") and
                             _f(a["target"]["span"]["start"]) < end and
                             _f(a["target"]["span"]["end"]) > start]
                records.append({"case_id": case["case_id"], "version": VERSION,
                                "identity": {**case["dataset_identity"], "score_id": case["score_id"]},
                                "category": category, "episode": episode,
                                "reference_progression": neighbors, "provenance": case["provenance"],
                                "ir_path": str(folder.resolve()), "training_eligible": False})
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({"case_id": case["case_id"], "error": str(exc)})
    (output/"episodes.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in records), encoding="utf-8")
    types = defaultdict(list)
    for r in records:
        if r["identity"]["split"] == "train":
            c = r["category"]
            key = (c["family"], c["target"], c["quality"], c["arrival_observation"],
                   r["episode"]["windows"]["current"]["texture"])
            types[key].append(r["case_id"])
    index = [{"family": k[0], "target": k[1], "quality": k[2], "arrival": k[3],
              "texture": k[4], "case_ids": v, "case_count": len(v)} for k, v in types.items()]
    (output/"type-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"version": VERSION, "cases": len(records), "splits": dict(Counter(r["identity"]["split"] for r in records)),
              "families": dict(Counter(r["category"]["family"] for r in records)),
              "textures": dict(Counter(r["episode"]["windows"]["current"]["texture"] for r in records)),
              "reference_type_count": len(index),
              "errors": errors, "holdout_evaluated": False, "production_enabled": False}
    (output/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def evaluate(output, per_family=4):
    """Stratified dev diagnostic. Never tune or inspect holdout labels here."""
    output = Path(output)
    records = [json.loads(s) for s in (output/"episodes.jsonl").read_text(encoding="utf-8").splitlines() if s]
    train = [r for r in records if r["identity"]["split"] == "train"]
    groups = defaultdict(list)
    for r in records:
        if r["identity"]["split"] == "dev":
            groups[r["category"]["family"]].append(r)
    queries = [r for family in sorted(groups) for r in sorted(groups[family], key=lambda r: r["case_id"])[:per_family]]
    def surface(ep):
        return {**ep, "windows": {"current": ep["windows"]["current"]}}
    baseline = [{**r, "episode": surface(r["episode"])} for r in train]
    results = []
    for r in queries:
        contextual = judge_episode(r["episode"], train, r["identity"])
        plain = judge_episode(surface(r["episode"]), baseline, r["identity"])
        expected = r["category"]["family"]
        def top(result):
            return result["alternatives"][0]["family"] if result["alternatives"] else None
        results.append({"case_id": r["case_id"], "expected_family": expected,
                        "surface_top1": top(plain), "context_top1": top(contextual),
                        "context_status": contextual["status"], "decision": contextual})
    n = len(results)
    report = {"version": VERSION, "query_count": n, "train_reference_count": len(train),
              "sampling": f"first {per_family} dev case IDs per family; stratified diagnostic, not population accuracy",
              "known_annotation_boundaries": True, "holdout_evaluated": False,
              "surface_family_top1": sum(r["surface_top1"] == r["expected_family"] for r in results)/n if n else None,
              "context_family_top1": sum(r["context_top1"] == r["expected_family"] for r in results)/n if n else None,
              "candidate_count": sum(r["context_status"] == "candidate" for r in results),
              "results": results}
    (output/"dev-diagnostic.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: v for k, v in report.items() if k != "results"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source")
    p.add_argument("--case-library")
    p.add_argument("--output", required=True)
    p.add_argument("--evaluate", action="store_true")
    args = p.parse_args()
    if not args.evaluate and (not args.source or not args.case_library):
        p.error("--source and --case-library are required to build episodes")
    result = evaluate(args.output) if args.evaluate else build(args.source, args.case_library, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
