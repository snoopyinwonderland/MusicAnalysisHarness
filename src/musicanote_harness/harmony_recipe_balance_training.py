"""Reopen the same approved Train contrasts, including unknown recipe shapes.

The parent JSON containers include historical Dev rows, but only approved Train
rows enter recomputation, loss or fit. No claim of never-exposed blind data.
"""
from pathlib import Path
from . import harmony_support_balance_training as prior
from . import harmony_support_balance_learning as old_learning
from . import harmony_recipe_balance as scoring
from . import harmony_recipe_balance_learning as learning
from .harmony_structured_learning import content_hash, validate_use_contract

PINS = prior.PINS
PARENT_SHA = prior.PARENT_SHA
SUPPORT_MODEL = "output/harmony-support-balance-2026-10-05-r2/model.json"
SUPPORT_MODEL_SHA = "de9fe82781d107d443999b2c3f1e769f002d2077e0e8c20aa0b6bb796ddca896"


def contrast_row(item, entry, graph, ev, args, fixed, cells):
    base = scoring.support.Scorer(graph, ev, fixed, build_index=False, **args)
    checked = prior.contrast_row(item, entry, graph, ev, args, base, cells)
    def value(ids):
        return sum((scoring.recipe_feature(graph, a, b, sig)
                    for a, b, sig in scoring.support.completed_runs(graph, ids)), scoring.F())
    negative, target = value(item["negative_ids"]), value(item["target_ids"])
    return item | {"entry": entry, "feature_delta": {scoring.FEATURE: scoring.support.q(negative-target)},
        "feature_available": {scoring.FEATURE: True}, "loss": checked["loss"],
        "negative_features": {scoring.FEATURE: scoring.support.q(negative)},
        "target_features": {scoring.FEATURE: scoring.support.q(target)},
        "frozen_support_feature_availability": checked["feature_available"],
        "base_cost_gap": scoring.support.q(base.score_path(item["negative_ids"])-base.score_path(item["target_ids"])),
        "base_score": "step67_frozen_train_calibrated_with_nullable_support_observations"}


def prepare(read, save, output):
    previous, recall, integration, contract, historical_model, learned = [read(p, h) for p, h in PINS.items()]
    if content_hash(historical_model) != learned["model_content_sha256"]:
        raise ValueError("historical_model_binding_changed")
    manifest = recall["package_manifest"]
    approvals = validate_use_contract(contract, manifest, PARENT_SHA)
    for approval in approvals.values():
        lic = approval["source_license"]
        for name in ("local_license", "readme"):
            read(lic[name+"_path"], lic[name+"_sha256"], raw=True)
    fixed_model = read(SUPPORT_MODEL, SUPPORT_MODEL_SHA)
    fixed = old_learning.model_weights(fixed_model, contract, manifest, PARENT_SHA)
    groups, counts = prior.contrasts(historical_model)
    refs = {r["sample_id"]: r for r in learned["records"]}
    prev = {r["sample_id"]: r for r in previous["records"]}
    if len(refs) != len(learned["records"]) or len(prev) != len(previous["records"]):
        raise ValueError("duplicate_training_scope")
    rows, eligibility, sources = [], [], set()
    for sample, items in sorted(groups.items()):
        ref = refs[sample]
        entry, graph, ev, clock, args = prior.prepare_context(prev[sample], ref, manifest, integration, read)
        if entry["manifest_entry_id"] not in approvals:
            raise ValueError("unapproved_historical_train_context")
        gate = clock.scope(ref["sample_span"])
        sources.add(ev.source.source_ir_content_sha256)
        receipt = {"sample_id": sample, "pair_id": ref["pair_id"], "sample_span": ref["sample_span"],
            "work_family_id": entry["work_family_id"], "source_clock_gate": gate,
            "source_ir_content_sha256": ev.source.source_ir_content_sha256,
            "candidate_inventory_content_sha256": ref["candidate_inventory_content_sha256"],
            "contrasts": len(items), "eligible_contrasts": 0}
        if gate["accepted"]:
            cells = tuple(prior.old.cells_from_record(ref))
            for item in items.values():
                rows.append(contrast_row(item, entry, graph, ev, args, fixed, cells) | {"sample_id": sample})
                receipt["eligible_contrasts"] += 1
        clock.check_source()
        eligibility.append(receipt)
        print(f"[Train recipe {len(eligibility)}/{len(groups)}] {sample}: {receipt['eligible_contrasts']}/{len(items)}", flush=True)
    counts.update(unique_historical_contrasts=sum(map(len, groups.values())), historical_samples=len(groups),
        eligible_contrasts=len(rows), eligible_samples=len({r["sample_id"] for r in rows}), full_source_packages=len(sources),
        legacy_unavailable_contrasts=sum(not all(r["frozen_support_feature_availability"].values()) for r in rows))
    dataset = {"rows": rows, "eligibility": eligibility, "counts": counts,
        "frozen_support_model_sha256": SUPPORT_MODEL_SHA, "historical_negative_pool_complete": False,
        "fresh_adversary_search": False, "dev_labels_used": False, "candidate_policy_changed": False}
    save(output/"training-contrasts.json.gz", dataset, True)
    model = learning.fit(rows, contract, manifest, PARENT_SHA)
    model["training_dataset_content_sha256"] = content_hash(dataset)
    model["frozen_support_model_sha256"] = SUPPORT_MODEL_SHA
    model["negative_pool"] = "deduplicated_sealed_J2f_updates_and_collisions_including_unknown_shapes"
    save(output/"model.json", model)
    return model, contract, manifest, dataset, fixed
