"""Joint span/chord search with conditional non-chord-tone hypotheses.

Source labels and phrase labels are never inputs. Scores are heuristic costs.
"""
from collections import defaultdict
from fractions import Fraction
from .formal_ir import q
from .harmony_surface import TEMPLATES, PITCH_NAMES

VERSION = "joint-span-chord-nct-0.1.0"


def f(x):
    return Fraction(x["numerator"], x["denominator"])


def prepare(ir):
    notes = {n["note_id"]: n for n in ir.get("note_events", [])}
    rows = []
    voices = defaultdict(list)
    for s in ir["sounding_events"]:
        midi = s["pitch"].get("midi_pitch")
        a, b = f(s["span"]["start"]), f(s["span"]["end"])
        if midi is None or b <= a:
            continue
        n = notes.get(s.get("attack_note_id"), {})
        r = {"start": a, "end": b, "pitch": midi, "id": s["sounding_event_id"],
             "voice": n.get("voice_id"), "spelling": s["pitch"].get("spelling")}
        rows.append(r)
        if r["voice"]:
            voices[r["voice"]].append(r)
    neighbors = {}
    for sequence in voices.values():
        groups = defaultdict(list)
        for r in sequence:
            groups[r["start"]].append(r)
        times = sorted(groups)
        for i, t in enumerate(times):
            # Polyphonic chord members cannot be assumed to be one melody chain.
            if len(groups[t]) == 1:
                previous = groups[times[i-1]] if i else []
                following = groups[times[i+1]] if i+1 < len(times) else []
                neighbors[groups[t][0]["id"]] = (previous[0] if len(previous)==1 else None,
                                                 following[0] if len(following)==1 else None)
    return rows, neighbors


def nct(r, pcs, start, end, neighbors, beat):
    p, nxt = neighbors.get(r["id"], (None, None))
    if nxt is None or nxt["start"]-r["end"] > beat or nxt["start"] > end+beat:
        return None
    departure = nxt["pitch"]-r["pitch"]
    if nxt["pitch"] % 12 not in pcs:
        return None
    if r["start"] < start and departure in (-1, -2) and nxt["start"] < end:
        return {"type": "suspension_like", "strength": .65, "refs": [r["id"], nxt["id"]]}
    if p is None or r["start"]-p["end"] > beat or p["pitch"] % 12 not in pcs:
        return None
    approach = r["pitch"]-p["pitch"]
    short = r["end"]-r["start"] <= beat/2
    if short and 0 < abs(approach) <= 2 and 0 < abs(departure) <= 2:
        kind = "neighbor_like" if p["pitch"] == nxt["pitch"] else (
            "passing_like" if approach*departure > 0 else None)
        if kind:
            return {"type": kind, "strength": .8, "refs": [p["id"], r["id"], nxt["id"]]}
    return None


def candidates(rows, neighbors, start, end, beat, limit=5, min_shared_pcs=2, nct_evaluator=None):
    evaluate_nct = nct_evaluator or nct
    active = [r for r in rows if r["start"] < end and r["end"] > start]
    if not active:
        return [{"label": "rest", "root": None, "pcs": [], "cost": 0, "nct": []}]
    weights = [(r, float(min(r["end"], end)-max(r["start"], start))) for r in active]
    total = sum(w for _, w in weights)
    at_start = [r for r in active if r["start"] <= start < r["end"]]
    bass = min((r["pitch"] for r in at_start or active)) % 12
    choices = []
    for root in range(12):
        for quality, intervals in TEMPLATES:
            pcs = {(root+i) % 12 for i in intervals}
            observed = {r["pitch"] % 12 for r in active}
            if len(pcs & observed) < min_shared_pcs:
                continue
            unexplained = 0
            evidence = []
            for r, w in weights:
                if r["pitch"] % 12 not in pcs:
                    hypothesis = evaluate_nct(r, pcs, start, end, neighbors, beat)
                    unexplained += w*(1-hypothesis["strength"] if hypothesis else 1)
                    if hypothesis:
                        evidence.append({"sounding_event_id": r["id"], **hypothesis})
            coverage = len(pcs & observed)/len(pcs)
            loss = .7*unexplained/total + .3*(1-coverage) + .04*(bass != root)
            choices.append({"label": f"{PITCH_NAMES[root]}:{quality}", "root": root,
                            "pcs": sorted(pcs), "cost": loss, "nct": evidence,
                            "coverage": coverage, "unexplained_weight_ratio": unexplained/total})
    choices.sort(key=lambda c: (c["cost"], c["label"]))
    return choices[:limit] or [{"label": "unknown", "root": None, "pcs": [], "cost": .8, "nct": []}]


