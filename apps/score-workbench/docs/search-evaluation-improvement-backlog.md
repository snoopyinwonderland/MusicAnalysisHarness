# 검색 변형 평가 — 개선안 통합 보류 목록

2026-09-22 현황: 최근 5배치 305회 검토에서 묶은 EVAL-001~008을 일반 규칙 또는 결과 표현 계약으로 모두 반영했다. 사용자 승인으로 별도 추가한 단순 패턴 허용 옵션은 이 8개 해결과 구분한다([정책·검증](simple-pattern-search-options.md)).

2026-09-17 사용자 지시: 변형 테스트를 먼저 이어가며 개선안은 마지막에 모아서 검토·반영한다. 아래 항목은 구현 완료가 아니며, 운영 검색의 점수/후보 생성/정렬/Exact 판정은 이번 평가 중 변경하지 않는다.

| ID | 관찰 및 근거 | 일반화 개선 후보 | 상태 |
|---|---|---|---|
| EVAL-001 | memory-variation-50-v1: 음 끝 쉼표 변형 10개가 Exact 100 | 허용적 IOI 리듬 점수와 엄격한 duration/rest Exact 판정을 분리 | **반영·회귀 통과 (2026-09-19)** |
| EVAL-002 | MEM10-absorb-ornament: 원곡 1위지만 3박 F4→0.5박 동음, 다른 긴 음 누락 | 도착 시각·지속시간·긴 음 coverage로 경쟁 정렬 경로 비교 | **반영·회귀 통과 (2026-09-19)** |
| EVAL-003 | repeat-split 10개: 추가 반복 attack가 unmatched | 같은 높이 2음↔1음의 split/merge 대응을 별도로 설명·표현 | **반영·회귀 통과 (2026-09-22)** |
| EVAL-004 | 대표 반복 위치와 의도한 위치 차이 | 작품 회수·대표 구간·반복 위치 포함을 분리해서 평가 | **평가·API·UI 반영 확인 (2026-09-22)** |
| EVAL-005 | OCT01/02 단일 옥타브 및 OCT01 복합에서 변경 음 미대응, OCT02 복합에서 다른 높이에 대응 | 국소 옥타브 치환과 음 누락의 경쟁 경로를 구분해 진단; octave 허용을 무조건 강화하지 않고 반례와 비교 | **표시 정렬 반영·회귀 통과 (2026-09-22)** |
| EVAL-006 | SH05-L12-ornament-delete: 원곡 후보 존재, melodic 점수는 높지만 equality 85.45 / meter 10.91로 low-information-floors 탈락 | 10음 이상 저정보량 Query도 한 조옮김·템포 아래 유지 음의 높이/음가/도착 간격과 내부 attack 하나 누락을 전부 증명할 때만 제한 통과 | **반영·독립 사례 회귀 통과 (2026-09-22)** |
| EVAL-007 | SH03-L8-pitch-change: 원곡 stream이 hits에는 있지만 candidates에는 없고 정렬 평가도 없음 | 8–12음 Query에서 정확히 한 음만 바뀌고 강한 리듬 증거가 있는 후보를 양끝 interval anchor에서 제한적으로 복구 | **반영·집중 회귀 통과 (2026-09-22)** |
| EVAL-008 | SH02-L6-original: 정확한 137마디 원형 대신 같은 음정·다른 리듬의 131마디를 평가, 반환 100개에서 원본 미회수 | Melody + Rhythm은 리듬까지 정확한 occurrence를 먼저 대표 구간으로 선택하고, 없을 때만 interval 대표 구간으로 하향 | **반영·회귀 통과 (2026-09-22)** |

평가 기준 보충: 변형된 Query의 원곡 1위 유지가 목표는 아니다. 확인 가능한 상위권 회수는 긍정적으로 평가하고, 순위 하락과 실제 정렬·판정 오류를 구분한다.

각 사례의 원형/변형 Query, XML 문맥, 실제 응답, 검토 의견은 export bundle에 둔다. 이 문서는 비교와 우선순위 결정용 목록이며 원본 근거를 대체하지 않는다. 특정 작품/Query만을 위한 production 예외는 추가하지 않는다.

