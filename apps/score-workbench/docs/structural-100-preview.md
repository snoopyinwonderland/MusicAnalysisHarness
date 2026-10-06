# 構造 변형 100개 악보 미리보기

2026-09-16. 상태: 검토용 생성 초안 완료. 사용자 확인 후 검색 baseline 실행 시작; 최종 완료 여부는 실행 summary.json 기준. 음높이 변경 등 별도 음성 대조군은 미생성.

## 단계별 평가 합의 및 실행

### 완료 결과와 12개 악보 검토 페이지

120건 완료, 실패/timeout 0. 변형 100개 source 회수 100, 1위 64, top5 99, 원 구간 대응 proxy 통과 89. 원본 대조군 20개 모두 회수. 변형 중앙 지연 16.6초/p95 38.6초. 이는 삽입 중심 초안의 결과이며 복잡한 장식 교체 전반의 성능을 뜻하지 않는다.

사용자 요청에 따라 `evaluation/reports/structural-review-12-v1/index.html`에 원 구간 proxy 미통과 11개 및 S100-055(원곡 8위)를 모았다. 각 카드에 변형 전 Query, 변형 Query, 실제로 회수된 원곡의 XML 악보 및 alignment 색칠을 제공한다. 8위 사례는 1위 경쟁 악보도 추가했다. 12개 카드/37개 악보 렌더링 및 표시 ID 검사 성공, 오류 0. 모든 악보의 브라우저 배치/청취를 수동 검수했다는 의미는 아니다.

원본/변형은 비교 재기보이므로 악보 안의 마디 번호는 원본과 다르다. 검색 결과는 원 XML을 사용한다. 재생은 저장된 검색 성부만 사용하며 전체 반주 재생이 아니다. `cases.json`에는 원본/변형 Query, 원본 위치, 실제 결과와 변경 기록을 저장했다. 다른 반복 구간을 찾은 경우가 있을 수 있으므로 proxy 미통과를 오탐 판정으로 바꾸지 않았다.

재현: `node scripts/export-structural-review.mjs evaluation/reports/structural-review-12-v1` (새 출력 폴더 필요).

사용자가 현재 변형을 이번 단계로 평가하고, 그 결과를 본 뒤 다음 단계에서 변형을 추가하기로 했다. 현재 suite는 유지하고 다음 suite를 별도 버전으로 만든다. 이번 결과를 보기 전에 검색 계수나 변형 강도를 바꾸지 않는다.

`scripts/run-structural-baseline.mjs`를 통해 `evaluation/runs/structural-baseline-v1/`에 원본 20개 + 변형 100개를 실행한다. 전체 DB, top100, query당 60초 제한. 원본/변형 성공률과 timeout을 분리하며 원곡이 없는 결과를 자동으로 오탐 확정하지 않는다. 각 Query 원문, 결과 전체, 순위, 원 구간 대응 proxy, 문제를 보존한다. manifest에는 suite/검색 엔진 hash와 DB 크기/mtime을 기록하며 변경되면 중단한다.

재개: `node scripts/run-structural-baseline.mjs evaluation/runs/structural-baseline-v1`. 이미 기록된 실패를 자동으로 덮어쓰거나 재시도 성공으로 바꾸지 않는다. 결과 악보의 실제 표시/상위 경쟁 결과 청취는 별도 검토 대상이다.

## 산출물

- `evaluation/reports/structural-100-preview-v1/index.html`: 100개 카드, 원본/변형 200개 Verovio 악보. 유형 필터, 90 BPM 재생/정지, Query JSON.
- 같은 폴더 `suite.json`: 원본 20개, 변형 100개, 원 XML 연결, 보존 ID, 분석기 후보 ID, 변경 기록, sourceToQueryMap.
- `render-audit.json`: 200개 렌더링 성공 및 표시 대상 SVG ID 존재 검사. 브라우저에서 모든 악보 배치/청취를 검수했다는 뜻은 아니다.

파랑은 생성기 보존음, 보라는 그중 자동 분석기 후보, 빨강은 추가/변경음(표시 우선)이다. 음가를 분할한 보존음도 빨강으로 보일 수 있다. 보존 조건은 해당 원음의 pitch와 attack onset이며 모든 원음의 duration까지 유지하는 조건은 아니다. tie가 아니라 반복 재타격을 생성한 경우 별도 소리가 맞다.

## 생성 규칙과 중요한 한계

기존 harder-100의 실제 원본 20개/10음 Query를 재사용한다. 처음/끝 음과 XML 감사에서 얻은 기둥 후보를 보존 대상으로 지정한다. 이것은 확정 Schenker 기둥이 아닌 source-derived scaffold다. 제안했던 12–32음의 새로운 층화 표본은 아직 아니다.

각 20개: 2/4반음 사이 중간음 삽입, 반음 이탈-복귀 추가, 같은 음 재타격 분할, 보호되지 않은 내부 도착의 음가 이동, 경과/보조 형태 결합. 모든 입력 쉼표와 전체 길이를 보존한다. 모든 원래 음높이도 유지한다. 따라서 기존 장식음을 서로 다르게 교체/삭제한 본격 검증보다 쉬운 삽입 중심의 파일럿이다.

반음 보조 형태는 조성에 따라 어색할 수 있다. 특히 비교 첫 음의 축약은 보존 attack은 유지해도 중요도 지각을 바꿀 수 있다. 자동 생성 성공을 음악적 동등성의 증명으로 사용하지 않는다. 사용자의 악보/청취 검토를 위한 초안으로 먼저 공개한다.

화성 근거를 인위적으로 추가하지 않았다. 신규 구조 축약 모듈은 production 검색에 연결하지 않았으며 검색 결과/순위를 만들어 쓰지 않았다.

## 재현 및 다음 단계

```powershell
node scripts/build-structural-preview.mjs evaluation/reports/structural-100-preview-v1
node node_modules/vitest/vitest.mjs run scripts/structural-variation.test.js server/structural-reduction.test.js
```

기존 출력 보호를 위해 새 폴더만 허용한다. 다음은 검토에서 부자연스러운 변형 분류, 장식 교체/삭제 확장, 별도 대조군 생성, suite 동결 후 기존 검색 baseline이다. 현재 페이지의 100개를 이미 검증된 정답 100개라고 취급하지 않는다.