def analyze_joint(ir, max_beats=8, candidate_provider=None, segment_policy=None, analysis_span=None):
    choose = candidate_provider or candidates
    rows, neighbors = prepare(ir)
    if analysis_span is not None:
        window_start, score_end = f(analysis_span['start']), f(analysis_span['end'])
        if window_start < 0 or score_end <= window_start:
            raise ValueError('invalid_analysis_span')
        # Neighbors come from the original score; never manufacture attacks/releases.
        rows = [r for r in rows if r['start'] < score_end and r['end'] > window_start]
    elif not rows:
        return {"engine_version": VERSION, "segments": [], "calibrated": False}
    else:
        window_start = Fraction(0)
        score_end = max(r["end"] for r in rows)
    # Sound release points are included so silence remains explicit.
    points = {window_start, score_end}
    points.update(t for r in rows for t in (r['start'], r['end']) if window_start <= t <= score_end)
    measures = sorted(ir.get("measures", []), key=lambda m: f(m["global_start_quarter"]))
    for m in measures:
        a = f(m["global_start_quarter"])
        b = min(score_end, a+f(m["actual_duration_quarter"]))
        unit = Fraction(4, m["time_signature"]["beat_type"])
        if a < window_start:
            a += ((window_start-a)//unit)*unit
        while a <= b:
            if a >= window_start:
                points.add(a)
            a += unit
    times = sorted(points)
    states = {0: {None: (0, [])}}
    for j in range(1, len(times)):
        end = times[j]
        states[j] = {}
        for i in range(j-1, -1, -1):
            start = times[i]
            m = next((m for m in reversed(measures) if f(m["global_start_quarter"]) <= start), None)
            beat = Fraction(4, m["time_signature"]["beat_type"]) if m else Fraction(1)
            if end-start > max_beats*beat:
                continue
            duration = float((end-start)/beat)
            for c in choose(rows, neighbors, start, end, beat):
                key = c["label"]
                for previous_cost, path in states[i].values():
                    previous = path[-1]["selected"] if path else None
                    transition = .04 if previous and previous["label"] != key else 0
                    # Weak syntactic evidence: root movement from dominant to target.
                    if previous and previous["root"] is not None and c["root"] is not None:
                        if previous["label"].endswith(":dominant7") and (previous["root"]-c["root"]) % 12 == 7:
                            transition -= .06
                    policy = segment_policy(rows, start, end, beat, previous, c) if segment_policy else None
                    charge = policy['charge'] if policy else .15
                    if not 0 <= charge <= .15:
                        raise ValueError('segment_charge_out_of_range')
                    cost = previous_cost + duration*c["cost"] + charge + transition
                    if key not in states[j] or cost < states[j][key][0]:
                        states[j][key] = (cost, path+[{"span": {"start": q(start), "end": q(end)},
                                                      "selected": c, "beat_unit_quarter": q(beat),
                                                      **({'segment_policy':policy} if policy else {})}])
        states[j] = dict(sorted(states[j].items(), key=lambda item: item[1][0])[:12])
    ranked = sorted(states[len(times)-1].values(), key=lambda item: item[0])
    if not ranked:
        raise ValueError("Timeline has an unsupported gap; provide complete measure grid")
    best_cost, path = ranked[0]
    for s in path:
        s["alternatives"] = choose(rows, neighbors, f(s["span"]["start"]), f(s["span"]["end"]), f(s["beat_unit_quarter"]))
        s["status"] = "hypothesis"
    return {"engine_version": VERSION, "input_policy": "canonical_ir_only_no_phrase_or_source_labels",
            **({'analysis_span': analysis_span, 'window_contract_version': 'absolute-window-0.1.0',
                'time_policy': 'absolute_original_events_full_score_neighbors',
                'context_limit': 'search history outside analysis_span is not optimized'} if analysis_span is not None else {}),
            "calibrated": False, "segments": path, "path_cost": best_cost,
            "competing_path_costs": [cost for cost, _ in ranked[1:4]],
            "limitations": ["NCT labels conditional on chord hypothesis", "nearest sequence requires monophonic voice",
                            "No local-key or secondary-function inference", "Beam pruning is approximate",
                            "No appoggiatura or anticipation classifier yet"]}