## EVAL-001 반영 증거 — 2026-09-19

- 일반 유사 검색의 rhythm shape/DTW 점수와 후보·순위 논리는 유지하고, 사용자에게 보이는 `Exact` bucket만 별도의 엄격 판정으로 결정한다.
- 엄격 판정은 tie로 묶인 Query 음을 먼저 하나의 logical attack으로 합친 뒤, 실제 음가와 음 사이 silence gap을 분리하여 비교한다. 하나의 공통 템포 배율은 허용하지만 일부 음가만 줄여 쉼표로 바꾸는 국소 재분배는 허용하지 않는다.
- 명시적 선행 쉼표는 후보 직전 음의 끝과 첫 attack 사이를, 명시적 종결 쉼표는 후보 마지막 음의 끝과 다음 attack 사이를 확인한다. 다음 attack이 없어 silence 길이를 입증할 수 없는 경우는 보수적으로 Exact로 분류하지 않는다.
- `memory-variation-50-v1` 고정 10개 원형은 10/10 Exact, 같은 10개 음가→쉼표 변형은 0/10 Exact였다. 실제 DB 대표 사례 MEM01은 원형 1위/Exact 100을 유지했고 변형도 1위를 유지하면서 Similar 97로만 재분류됐다.
- `absoluteExactOnly`의 Melody + Rhythm 경로도 이 엄격 판정을 통과하지 못하면 제외한다. `Exact Rhythm` 상세 옵션의 기존 tolerant filtering 및 일반 유사 순위는 이번 변경 범위에서 바꾸지 않았다.
- 검증: `npm test -- --run server/search-api.test.js` — 74/74 통과.

## EVAL-003 반영 증거 — 2026-09-22

- 검색 점수와 gap은 유지하고 정렬 결과에 `repeat-split`/`repeat-merge` 의미만 추가했다. 같은 높이, 연속 onset, 한 공통 템포 아래 합산 음가가 모두 정확한 경우에만 붙는다.
- 이 관계는 타이나 Exact가 아니다. 기존 `deletion`/`insertion` step을 보존하므로 강조 인덱스와 기존 API도 깨지지 않는다.
- 합성 양방향·음가 반례를 포함한 서버 테스트가 통과했다. repeat-split 실제 사례 10개는 모두 기존 1–4위 범위를 유지한다. 대표 구간에서 지속음↔두 attack이 실제인 8개에는 관계 주석이 붙고, 다른 반복 위치에서 두 attack이 직접 존재한 MEM01·MEM08에는 거짓 관계를 만들지 않았다.
- MEM01·MEM08의 일시적 0건은 EVAL-002 재평가가 낮은 coverage 경로를 고른 문제였으며 similarity 우선·실패 coverage 한정 lookback으로 둘 다 1위 복구했다. 상세 내용은 [EVAL-002 기록](eval-002-held-arrival-alignment.md)과 [EVAL-003 기록](eval-003-repeat-attack-semantics.md)에 둔다.

## EVAL-004 반영 증거 — 2026-09-22

- 평가 보고서는 작품 순위, 대표 구간 겹침, 원래 반복 위치 포함 여부를 각각 `sourceRank`, `representativeWindowRank`, `originalStartInOccurrences`로 저장한다.
- 운영 API는 대표 결과와 별도로 `occurrenceCount`, `occurrenceMeasures`, `partOccurrences`를 반환하고 결과 카드는 반복 횟수·마디·파트를 표시한다.
- `memory-variation-50-v1`의 대표 구간 차이 5개는 모두 작품 회수 성공이며 의도한 원래 시작 마디도 occurrence 목록에 보존됐다. 점수나 대표 구간을 사례별로 고정하지 않았다.
- 상세 계약은 [EVAL-004 기록](eval-004-repeated-occurrence-reporting.md)에 둔다.

## EVAL-005 반영 증거 — 2026-09-22

