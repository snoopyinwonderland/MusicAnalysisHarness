# ID and Time Coordinate Specification

## 1. Recommended hybrid ID strategy

단일 전략은 충분하지 않다.

| 전략 | 장점 | 문제 |
|---|---|---|
| path-based | 결정론적·설명 가능 | 앞부분 삽입 시 뒤 ID 연쇄 변경 |
| source hash + location | exact source 재현 | 사소한 수정에도 전체 namespace 변경 |
| content hash | 위치 이동에 강함 | 반복되는 동일 음을 구분하기 어려움 |
| UUID + mapping table | 영속성 | 최초 mapping DB가 필수, 재생성 불가 |
| hybrid | 재현성과 migration 균형 | 구현이 복잡함 |

권고:

1. `source_file_id = src_` + normalized source bytes SHA-256 prefix.
2. `score_id`는 work identity가 확인되면 registry UUID, 없으면 source-file-derived provisional ID.
3. Part/Staff/Voice/Measure/Event ID는 score namespace + canonical structural locator + local occurrence discriminator로 생성.
4. 각 event는 별도 `event_fingerprint`(pitch, rational onset/duration, lane, local neighbors)를 갖는다.
5. source 수정 후 migration은 old/new fingerprint alignment로 `id_mapping.jsonl`을 만든다.
6. high-value annotation이 존재하는 score는 registry UUID와 mapping table을 필수화한다.

ID 예:

```text
src_f84c...
score_2d71...
part_01f3...
staff_a821...
voice_b917...
measure_5de2...
note_3a60...
rest_072c...
tie_884f...
sound_14cc...
attack_09bd...
span_61a2...
```

Array index, display title, printed measure number만으로 ID를 만들지 않는다.

## 2. Source edit behavior

- byte-identical reparse: 모든 ID 동일.
- metadata-only edit: source_file_id는 변경되지만 structural IDs는 registry score namespace가 있으면 유지 가능.
- note edit: 해당 event ID는 새로 만들고 mapping은 `modified` 관계를 기록.
- 앞부분 삽입: sequential index가 바뀌어도 fingerprint alignment로 뒤 event ID를 보존하도록 migration을 시도.
- ambiguous repeated passages: 자동 mapping을 확정하지 않고 candidate mappings와 confidence를 출력해 사람 검토.

## 3. Rational time

```json
{"numerator":1,"denominator":3}
```

- denominator > 0
- gcd로 약분
- 0은 `0/1`
- internal arithmetic에 IEEE float 금지
- serialization에서 decimal mirror를 둘 수 있으나 authoritative가 아님

## 4. Coordinate types

- `printed_measure_number`: UI/source label, string
- `sequential_measure_index`: part 안 0-based canonical order
- `beat`: notated meter에 따른 1-based rational display coordinate
- `onset_in_measure`: measure start 기준 quarter rational
- `global_quarter`: notated timeline score origin 기준 rational
- `normalized_measure_position`: derived rational in `[0,1]`

## 5. Span rule

모든 span은 `[start,end)`이고 `end >= start`다. Zero-length point annotation은 `PointReference` 또는 `start=end`와 명시적 `target_kind=point`로 표현한다. UI display coordinate는 authoritative global coordinate와 일치해야 한다.

```json
{
  "start":{"numerator":12,"denominator":1},
  "end":{"numerator":16,"denominator":1},
  "display":{"start_measure_id":"measure_004","start_beat":{"numerator":1,"denominator":1},"end_measure_id":"measure_005","end_beat":{"numerator":1,"denominator":1}}
}
```

## 6. Notated vs playback timeline

Core event onset은 notated timeline이다. Repeat, ending, D.C./D.S., coda를 펼친 순서는 `PlaybackOccurrence` mapping으로 표현한다. 하나의 Core note가 여러 playback occurrence를 가질 수 있으며 Core note ID를 복제하지 않는다.

