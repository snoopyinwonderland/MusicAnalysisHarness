# Multi-segment source-attribution fixtures

4 newly authored synthetic references and 24 uploads. Not infringement findings.

Only uploads/*.musicxml are detector input. evaluator/ contains hidden source mappings, expected phrase family/occurrence counts and transformation recipes; never pass it to search. sources/ may be indexed in an isolated fixture database, never add uploads to the production corpus. Baseline files intentionally preserve source bytes.

Each upload has an event snapshot. manifest.json lists hashes and all rendered SVG pages. XML round-trip audit is separate. No actual search or legal risk calibration has been performed.
