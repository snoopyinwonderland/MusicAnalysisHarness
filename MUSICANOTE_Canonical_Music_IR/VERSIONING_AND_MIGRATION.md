# Versioning and Migration

## 1. Schema identity

Canonical documents declare:

```json
{
  "schema_name": "musicanote-canonical-music-ir",
  "schema_version": "0.1.0"
}
```

Semantic Versioning is used:

- PATCH: compatible clarification or validator bug fix with unchanged document meaning
- MINOR: backward-compatible optional field/entity addition
- MAJOR: incompatible field removal, type change, or semantic change

The meaning of an existing Core field MUST NOT change in place. Deprecated fields remain readable for at least one supported major-version migration window.

## 2. Producer and policy versions

Schema version, parser version, normalization-policy version, derived-feature version, and analyzer version are independent. A parser bug fix that changes emitted events requires a parser/policy version change and a migration note even if the JSON Schema version is unchanged.

## 3. Extensions

Extensions are registered objects, not arbitrary ungoverned JSON. Each extension declares `name`, semantic `version`, `owner`, `schema_uri`, and `payload`. Names use a reverse-domain or MUSICANOTE-controlled namespace. An extension MUST NOT redefine Core semantics or shadow Core fields. Consumers ignore unknown optional extensions but preserve them during lossless document transport when possible.

## 4. Migration artifacts

Every breaking migration provides:

1. source and target version range;
2. deterministic migration program;
3. field mapping and loss report;
4. ID preservation report;
5. regression fixtures;
6. annotation target reconciliation report.

Migrations generate a new `ir_document_id` while retaining the same `score_id` only when work/source identity policy says the musical source is unchanged. Original documents remain immutable.

## 5. Current prototype transition risk

The existing prototype emits `musicanote-canonical-ir-0.2` and uses structures such as segments, sounding events, and harmonic atoms. The formal schema is named `musicanote-canonical-music-ir` version `0.1.0`; version numbers are not directly comparable. A compatibility adapter is required, not a string-version bump. Particular risks are file-name/size-based score identity, missing source locators, measure-index ambiguity, absent explicit attack/tie-chain/chord-onset entities, and persisted harmonic atoms whose formal status is derived cache.

## 6. Physical storage

The logical schema is independent of storage. JSON is normative for exchange/debugging; JSONL is suitable for record streams; Parquet for analytical event tables; PostgreSQL plus relational keys/JSONB for operations; protobuf or msgpack only with generated compatibility contracts. Storage migrations MUST preserve logical IDs, exact rationals, and source traceability.

