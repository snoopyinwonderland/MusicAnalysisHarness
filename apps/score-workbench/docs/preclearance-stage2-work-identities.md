# 사전검토 2단계: 작품과 판본 연결

2026-09-14. 사전검토 결과 집계에 적용하며 일반 텍스트 검색에는 적용하지 않는다.

## 저장 구조

`data/work-identities.json`은 canonical composition과 source별 edition을 연결하는 별도 registry다. 인덱스를 재작성하지 않는다. canonical ID, 검토 상태, 근거, 검토 주체, 원본 source ID와 SHA-256, 편성, 원본 권리 표기와 미확정 권리 상태를 보존한다.

일치하는 제목만으로 작품을 통합하지 않는다. 제목/작곡가 정규화는 NFC, 공백, 대소문자와 Composed by 접두어에 한정한다. 악장 번호·부제·작품번호를 제거하거나 동명이곡을 추측하지 않는다. 동일 메타데이터는 needs-review 후보만 생성한다.

현재 확인한 ENDLESS LOVE의 Duet/Trio/Quartet은 세 원본 XML의 제목과 Lionel Richie 작곡가 정보, 명시적인 편성명, 판본별 5개 이상의 exact 구간으로 같은 작품임을 교차 확인했다. `humanConfirmed:false`, reviewer=implementation-audit를 명시했다. 음악학 전문가나 사용자가 직접 확인한 라벨로 가장하지 않는다.

## 적용과 갱신

`server/work-identity.mjs`는 verified 상태의 명시적 source 연결만 해석한다. 중복 canonical ID와 충돌 source 연결은 오류다. 메타데이터가 달라지면 metadata-conflict, registry와 인덱스 크기/mtime이 다르면 stale-index로 보류한다. 원본 SHA-256은 감사 당시 증거이며 검색마다 XML 전체를 읽어 검증하지 않는다. 원본 변경 뒤에는 재인덱싱과 registry 재검토가 필요하다.

사전검토 job manifest에 registry hash와 resolver 코드 hash를 추가했다. 매핑이 바뀐 경우 과거 집계가 무심코 재사용되지 않는다. 기존 보고서는 `regroup-preclearance-results.mjs`로 검색 재실행 없이 새 경로에 재집계할 수 있다.

## 결과 보존

대표 점수는 최고 구간 유사도다. 판본 수나 반복 횟수를 점수에 더하지 않는다. coverage는 기존 query event ID 합집합이다. 각 match에 원래 work/source/stream, 마디, target 음표, alignment, accessPolicy와 rightsStatus를 남기고, editions 배열에 판본별 목록을 제공한다. 원본의 권리 표기는 법적 권리 상태 확정값이 아니므로 rightsStatus는 unknown이다.

## 검증 결과

- 관련 테스트 17개 통과: 동명이곡, 미검토 후보, 매핑 충돌, 오래된 인덱스, 실제 사례 회귀.
- 기존 28개 그룹 → 26개 그룹. ENDLESS LOVE 판본 3개 → 작품 1개.
- ENDLESS LOVE의 23개 match와 전체 결과의 match 총수가 그대로 보존됨.
- 최고 유사도 100, coverage 100% 유지. 300점처럼 합산하지 않음.
- 동일 제목/작곡가 검토 후보 묶음은 6개이며 그중 하나가 이번에 연결한 ENDLESS LOVE다. 나머지 5개는 아직 자동 통합하지 않았다.
- 전체 결과: `evaluation/runs/preclearance-grouped-2026-09-14.json`.

```powershell
node scripts/regroup-preclearance-results.mjs evaluation/runs/preclearance-search-2026-09-14.json NEW-grouped-report.json
```

## 남은 범위

작품 식별 registry는 현재 검증한 한 작품부터 시작한다. 전체 corpus의 판본 판별 완료를 뜻하지 않는다. 검토 UI, 외부 작품번호/권위 ID 연결, 악장/부분곡/공유 선율군 관계는 후속 확장이다. THAXTED/Jupiter처럼 같은 선율을 공유하는 다른 작품은 동일 composition으로 성급히 합치지 않고 별도 tune relationship이 필요하다.

다음 단계는 후보 작품에 동일 구조 분석을 적용해 양쪽 Phrase/Motif의 중요도를 비교하는 작업이다.
