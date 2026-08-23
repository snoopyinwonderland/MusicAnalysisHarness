# Annotation Extension Specification v0.1

## 1. Purpose

Annotation records preserve review history without contaminating Canonical Core or erasing AI uncertainty. Parsing and deterministic representation MUST work when no annotations exist.

## 2. Record model

An annotation targets a stable entity or span and identifies an annotation type. It MAY reference the Analysis Record that prompted review. AI suggestion and human judgment are separate objects.

Human lifecycle states are:

- `unreviewed`: no human decision
- `accepted`: the reviewer accepts a stated AI hypothesis
- `corrected`: the reviewer supplies a replacement or refinement
- `rejected`: the reviewer rejects the claim without asserting a replacement
- `ambiguous`: multiple interpretations remain defensible
- `needs_review`: insufficient context or expertise

Human fields MAY be null. A human decision MUST record annotator identity or pseudonymous ID, timestamp, annotation version, confidence where supplied, and optional comment.

## 3. Alternatives and ambiguity

Corrections SHOULD store a primary label and MAY store alternatives with confidence or rank. An ambiguous decision MUST NOT be silently collapsed into one gold label. Reviewer disagreement is represented as multiple immutable reviews plus an optional adjudication record.

## 4. Revision and audit

Annotation revisions are append-only. `supersedes_annotation_id` links a correction to an older record. Deletion is reserved for legal/privacy removal; ordinary mistakes are superseded. The system SHOULD retain source analysis ID, engine version, UI version, and target resolution status.

## 5. Training eligibility

`training_eligible` is explicit and defaults to false. Eligibility requires a resolvable target, approved annotation type, sufficient reviewer status, provenance, and dataset policy. Acceptance of an AI suggestion is not automatically equivalent to independent gold annotation. Dataset exports MUST record annotation IDs and selection policy.

## 6. Target migration

After reparsing an edited source, the migration service attempts exact stable-ID match, then source-locator match, then structural/content alignment. Outcomes are `exact`, `mapped`, `ambiguous`, or `orphaned`. Ambiguous and orphaned targets MUST be excluded from automatic training exports until reviewed.

## 7. Knowledge pipeline

The intended flow is Canonical IR → AI hypotheses/evidence → UI review → immutable annotation → optional adjudication → case library/training dataset. Case records and dataset manifests remain separate physical and logical schemas.

