# Classical harmony corpora: local format audit (2026-09-24)

Developer handoff and implementation gates: [Harmony, structure, composition and arrangement implementation plan](HARMONY_COMPOSITION_HARNESS_IMPLEMENTATION_PLAN.md). This audit provides evidence, not an implementation-completion claim.

Scope: read-only inspection of `K:/MusicSearch/data/classical-corpora`, its 2026-09-23 inventory, and representative data/README files. File counts below are inventory extension counts, not verified distinct works, matched pairs, or human-validated labels. No corpus-wide alignment or licence audit was completed.

## Finding

The folder can support a harmony harness now, but the data are not one homogeneous training set. Begin with matched score and reviewed harmony annotations in DCMLab. Use When in Rome as a RomanText adapter and cross-source test set; use TAVERN for phrase-level functional patterns. Treat ChoCo as a provenance-rich aggregation and retrieval resource, not 106,810 independent gold examples. YCACL is observed pitch slices plus estimated local key, not human Roman/cadence labels.

## Inventory and intended role

| Corpus | Observed local files / sample | Best first use | Main conversion/quality concern |
| --- | --- | --- | --- |
| DCMLab | 17 subcorpora; 816 `.musicxml`, 816 `.mxl`, 4,532 TSV across tables; Beethoven `01-1` has matching score, measure and harmony TSV | Primary score-linked Roman, local key, cadence/phrase-end evaluation | `mc` vs `mn`, pickup `mn=0`, fractional onsets, repeats/unfolded variants; optional/missing fields; edition matching |
| When in Rome | 765 `.musicxml`, 921 `.rntxt` overall; K576/1 has score, human-derived `analysis.txt`, `analysis_automatic.rntxt`, and working DCML TSV | RomanText adapter, independent evaluation only after source-family split | Human vs automatic analyses, m0/beat fractions, variable score alignment, DCML overlap |
| TAVERN | 5,484 `.krn`; joined example has `**function`, `**harm`, `**kern` side by side | Phrase-scale function, motif/phrase repetition and annotator agreement | Per-phrase Humdrum spines, A/B variants, forced phrase model; not eventwise Roman gold |
| ChoCo | 106,810 `.jams`, 7,914 `.mxl`; sample score JAMS has `chord_roman`, `key_mode`, `timesig`, provenance | Broad label vocabulary, retrieval, domain transfer | Count includes partitions/stages; overlap with DCML/WiR; score vs audio time units; not all JAMS have note-level score match; confidence 1.0 in sample is not calibrated model confidence |
| YCACL | 8,672 CSV; sample rows offset, chord pitch list, `LocalTonic`, `LocalMode` | Vertical-slice/key evidence and unsupervised prior | No Roman numeral or cadence label, confidence removed, standalone score unavailable in this folder |
| Beethoven-symphonies/Hauptstimme | 96 `.musicxml`, full/`_melody` MXL, 332 CSV | Melody extraction and full-score vs melody comparison | Main objective is melody/Hauptstimme; CSV annotation semantics must be checked before calling harmony labels |
| OpenScore Lieder | 1,462 `.musicxml`, 1,156 `.rntxt` (including automatic analyses) | Voice/bass and score parsing; selective harmony adapter | Automatic files must not become human gold; overlap with When in Rome/ChoCo |
| OpenScore Quartets | 196 `.musicxml` | Voice-leading and orchestration evidence | No broad reviewed harmony labels observed in inventory |
| kernscores, musedata, Mutopia, Josquin | 567/255 MusicXML for first two, LilyPond or Humdrum for others | Score parsing, bass/texture, negative cases | Mostly scores rather than paired human harmony labels; format conversion |
| Taking Form | 120 CSV | Large-scale form and phrase hierarchy | Form boundary labels are not chord/cadence labels; score links need validation |
| ASAP | 235 MusicXML, 1,302 MIDI and alignment texts | Performance/score timing after symbolic harness | No direct harmony gold; performance time not symbolic quarter time |

## Concrete sample checks