- 검색 점수와 순위는 이미 양호했으므로 옥타브 유사도를 전역 강화하지 않았다. 최종 표시 경로에서만 조옮김 후 정확한 일반 음, 정확히 한 개의 ±12 residual, 최대 한 개의 실제 길이 차이 gap으로 전체 구간이 설명될 때 재정렬한다.
- OCT01/02 단일 변형은 변경 음이 원래 pitch class 음에 직접 대응하고 gap 0이 됐다. 두 복합 변형은 같은 직접 대응과 실제 omission gap 1개만 남았다. 네 사례 모두 일반 substitution은 0개다.
- 합성 양성·복합·일반 substitution 반례를 포함한 서버 테스트 92/92 통과. 상세는 [EVAL-005 기록](eval-005-local-octave-alignment.md)에 둔다.

## EVAL-007 반영 증거 — 2026-09-22

- 단순히 후보 수를 늘리는 방식은 채택하지 않았다. SH03 원곡은 전체 후보 작품 순위 6,963, 남은 단일 anchor 안에서도 459위여서 작은 일반 reserve로는 회수되지 않았고, 큰 reserve는 약한 후보를 과도하게 늘렸다.
- 8–12음, 저정보량 Query가 아님, Exact 상세 옵션이 아님이라는 조건에서만 양끝 interval anchor를 최대 600작품씩 살핀다. 한 조옮김 아래 정확히 한 음만 달라야 하며 Melody + Rhythm에서는 템포를 정규화한 리듬 형태가 90점 이상이어야 한다.
- 통과 후보는 최대 40개이고 작품당 한 위치만 후보 정밀 평가로 넘긴다. 이 단계는 점수나 Exact 판정을 올리지 않고 이미 존재하는 정밀 정렬·박자·구조·admission 검사를 받을 기회만 복구한다.
- 실제 `SH03-L8-pitch-change` 재실행: 변경 전에는 hits에만 있고 candidates에는 없어 순위 없음, 변경 후 `UN DI, FELICE` 6–9마디가 1위(97점), local 98.62, rhythm 100으로 회수됐다. profiling상 candidate key 2,664, 평가 작품 1,534, cold 실행 약 8.4초였다.
- 집중 서버 테스트 79/79 통과. 전체 테스트는 484/486 통과했고, 남은 2건은 이번 변경 경로와 무관한 `FullScorePage` Motif 범위 기대값 실패다. 상세 설계와 제한은 [EVAL-007 기록](eval-007-single-pitch-retrieval.md)에 둔다.

## EVAL-008 반영 증거 — 2026-09-22

- 한 작품 안에 interval이 같은 반복 구간이 여러 개 있을 때 기존 코드는 Melody + Rhythm에서도 phrase evidence가 높은 interval occurrence를 대표로 선택했다. 별도로 계산한 rhythm-exact occurrence는 Absolute 옵션에서만 사용되고 있었다.
- Melody + Rhythm은 rhythm-exact occurrence가 있으면 그 집합 안에서 phrase evidence로 대표 위치를 정한다. 리듬까지 맞는 곳이 없을 때만 기존 interval occurrence로 내려간다. Melody Only와 명시적 Exact 옵션의 선택 규칙은 유지한다.
- 실제 `SH02-L6-original`: 변경 전 기대 작품 `ANGEL`은 131마디의 다른 리듬만 평가되어 Top 200 밖, 변경 후 137–138마디가 1위 Exact 100점, rhythm/meter/skeleton 100으로 회수됐다.
- 집중 서버 테스트 83/83 통과. 상세 내용은 [EVAL-008 기록](eval-008-rhythm-occurrence-selection.md)에 둔다.

## EVAL-006 반영 증거 — 2026-09-22

