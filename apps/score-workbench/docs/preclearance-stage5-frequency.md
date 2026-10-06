# 코퍼스 빈도 기반 검토 순서 A/B — v1

## 무엇을 측정하는가

선택 Query의 연속 5개 반음 음정(6개 음표) 패턴을 기존 `i5:` index 형식으로 추출한다. Query 내 중복 토큰은 한 번만 평가한다. 검색 top-k 결과가 아니라 grams 전체에서 해당 토큰을 포함하는 **서로 다른 source 파일 수**를 구한다. 한 파일의 파트·voice·반복 등장은 중복 집계하지 않는다. 같은 작품의 다른 판본은 여전히 별도 파일이므로 canonical 작품 빈도가 아니다.

쉼표·리듬·Phrase 맥락과 전체 긴 멜로디의 동일성은 이 빈도에 포함되지 않는다. 음계/아르페지오 등 관용구를 알아보는 보조 신호이며 originality나 보호 가능성을 판정하지 않는다. 업로드 원본이 DB에 있으면 그 source도 모집단에 포함된다.

## 계산과 불확실성

N=전체 source 수, df=해당 패턴을 포함하는 source 수. 패턴별 `log((N+1)/(df+1)) / log(N+1)`의 중앙값을 rarityProxy로 사용한다. 희귀할수록 1에 가깝다. 실험 계수는 `0.85 + 0.15 * rarityProxy`다. baseline match 점수에 곱하고 작품별 최대값을 선택한다. 중복을 합산하지 않는다.

하나라도 미관측/잘못된 df거나 토큰이 부족하면 unknown이다. 없는 패턴을 독창성의 증명으로 취급하지 않는다. 이 선택은 보수적이며 입력 음 하나를 바꿨을 때 패턴이 없어지는 경우도 unknown으로 남는다. 통계학적으로 보정된 침해 확률이나 전문가 기준의 가중치는 아니다.

`works` 및 `priorityReview`는 유지하고 `corpusPriorityReview`에 새 순서와 match별 baseline/새 점수/df/계수를 저장한다. 기존 검색 순서와 전문가 라벨을 덮어쓰지 않는다.

## 실행과 인수인계

```powershell
node scripts/measure-preclearance-frequency.mjs evaluation/runs/preclearance-priority-2026-09-15.json evaluation/runs/preclearance-frequency-2026-09-15.json
```

새 output을 사용한다. 기존 priority report의 index size/mtime와 현재 index를 비교하고 WAL이 있는 DB는 거부한다. worker 읽기 전용 조회, 180초 제한, Ctrl+C 종료를 지원한다. 실패하면 성공 보고서를 쓰지 않는다. 입력/코드/DB 지문, df 전부를 보관해 재검토한다. mtime는 내용 해시의 대체가 아니므로 데이터 인계 시 별도 SHA-256 검증이 필요하다.

처음의 JOIN 방식은 60초 제한에서 중단됐다. 최종 방식은 works의 ID→source 대응표를 한 번 읽고 각 token의 distinct work_id를 source로 매핑한다. 의미는 동일하며 반복적인 큰 works 행 조회를 줄인다. DB 수정/새 index 생성은 하지 않는다. 이 방법도 전체 조회이므로 요청마다 웹에서 호출하지 않는다.

## 검증 상태

- 관련 7개 테스트 파일의 40개 테스트 통과.
- 실제 소형 SQLite/worker 테스트로 한 source의 여러 파트·반복 posting이 1번으로 집계됨을 확인했다.
- 희귀/흔한 토큰의 방향, 미관측 unknown, 조옮김 불변, baseline 불변 회귀를 확인했다.
- 전체 DB 실행 완료: 95,813 source, 64개 unique i5 패턴, 약 75.43초. 결과 `evaluation/runs/preclearance-frequency-2026-09-15.json`.
- 관측 df 범위 47~62,268. 동일음 6개 패턴 `i5:0,0,0,0,0`은 62,268 source에서 관측됐다. 이것이 긴 전체 멜로디가 그만큼 등장했다는 뜻은 아니다.
- 26개 작품/56개 match의 빈도 계수가 모두 계산됐다. unknown 0. 기존 works와 baseline priority를 포함한 전체 입력 report가 새 필드 외에는 동일함을 deep equality로 확인했다.
- baseline 검토 순위 대비 순서 변화 0개. ENDLESS LOVE의 실험 점수 87.84→80.33, 1위 유지. 이번 자료에서 품질 향상을 입증하지 못했으므로 메인 검색에 적용하지 않는다.
- 다음 평가는 반복음, 음계, 아르페지오, 드문 도약을 균형 있게 포함하고 사람의 비교 순위 판단을 받아야 한다.

## 다음 한계

검증된 작품 identity를 활용한 판본 빈도 보정, 장르/시대/편성별 모집단 편향, 전체 phrase/리듬 빈도, 전문가 A/B 라벨이 필요하다. 현재 숫자만으로 침해 위험 등급을 만들지 않는다.
