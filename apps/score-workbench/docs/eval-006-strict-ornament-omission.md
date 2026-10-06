# EVAL-006 — 반복음 Query의 엄격한 단일 장식음 누락

## 문제

`SH05-L12-ornament-delete`는 12음 원형에서 짧은 약박 음 하나를 빼 11음으로 만든 Query다. 기대 작품은 후보와 정렬까지 도달했으나 반복음이 많아 적용되는 엄격 하한에서 equality 85.45, meter 10.91로 제외됐다. 음 하나를 제거하며 뒤 onset이 0.25박 당겨졌기 때문에 단순 박자 점수만으로는 실제 관계를 설명하기 어렵다.

전역 meter/equality threshold를 내리면 반복음이 많은 일반 오탐도 함께 늘어난다. 따라서 threshold가 아니라 ‘정확히 무엇이 생략되었는가’를 별도 가설로 증명한다.

## 제한 규칙

저정보량 Query에서 다음 조건을 모두 만족할 때만 단일 누락 예외를 허용한다.

1. Query 실제 음이 10개 이상이다.
2. 후보가 Query보다 attack 하나 더 많다.
3. 빠진 후보 attack은 첫음·끝음이 아닌 내부의 실제 비중첩 attack이다.
4. 유지된 모든 음높이는 하나의 전역 조옮김으로 일치한다.
5. 유지된 모든 음가는 하나의 전역 템포 비율로 일치한다.
6. 유지된 음 사이 도착 간격은 빠진 attack 시간을 제외했을 때 모두 일치한다.
7. 두 음 이상 누락, 추가 substitution, cue/겹친 음, 유지 음의 음가 변경은 허용하지 않는다.

검증된 omission path는 fuzzy local alignment보다 우선한다. 이는 점수를 무조건 올리는 규칙이 아니라 실제 삽입 위치를 보존하는 규칙이다. 누락 비용이 남고 alignment에 insertion 한 개가 표시되므로 Exact로 분류되지 않는다.

## 실제 결과

| 사례 | 변경 전 | 변경 후 |
|---|---|---|
| SH05 `2 Become 1` | 후보 평가 후 low-information-floors, 미회수 | 3위 Similar 96.45, 37마디, 삽입 1 |
| SH09 `WAY BACK THEN` | 후보 평가 후 low-information-floors, 미회수 | 작품 1위 Similar, 삽입 1 |
| DM03 시간축소 | low-information-floors, 미회수 | 1위 Similar 95.35 |
| DM03 시간유지 | 2위 | 1–2위 유지, Similar 97 |
| DM04 시간축소 | admission-floor, 미회수 | 1위 Similar 97 |
| DM04 시간유지 | admission-floor, 미회수 | 1위 Similar 97 |

SH09의 기대 stream과 같은 source 안에 동일 signature를 가진 다른 stream이 더 높은 대표 점수로 선택됐다. 작품은 1위로 회수되며 해당 source의 stream들은 part occurrence로 결합된다. 이는 EVAL-004의 대표 위치/표시 문제와 구분한다.

## 검증과 제한

- 관련 `search-api`, `single-omission`, `single-omission-seeds` 테스트 96/96 통과.
- 전체 테스트 492/494 통과. 남은 두 실패는 이번 서버 변경과 무관한 `FullScorePage` Motif 범위 기대값이다.
- TypeScript 및 production build 통과.
- 6→5와 8→7처럼 변화 비율이 큰 짧은 저정보량 Query에는 이 예외를 적용하지 않는다.
- 이 규칙은 작품 ID, 제목, 마디 번호, 박자 종류를 참조하지 않는다.
