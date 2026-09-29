"""Offline textbook/case links; source labels are not inferred musical truth."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .harmony_case_retrieval import _f, _sounds

VERSION = "harmony-curriculum-0.1.0"
QUALITIES = {"M": "major", "m": "minor", "o": "diminished", "+": "augmented"}
TEMPLATES = {"major": (0, 4, 7), "minor": (0, 3, 7),
             "diminished": (0, 3, 6), "augmented": (0, 4, 8)}


def concepts():
    """Reading prerequisites stay explicit: registration is not completed reading."""
    rows = []
    for unit, title, page, deps in [
        (1, "Key, Scales, and Modes", 3, []),
        (2, "Intervals", 21, ["hvl.unit01"]),
        (3, "Rhythm and Meter", 35, ["hvl.unit01", "hvl.unit02"]),
        (4, "Triads and Seventh Chords", 46, ["hvl.unit02", "hvl.unit03"]),
    ]:
        rows.append({"concept_id": f"hvl.unit{unit:02}", "title": title,
                     "prerequisites": deps, "reading_status": "toc_verified",
                     "source": {"book": "Harmony and Voice Leading", "edition": 4,
                                "unit": unit, "printed_start_page": page,
                                "pdf_start_page": {1:19,2:37,3:51,4:62}[unit]}})
        rows[-1]["reading_status"] = "text_reviewed_visual_examples_sampled"
        rows[-1]["reviewed_sections"] = list(range(1,{1:26,2:18,3:12,4:22}[unit]))
        rows[-1]["implementation_status"] = "partial_features_not_full_interpretation"
    for quality in TEMPLATES:
        rows.append({"concept_id": f"hvl.triad.{quality}", "title": f"{quality} triad",
                     "prerequisites": ["hvl.unit04"], "reading_status": "triad_sections_reviewed",
                     "source": {"book": "Harmony and Voice Leading", "edition": 4,
                                "unit": 4, "printed_start_page": 47, "pdf_start_page": 63},
                     "rule_status": "candidate_not_production"})
    rows.append({"concept_id":"hvl.seventh.shapes", "title":"Seventh qualities and inversions",
                 "prerequisites":["hvl.unit04"], "reading_status":"text_reviewed_visual_examples_sampled",
                 "source":{"book":"Harmony and Voice Leading", "edition":4, "unit":4,
                           "printed_start_page":56, "pdf_start_page":72, "sections":[12,13,14,15,16,17]},
                 "implementation_status":"complete_spelling_shapes_only",
                 "case_link_status":"pending_seventh_annotation_adapter",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit05", "title":"Introduction to Counterpoint",
                 "prerequisites":["hvl.unit02","hvl.unit03","hvl.unit04"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,17)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":5,
                           "printed_start_page":61,"pdf_start_page":77},
                 "implementation_status":"adjacent_melodic_geometry_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit06", "title":"Procedures of Four-Part Writing",
                 "prerequisites":["hvl.unit04","hvl.unit05"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,19)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":6,
                           "printed_start_page":93,"pdf_start_page":109},
                 "implementation_status":"explicit_pair_motion_geometry_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit07", "title":"I, V, and V7",
                 "prerequisites":["hvl.unit04","hvl.unit05","hvl.unit06"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,18)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":7,
                           "printed_start_page":115,"pdf_start_page":129},
                 "implementation_status":"conditional_melodic_chord_support_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit08", "title":"I6, V6, and VII6",
                 "prerequisites":["hvl.unit04","hvl.unit06","hvl.unit07"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,15)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":8,
                           "printed_start_page":131,"pdf_start_page":145},
                 "implementation_status":"conditional_bass_path_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit09", "title":"Inversions of V7",
                 "prerequisites":["hvl.unit07","hvl.unit08"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,14)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":9,
                           "printed_start_page":147,"pdf_start_page":161},
                 "implementation_status":"conditional_dominant_inversion_bass_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit10", "title":"Leading to V: IV, II, and II6",
                 "prerequisites":["hvl.unit07","hvl.unit08","hvl.unit09"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,19)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":10,
                           "printed_start_page":161,"pdf_start_page":175},
                 "implementation_status":"conditional_complete_snapshot_transition_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit11", "title":"The Cadential 6/4",
                 "prerequisites":["hvl.unit05","hvl.unit09","hvl.unit10"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,15)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":11,
                           "printed_start_page":181,"pdf_start_page":195},
                 "implementation_status":"conditional_snapshot_and_unambiguous_motion_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit12", "title":"VI and IV6",
                 "prerequisites":["hvl.unit10","hvl.unit11"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,8)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":12,
                           "printed_start_page":194,"pdf_start_page":208},
                 "implementation_status":"conditional_complete_shapes_and_lowest_pitch_geometry_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit13", "title":"Supertonic and Subdominant Seventh Chords",
                 "prerequisites":["hvl.unit05","hvl.unit09","hvl.unit11","hvl.unit12"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,14)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":13,
                           "printed_start_page":208,"pdf_start_page":222},
                 "implementation_status":"conditional_seventh_entry_exit_geometry_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit14", "title":"Other Uses of IV, IV6, and VI",
                 "prerequisites":["hvl.unit10","hvl.unit11","hvl.unit12","hvl.unit13"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,9)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":14,
                           "printed_start_page":229,"pdf_start_page":243},
                 "implementation_status":"conditional_role_candidates_and_cadence_evidence_requirements_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit15", "title":"V as a Key Area",
                 "prerequisites":["hvl.unit01","hvl.unit07","hvl.unit13","hvl.unit14"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,14)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":15,
                           "printed_start_page":245,"pdf_start_page":259},
                 "implementation_status":"dual_key_coordinates_and_shared_shape_compatibility_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit16", "title":"III and VII",
                 "prerequisites":["hvl.unit02","hvl.unit08","hvl.unit14","hvl.unit15"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,13)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":16,
                           "printed_start_page":265,"pdf_start_page":279},
                 "implementation_status":"conditional_mediant_coordinates_and_complete_shape_alternatives_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit17", "title":"5/3-Chord Techniques",
                 "prerequisites":["hvl.unit06","hvl.unit14","hvl.unit16"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,15)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":17,
                           "printed_start_page":285,"pdf_start_page":298},
                 "implementation_status":"supplied_root_relation_and_role_candidates_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit18", "title":"Diatonic Sequences",
                 "prerequisites":["hvl.unit06","hvl.unit15","hvl.unit16","hvl.unit17"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,23)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":18,
                           "printed_start_page":301,"pdf_start_page":314},
                 "implementation_status":"four_supplied_triad_patterns_and_separate_exact_voice_geometry_only",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit19", "title":"6/3-Chord Techniques",
                 "prerequisites":["hvl.unit08","hvl.unit17","hvl.unit18"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,10)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":19,
                           "printed_start_page":330,"pdf_start_page":343},
                 "implementation_status":"conditional_linear_neighbor_passing_and_sixth_substitution_roles_with_surface_observations",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit20", "title":"6/4-Chord Techniques",
                 "prerequisites":["hvl.unit11","hvl.unit18","hvl.unit19"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,19)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":20,
                           "printed_start_page":346,"pdf_start_page":359},
                 "implementation_status":"conditional_six_four_roles_and_separate_direct_stationary_bass_geometry",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit21", "title":"Melodic Figuration",
                 "prerequisites":["hvl.unit05","hvl.unit18","hvl.unit20"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,18)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":21,
                           "printed_start_page":371,"pdf_start_page":382},
                 "implementation_status":"rhythmic_slot_compound_correspondence_candidates_and_separate_conditional_triad_links",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit22", "title":"Rhythmic Figuration",
                 "prerequisites":["hvl.unit13","hvl.unit21"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,29)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":22,
                           "printed_start_page":392,"pdf_start_page":403},
                 "implementation_status":"literal_boundary_retention_and_separate_conditional_member_arrival_candidates",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit23", "title":"Leading-Tone Seventh Chords",
                 "prerequisites":["hvl.unit13","hvl.unit20","hvl.unit22"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,17)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":23,
                           "printed_start_page":421,"pdf_start_page":431},
                 "implementation_status":"spelled_seventh_hypotheses_surface_shapes_and_independent_member_exit_paths",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit24", "title":"Mixture",
                 "prerequisites":["hvl.unit16","hvl.unit22","hvl.unit23"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,9)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":24,
                           "printed_start_page":435,"pdf_start_page":445},
                 "implementation_status":"conditional_modal_coordinates_unselected_primary_secondary_mixture_templates_and_literal_paths",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit25", "title":"Remaining Uses of Seventh Chords",
                 "prerequisites":["hvl.unit18","hvl.unit22","hvl.unit23","hvl.unit24"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,17)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":25,
                           "printed_start_page":449,"pdf_start_page":459},
                 "implementation_status":"conditional_seventh_successions_apparent_triad_alternatives_and_literal_paths",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit26", "title":"Applied V and VII",
                 "prerequisites":["hvl.unit15","hvl.unit23","hvl.unit24","hvl.unit25"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,21)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":26,
                           "printed_start_page":467,"pdf_start_page":477},
                 "implementation_status":"spelled_applied_families_explicit_target_and_neighbor_comparison_with_critical_paths",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit27", "title":"Diatonic Modulation",
                 "prerequisites":["hvl.unit15","hvl.unit18","hvl.unit26"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,17)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":27,
                           "printed_start_page":494,"pdf_start_page":504},
                 "implementation_status":"dual_key_membership_local_syntax_and_contiguous_source_key_run_evidence",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit28", "title":"Seventh Chords with Added Dissonance",
                 "prerequisites":["hvl.unit21","hvl.unit22","hvl.unit23","hvl.unit26"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,12)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":28,
                           "printed_start_page":517,"pdf_start_page":525},
                 "implementation_status":"conditional_added_tone_geometry_core_presence_and_competing_shapes",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit29", "title":"The Phrygian II (Neapolitan)",
                 "prerequisites":["hvl.unit24","hvl.unit26","hvl.unit27","hvl.unit28"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,22)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":29,
                           "printed_start_page":536,"pdf_start_page":544},
                 "implementation_status":"conditional_bII_spelling_inversion_direct_voice_paths_and_context_shapes",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit30", "title":"Augmented Sixth Chords",
                 "prerequisites":["hvl.unit24","hvl.unit26","hvl.unit28","hvl.unit29"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,26)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":30,
                           "printed_start_page":559,"pdf_start_page":567},
                 "implementation_status":"conditional_spelled_families_literal_surface_and_joint_voice_geometry",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit31", "title":"Other Chromatic Chords",
                 "prerequisites":["hvl.unit24","hvl.unit25","hvl.unit26","hvl.unit30"],
                 "reading_status":"text_reviewed_visual_examples_sampled",
                 "reviewed_sections":list(range(1,19)),
                 "source":{"book":"Harmony and Voice Leading","edition":4,"unit":31,
                           "printed_start_page":589,"pdf_start_page":597},
                 "implementation_status":"selected_mixture_shapes_augmented_fifth_paths_and_common_tone_competition",
                 "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit32", "title":"Chromatic Voice-Leading Techniques",
        "prerequisites":["hvl.unit18","hvl.unit19","hvl.unit22","hvl.unit30","hvl.unit31"],
        "reading_status":"text_reviewed_visual_examples_sampled", "reviewed_sections":list(range(1,20)),
        "source":{"book":"Harmony and Voice Leading","edition":4,"unit":32,
                  "printed_start_page":610,"pdf_start_page":618},
        "implementation_status":"literal_chromatic_equal_step_alternating_runs_and_synchronized_pair_geometry",
        "rule_status":"candidate_not_production"})
    rows.append({"concept_id":"hvl.unit33", "title":"Chromaticism in Larger Contexts",
        "prerequisites":["hvl.unit24","hvl.unit26","hvl.unit27","hvl.unit30","hvl.unit31","hvl.unit32"],
        "reading_status":"text_reviewed_visual_examples_sampled", "reviewed_sections":list(range(1,17)),
        "source":{"book":"Harmony and Voice Leading","edition":4,"unit":33,
                  "printed_start_page":645,"pdf_start_page":653},
        "implementation_status":"conditional_enharmonic_templates_literal_boundary_continuity_and_source_key_context",
        "rule_status":"candidate_not_production"})
    for number, title, start, end, status in [
        (1, 'Keyboard Progressions', 670, 691, 'progression_metamorphic_tests_not_exercise_solver'),
        (2, 'Score Reduction', 692, 695, 'literal_doubling_and_reduction_proposal_contract_not_automatic_reduction'),
        (3, 'Roman Numerals and Registers; Explanatory Tables and Charts', 696, 707,
         'notation_profile_guard_and_sequence_bass_taxonomy_not_full_adapter')]:
        rows.append({'concept_id': f'hvl.appendix{number:02}', 'title': title,
            'prerequisites': ['hvl.unit33'], 'reading_status': 'available_text_and_all_page_images_reviewed',
            'source': {'book': 'Harmony and Voice Leading', 'edition': 4,
                       'printed_pages': [start, end], 'pdf_pages': [start+8, end+8],
                       'unavailable_printed_pages': [708] if number == 3 else []},
            'implementation_status': status, 'rule_status': 'candidate_not_production'})
    return rows


def same_span(a, b):
    return all(_f(a[k]) == _f(b[k]) for k in ("start", "end"))


def current_annotation(episode, annotations):
    """Never assume the first contextual annotation is the current one."""
    matches = [a for a in annotations
               if a.get("source_locator") == episode["provenance"]["source_locator"]
               and a.get("source_asset_sha256") == episode["provenance"]["source_asset_sha256"]
               and a.get("target", {}).get("score_id") == episode["identity"]["score_id"]
               and a.get("target", {}).get("span")
               and same_span(a["target"]["span"], episode["episode"]["span"])]
    if len(matches) != 1:
        raise ValueError(f"current_annotation_match_count={len(matches)}")
    return matches[0]


def observe(ir, span):
    start, end = _f(span["start"]), _f(span["end"])
    if end <= start:
        raise ValueError("nonpositive_span")
    rows = [r for r in _sounds(ir) if r[0] < end and r[1] > start]
    if not rows:
        raise ValueError("no_pitched_events")
    # Ignore microtonal input rather than silently rounding it through _sounds.
    selected = {r[3] for r in rows}
    if any(s["pitch"]["midi_pitch"] % 1 for s in ir["sounding_events"]
           if s["sounding_event_id"] in selected):
        raise ValueError("microtonal_observation_unsupported")
    pcs = {r[2] % 12 for r in rows}
    candidates = []
    for quality, intervals in TEMPLATES.items():
        for root in range(12):
            expected = {(root + i) % 12 for i in intervals}
            if len(pcs & expected) < 2:
                continue
            candidates.append({"root_pitch_class": root, "quality": quality,
                               "missing_pitch_classes": sorted(expected - pcs),
                               "extra_pitch_classes": sorted(pcs - expected)})
    onset = max(start, min(r[0] for r in rows))
    bass = min(r[2] for r in rows if r[0] <= onset < r[1])
    return {"sounding_event_ids": sorted(selected), "pitch_classes": sorted(pcs),
            "pitch_spellings": sorted({r[4] for r in rows}),
            "first_sounding_bass_midi": bass,
            "surface_triad_candidates": candidates,
            "warning": "Union of span pitches is not a harmonic or NCT verdict."}


def link_case(episode, annotation, ir):
    raw = annotation.get("raw_fields", {})
    quality = QUALITIES.get(raw.get("chord_type"))
    if quality is None:
        return None, "not_supported_triad_type"
    if any(raw.get(k) for k in ("changes", "added_tones", "special")):
        return None, "modified_triad_needs_review"
    figure = raw.get("figbass", "")
    if figure not in ("", "6", "64"):
        return None, "unsupported_triad_figure"
    if ir["score"]["score_id"] != episode["identity"]["score_id"]:
        raise ValueError("score_identity_mismatch")
    if annotation["target"]["ir_document_id"] != ir["ir_document_id"]:
        raise ValueError("ir_identity_mismatch")
    concept_id = f"hvl.triad.{quality}"
    digest = hashlib.sha256(f'{VERSION}|{concept_id}|{episode["case_id"]}|{annotation["annotation_id"]}'.encode()).hexdigest()[:20]
    return {"schema_version": VERSION, "link_id": f"clink_{digest}",
            "concept_id": concept_id, "case_id": episode["case_id"],
            "identity": episode["identity"], "annotation_id": annotation["annotation_id"],
            "source_label": annotation["raw_label"], "source_quality": quality,
            "source_inversion": {"": 0, "6": 1, "64": 2}[figure],
            "source_target": raw.get("relativeroot") or None,
            "target": annotation["target"], "context_span": episode["episode"]["context_span"],
            "reference_progression": episode["reference_progression"],
            "provenance": episode["provenance"], "ir_path": episode["ir_path"],
            "observation": observe(ir, annotation["target"]["span"]),
            "link_basis": "source_label", "review_status": "candidate",
            "training_eligible": False, "production_enabled": False}, None


def build(source, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cache, links, errors, skipped = {}, [], [], Counter()
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        if ep["identity"]["split"] != "train":
            skipped["non_train"] += 1
            continue
        try:
            path = Path(ep["ir_path"])
            if path not in cache:
                ir = json.loads(path.read_text(encoding="utf-8"))
                anns = [json.loads(s) for s in (path.parent / "imported_annotations.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
                cache[path] = ir, anns
            ir, anns = cache[path]
            annotation = current_annotation(ep, anns)
            record, reason = link_case(ep, annotation, ir)
            if record:
                links.append(record)
            else:
                skipped[reason] += 1
        except (KeyError, ValueError, TypeError, OSError) as exc:
            errors.append({"case_id": ep["case_id"], "error": str(exc)})
    counts = Counter(r["source_quality"] for r in links)
    report = {"version": VERSION, "links": len(links), "qualities": dict(counts),
              "coverage_gaps": [q for q in TEMPLATES if not counts[q]],
              "inversions": dict(Counter(str(r["source_inversion"]) for r in links)),
              "independent_work_families": len({r["identity"]["work_family_id"] for r in links}),
              "skipped": dict(skipped), "errors": errors,
              "production_enabled": False, "training_eligible": False,
              "note": "Candidate links only; no textbook section or musical interpretation certified."}
    for name, rows in (("concepts.json", concepts()), ("report.json", report)):
        (output / name).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "case-links.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in links), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.episodes, args.output), ensure_ascii=False, indent=2))