- DCML Beethoven `harmonies/01-1.harmonies.tsv` has `quarterbeats`, `duration_qb`, `mc`, `mn`, `mc_onset`, `mn_onset`, `globalkey`, `localkey`, `label`, `numeral`, `cadence`, `phraseend`. In the sample, `mn=0` is a pickup whereas sequential `mc=1`; `measures/01-1.measures.tsv` gives the map and changing meter/pickup information. Rows include `V|HC` and `I|PAC`. Use the existing `quarterbeats` with measure validation, then rationalize into Canonical IR half-open spans. Do not infer `mn=mc`.
- When in Rome Mozart K576/1: `analysis.txt` credits DCML people; `analysis_automatic.rntxt` credits AugmentedNet. Both use `m... b...` positions and Roman labels, but are different annotation sources. A source-specific status field is mandatory.
- ChoCo Mozart Sonata JAMS sample: `sandbox.type=score`, `chord_roman` 502 observations, `key_mode` 5. The first Roman observation is `C:I` at JAMS time `1.1` duration `4.0`; retain native coordinate kind and use a score-specific adapter to map it. `annotation_metadata.data_source=expert_human` in this sample; verify per annotation, not just per corpus.
- YCACL Abel CSV sample: `0,G4 E-5 G3 E-4 E-3,?,?`. This is a sounding pitch set with unknown local key, not an interpreted chord progression. The README explicitly says confidence was removed.
- TAVERN joined Humdrum sample has synchronous function, Roman and score spines. Its README says phrases may have been forced into a phrase model, so use annotator alternatives rather than declare a unique answer.

## Harness architecture

1. **Registry and provenance.** One manifest entry per source score/analysis pair: corpus, subcorpus, work/movement, edition, source paths and hashes, annotator, human/automatic status, licence, dependency lineage, native time unit, parsed coordinate version. Deduplicate by work/movement/edition **and** upstream annotation lineage before train/test split; ChoCo copies are not independent from DCML or WiR originals.
2. **Source-specific adapters.** Start with DCML `measures+notes+harmonies`, then WiR RomanText, TAVERN Humdrum, ChoCo JAMS, YCACL slice reader. Keep raw label and native coordinate alongside parsed candidate. Reject unaligned score versions rather than silently join by title.
3. **Canonical alignment.** MusicXML/Humdrum score to Canonical Core; map annotation starts to stable `[global_quarter_start, global_quarter_end)` rational spans and note/sounding-event refs. Validate pickup, meter change, alternate endings/repeats, transposition, chord onset vs sounding notes, note/measure coverage, and duration/type inconsistencies. For a repeated passage, record whether annotation time is written score order or unfolded performance order.
4. **Separate labels.** Observed sonority/active pitch set is derived evidence. Surface chord, Roman numeral, local key, governing harmony, cadence, phraseend and form are separate versioned Analysis/Annotation records. Preserve raw Roman syntax, parsed key/degree/quality/inversion/applied target, label ambiguity, provenance, and reviewer status; keep `unknown` and abstention.
5. **Boundary-focused analyzer.** For each proposed phrase boundary, inspect a configurable before/after window, derive attacks and active sonorities from all parts, make surface-chord candidates, then compare preparation, terminal arrival and immediate after-boundary harmony. Phrase predictions cannot certify cadence and cadence cannot unilaterally force phrase boundaries. Use DCML cadence/phraseend as initial evaluation; TAVERN supplies function-pattern cases. This follows `BOUNDARY_HARMONY_CADENCE_SPEC_v0.1.md`.
6. **Evaluation and review.** Hold out by work/family/source lineage; measure score-to-annotation alignment success and coverage first. Then report chord-root/quality, Roman with key context, local-key, cadence class and boundary-window recall separately. Inspect errors in the score UI with evidence, alternatives and original annotation; store corrections as separate reviewer records. Do not treat unlabeled beats as negative harmony or automatically generated analysis as human gold.

## Pilot acceptance gates

- DCML pilot: 10 to 20 score/TSV pairs covering pickups, 6/8, key/meter change, cadence and phraseend. Report number aligned, time errors, label parser coverage, missing data and duplicates.
- Confirm at least one source-family holdout to expose DCML/WiR/ChoCo leakage.
- Compare prediction to both raw harmony span and boundary-window cadence target; report abstentions.
- Only then broaden to all 17 DCML subcorpora and WiR/TAVERN adapters. YCACL can inform vertical evidence, not Roman supervision.

## Cadence data for Phrase boundaries

