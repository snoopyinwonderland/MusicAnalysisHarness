# Analysis and Evidence Interface Specification v0.1

## 1. Boundary

Canonical Music IR supplies stable score facts, deterministic evidence, IDs, and time coordinates. Harmony, NCT, phrase, cadence, motif, local key, modulation, form, melody, similarity, copyright, arrangement, and evaluation outputs are external records. An analyzer MUST NOT mutate Canonical Core to publish a conclusion.

## 2. Common analysis record

Every record identifies the score, target, hypotheses, evidence, engine, and lifecycle status. A target MAY be an entity, a list of entities, or a half-open span. When a claim concerns time, the span is authoritative; display measure/beat coordinates are a convenience projection.

Required concepts:

- `analysis_id`, `analysis_type`, `score_id`, `target`
- one or more `hypotheses`, including alternatives and confidence
- `selected_hypothesis`, which MAY be null when the engine abstains
- `evidence_refs`
- immutable `engine` provenance: name, version, configuration hash
- `status`: `candidate`, `selected`, `validated`, `rejected`, or `abstained`

`selected` means selected by a particular engine or workflow, not human-verified truth. Human review is represented by an Annotation Record.

## 3. Target contract

Targets use one or more of:

```json
{
  "entity_refs": ["note_sc01_n_000042"],
  "span": {
    "start": {"numerator": 12, "denominator": 1},
    "end": {"numerator": 16, "denominator": 1}
  }
}
```

All ranges are `[start, end)`. Empty spans are disallowed for ordinary analysis claims. Point observations use `entity_refs` or an explicitly typed point target.

## 4. Hypotheses and uncertainty

A hypothesis contains a machine-readable `label`, optional structured `parameters`, confidence in `[0,1]`, and optional rationale. Confidence semantics MUST be documented per analyzer and MUST NOT be compared across engines unless calibrated. Competing interpretations are retained. Re-running an analyzer creates a new record or run; it does not overwrite the old record.

## 5. Evidence records

Evidence is a traceable support or counter-signal, not an interpretation promoted to Core. Evidence types include note, interval, metric, vertical, phrase, cadence, key, retrieved-case, and rule evidence.

Evidence records contain:

- `evidence_id`, `evidence_type`, `score_id`
- `source_refs` back to Core or other evidence
- optional target span
- `relation` and typed `value`
- producer/version provenance
- optional graph edges with `supports`, `contradicts`, `derived_from`, or `corroborates`

An Evidence Graph is formed by IDs and edges. Cycles are permitted only for explicitly declared non-derivation relations; `derived_from` MUST remain acyclic.

## 6. Deterministic evidence versus analyzer evidence

Deterministic features such as pitch class, active pitch set, metric position, or lowest sounding pitch MAY be generated as a cache beside the IR. They MUST include algorithm/version information and be reproducible from the referenced IR. Labels such as `passing_tone`, `V7/V`, `half_cadence`, and `structural_bass` are analysis hypotheses even when produced by rules.

Vertical slices are recommended as a deterministic derived cache, not mandatory persisted Core. Cache keys SHOULD include IR document hash, slice algorithm version, and parameters.

## 7. Analyzer run manifest

Each batch/run SHOULD store `run_id`, input IR document hashes, analyzer versions, configuration hashes, random seed when applicable, timestamps, and output record IDs. Runtime working memory belongs in `analysis_state.json`; it is neither Core nor durable truth.

## 8. Compatibility

Analyzers MUST declare the supported Canonical IR version range. Unknown optional Core fields MUST be ignored safely. Unsupported major versions MUST fail explicitly. Evidence and analysis schemas evolve independently but reference stable Canonical IDs.

