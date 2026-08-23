# Entity Reference

## Score

필수: `score_id`, `source_file_id`, `title`, `part_ids`, `measure_ids`, `duration_quarters`, `metadata`. `composer`, `movement`, `pickup_measure_id`는 nullable이다. `measure_count`는 sequential measures의 수다.

## Part

`part_id`, `score_id`, `source_part_id`, `instrument_name`, `instrument_family`, `transposition`, `staff_ids`, `voice_ids`, optional MIDI program을 갖는다. Transposition은 diatonic/chromatic/octave change를 구조화한다.

## Staff

`staff_id`, `part_id`, `staff_number`, `clef_timeline`, `voice_ids`. Staff number는 source display coordinate이고 global unique identity가 아니다.

## Voice

`voice_id`, `part_id`, `source_voice_number`, `event_ids`, `default_staff_id`. Cross-staff event는 같은 `voice_id`를 유지하고 event의 `display_staff_id`만 바뀐다. source가 voice를 제공하지 않으면 generated voice와 generation policy/evidence를 기록한다.

## Measure

`measure_id`, `part_id`, `printed_measure_number`, `sequential_measure_index`, `global_start_quarter`, nominal/actual duration, time/key signature observation, pickup/implicit flag, repeat/barline metadata. Printed number는 중복·문자 suffix를 허용한다.

## NotatedNoteEvent

필수: note/score/part/staff/voice/measure ID, source ref, onset in measure, global onset, notated duration, written pitch, tie flags, grace flag, chord member metadata. Slur, lyric, articulation, beam, stem은 optional observation이다.

`logical_voice_id`와 `display_staff_id`를 분리하여 cross-staff를 표현한다. Note는 analysis label을 갖지 않는다.

## RestEvent

Note와 같은 timeline/source contract를 사용하되 pitch가 없다. Printed, hidden, spacer, cue 목적을 구분한다.

## TieChain

`tie_chain_id`, ordered `source_note_ids`, written/concert pitch, start, end, total duration, status를 갖는다. Notated notes는 삭제하지 않는다. Repeat jump 때문에 notated timeline에서 미해결이면 warning과 resolution context를 남긴다.

## SoundingEvent

`sounding_event_id`, ordered source note IDs, pitch, onset, release, duration, attack note ID, tie chain ID를 갖는다. 하나의 attack이 여러 notated segments로 이어질 수 있다.

## AttackEvent

`attack_event_id`, `sounding_event_id`, `note_id`, onset, velocity/source attack markings를 갖는다. Tie continuation은 AttackEvent를 만들지 않는다. Grace attack은 ordering 정보를 보존한다.

## ChordOnsetGroup

`chord_onset_group_id`, onset, note IDs, source formation(`musicxml_chord` 또는 deterministic simultaneous group)을 갖는다. 분석적 chord/roman/function field는 금지한다.

## Direction records

Tempo, Dynamic, Clef, KeySignature, TimeSignature, Slur, Articulation, Lyric, Repeat/Barline은 독립 record 또는 event reference로 저장할 수 있다. 값이 없는 경우 추론하지 않는다.

## DeterministicEvidence

`evidence_id`, algorithm/version/config hash, target refs, value와 units를 갖는다. 권장 feature: pitch class, melodic interval/contour, metric position/strength, simultaneous pitch classes, density, register, duration ratio, attack density, overlap, lowest/top pitch, chromatic flag relative to notated key signature.

## Derived VerticalSlice

`slice_id`, `[start,end)`, active sounding event IDs, attacked note IDs, released IDs, pitch classes, lowest/top pitch, count. 기본 정책은 재계산 가능한 cache다. 영구 저장 시 algorithm version과 input IR hash가 필수다.

## SpanReference

`start`, `end`, optional display start/end, optional event refs. Span identity가 필요하면 external registry에서 `span_id`를 부여한다. Core는 특정 분석 taxonomy를 알지 않는다.