Cadence labels can provide direct evidence for a nearby Phrase ending, especially when the melodic arrival, bass/harmonic support and subsequent restart agree. They cannot be used as a one-to-one boundary label. In DCML Beethoven `01-1.harmonies.tsv`, 241 rows include 20 nonempty `cadence` entries and 25 nonempty `phraseend` entries; only 13 share the exact TSV row. This row count is an audit observation, **not** the percentage of cadences coinciding with phrases: `phraseend` includes phrase-opening `{` as well as structural-ending `}` and interlocking `}{`. DCML defines full phrase extent from an opening `{` to the next opening `{`; `}` marks the structural arrival, after which codetta/transition material may still belong to that Phrase. Cadence labels mark the ultima, occasionally at its resolution after the structural arrival. Alternative endings/repeats also alter coordinates. Source: https://dcmlab.github.io/standards/build/html/reference/reference.html

For a pilot, align `cadence`, `{`, `}` and `}{` separately to quarter positions and evaluate the cadence arrival, structural ending, and next Phrase onset as distinct targets in a meter-relative window. Preserve `PAC`, `IAC`, `HC`, `DC`, `EC`, `PC` as distinct candidates and store the analyst's marks independently. A trained/evaluated cadence module may raise a proposed structural-ending or ensuing boundary's evidence only when its own features are derived from score events, with an explicit dependency edge. It must not use the same Phrase prediction as an input, and it must not count bass, vertical slice, and derived Roman label as three independent observations. Compare boundary-only baseline to boundary-plus-cadence on **held-out works/source families**, counting gains, false splits, missed phrases and abstentions. For repeated motifs and long notes, inspect the exact onset or release point rather than assigning every chord change a Phrase end.

## Additional format inventory — 2026-09-24

The earlier inventory covered 14 corpus directories. Four newly observed directories are listed separately here; extension counts are files, not distinct works or validated annotations.

| Corpus | Local observed files | Relevant use and format boundary |
| --- | --- | --- |
| DilemmaData | 329 `.mxl`, 24 `.musicxml`, 2,344 `.tsv`, 24 `.krn` | README describes processed AugmentedNet/Distant Listening data and pitch arrays for multiple analysis tasks. Inspect task labels and lineage before assigning harmony-gold status; MXL is compressed MusicXML. |
| Freischütz Digital | 182 `.xml` | README identifies the XML as MEI, with variants and a project-specific core model. Extension `.xml` alone does not establish MusicXML semantics. |
| Korean court music, Sejong | 279 `.musicxml`, 187 `.txt`, other code/metadata | Notation and generation research; Western common-practice harmony labels are not implied by score availability. |
| Wagner leitmotifs | 187 `.csv` | README describes leitmotif classification in opera recordings. Inspect time units and score alignment before treating CSV as score-event annotation. |

The local Music Analysis/MusicXML directory currently has 8,362 `.xml` files totalling about 4,382 MB. Seven size-quantile samples were compressed in memory with raw DEFLATE, without writing or altering source files: compressed payloads were about 3–9% of their original byte sizes (the median-size sample was 493 KiB → 19 KiB). This is an exploratory payload measurement, not a valid `.mxl` package or a whole-corpus storage/runtime benchmark. An actual MXL package requires the MusicXML ZIP container and `META-INF/container.xml` as specified by [MusicXML 4.0](https://www.w3.org/2021/06/musicxml40/tutorial/compressed-mxl-files/).

The MusicSearch search SQLite (`data/search-index-v2/search.sqlite`, observed size 28,887,072,768 bytes) has a `works` table storing source paths and `notes` JSON. `server/search-api.mjs` reads MusicXML separately through `sourceXml()` with an XML cache. Its `.mxl` branch resolves a pre-existing PDMX `.xml` sidecar, not a generic MXL reader. Compressing source MusicXML therefore would reduce source-file storage if deliberately deployed but would not proportionally shrink this search DB or guarantee faster score loading. MIDI remains a performance format; converting it to notated MusicXML requires inferred notation and must preserve both originals and conversion provenance.

## Rights note

Local READMEs show at least DCML Beethoven CC BY-NC-SA 4.0 and When in Rome CC BY-SA 4.0. YCACL README does not specify a new restriction and notes its upstream context. Usage or redistribution needs a per-subcorpus rights inventory before any shared training artifact or public dataset is published.