- 반복음이 많은 Query의 meter/equality 하한은 전역으로 낮추지 않았다. 대신 기존 단일 누락 검증기를 10음 이상 저정보량 Query에도 실행한다.
- 통과하려면 후보의 내부 실제 attack 정확히 하나만 빠지고, 나머지 전 음이 하나의 조옮김·템포 아래 음높이·음가·도착 간격까지 모두 일치해야 한다. 검증된 누락 정렬은 fuzzy alignment보다 우선하지만 삽입 비용과 Similar 분류를 유지한다.
- `SH05-L12-ornament-delete`: `2 Become 1`이 미회수에서 3위 Similar 96.45, 37마디, 내부 삽입 1개로 회수됐다.
- `SH09-L12-ornament-delete`: `WAY BACK THEN` 작품이 미회수에서 1위 Similar로 회수됐다. 같은 source의 동일 match signature 중 다른 stream이 대표가 되었으며 기대 stream도 검증·통과 후 part occurrence로 결합된다.
- 2/4 독립 사례: DM03 시간축소 1위, 시간유지 1–2위; DM04 두 조건 모두 1위로 회수됐다. 6→5, 8→7음 Query에는 이 저정보량 예외를 적용하지 않는다.
- 관련 3개 테스트 파일 96/96 통과. 전체는 492/494 통과하며 남은 2건은 기존 `FullScorePage` Motif 범위 테스트다. Production build 통과. 상세 내용은 [EVAL-006 기록](eval-006-strict-ornament-omission.md)에 둔다.

## 평가 순서

EVAL-002 반영 증거(2026-09-19, 2026-09-22 보완): Melody + Rhythm의 local alignment에서 각 구간의 대표 음가로 전체 템포 차이를 정규화한 뒤, 긴 Query 음을 매우 짧은 후보 동음에 대응시키면 비용을 부과한다. 삽입·누락 뒤에는 직전 실제 대응 음부터의 도착 간격을 비교한다. 긴 음 누락이 남아 있을 때만 인근 시작점을 제한적으로 재평가한다. 재평가 선택은 coverage가 포함된 similarity 우선이며 동률일 때만 raw cost를 쓴다. 정상 경로는 기존 4개, coverage 75% 미만 실패 경로만 최대 8개 lookback이다. 후보 생성·전역 admission/floor·Exact·최종 순위식은 변경하지 않았다. 고정 합성 회귀에서 원형/전체 템포 x2는 100, 장식음 흡수는 원래 긴 음 2개와 대응하며 77.5, 긴 첫 음을 0.5박 반복으로 대체한 대조는 53.2였다. 실제 MEM10 재검색은 64마디 4.5박의 짧은 동음 시작에서 64마디 1박의 원래 3박 음 시작으로 이동했다. 추가로 MEM01·MEM08은 10/17음 경로 탈락에서 17/17 대응·1위로 복구됐다. 상세는 [EVAL-002 기록](eval-002-held-arrival-alignment.md)에 둔다.

2/4 추가 근거(duple-meter-15-v1): 15회 완료. DM03-L12-ornament-delete는 후보 존재 후 low-information-floors 제외, 같은 원형의 음가 흡수 조건은 2위. DM04의 두 삭제 조건은 후보 존재 후 admission-floor 제외. EVAL-006 및 정렬·통과 조건 진단에 추가하며 2/4 자체의 오류로 단정하지 않는다. 원형 5/5, 삭제 시간 축소 3/5, 음가 흡수 4/5 Top5.

6/8·3/8 추가 근거(eighth-meter-60-v1): EM09-L12-original은 hits에는 있지만 candidates에서 제외, EM09-L8-original은 hits에도 없음. 원형 누락이므로 삭제 내성 실패와 분리하여 EVAL-007 후보 회수 감사에 포함한다. EM03의 12음 삭제 두 조건은 low-information-floors, EM08은 admission-floor 제외 근거를 기록했다. 특정 작품 예외는 추가하지 않는다.

1. memory-variation-50-v1 — 50개 변형 + 대조 15개 완료.
2. octave-combination-20-v1 — 10개 원형의 국소 옥타브 이동과 옥타브+장식음 누락, 대조 포함 30회.
3. short-query-90-v1 — 이전 20곡 밖의 새 원형 10곡, 3/4 세 곡·4/4 일곱 곡의 12/8/6음 paired 변형. 6/8은 아직 미검증. 서로 겹치는 prefix를 독립 성공률로 합산하지 않는다.

전체 테스트 종료 후 공통 원인별로 묶고, 대조군 회귀·오탐·속도 비용까지 비교해 적용 여부를 결정한다.
