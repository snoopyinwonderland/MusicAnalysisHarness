# Claude 인계: 2층 Phrase 분석과 음표 단위 Motif 탐색

브랜치 `claude/phrase-breath-layer` (worktree `K:\MusicSearch-breath-layer`, base `d9bca19c`).
원본 구현과 실험 기록: `K:\Music Composition\musicomp` / `K:\Music Composition\DEVELOPMENT_LOG.md` #14–#23.
모든 수치는 musicomp의 벤치마크 도구로 측정했다. 경로는 아래 "재현"에 있다.

## 1. 커밋 구성

| 커밋 | 내용 |
|---|---|
| 984292cc | 하위층(호흡 단위) `server/phrase-breath-layer.mjs` |
| c6892608 | 상위층 + 종지 근거, `search-api` `phraseLayers` 필드, `PhraseLayersPanel` |
| 650ca3b4 | 통합 검토 반영(종지 강도 관문, 붙임줄 검증, 마디별 박자, 패널 문구) |
| (이 커밋) | `server/motif-discovery.mjs` + 테스트 + 이 문서 |

기존 `analyzePhraseBoundaries`, `boundary-harmony.mjs`, `phraseMotifs`, `buildMotifSpans`는 수정하지 않았다.

## 2. Motif: 무엇을, 왜

### 측정 (선율 수준, 출현 구간 IoU ≥ 0.5 일대일, 가족 = 같은 정답 Motif끼리 묶였는지 쌍 단위)

| 엔진 | BPS-motif 출현 F1 | BPS 가족 P / R | JKU-PDD 출현 F1 | JKU 가족 P / R |
|---|---|---|---|---|
| MusicSearch 현재(analyzePhraseBoundaries → buildPhraseSpans → buildMotifSpans) | **0.401** | 0.952 / 0.349 | 0.164 | 1.0 / 0.677 |
| `discoverMotifs` 단독 | 0.300 | 0.965 / **0.623** | **0.312** | 1.0 / **1.0** |
| **현재 구간 + `linkMotifSpanFamilies`(가족 관계 합침)** | 0.401 (그대로) | 0.786 / 0.474 → 가족 F1 0.51→**0.59** | 0.164 | 1.0 / **1.0** |

- 정답 자료:
  - BPS-motif: 베토벤 소나타 1악장 32곡. 1번 보표 스카이라인 위의 출현 3,329개만 정답으로 쓴다.
  - JKU-PDD: 5곡, 단선율 버전, 112개
- 현재 엔진은 프레이즈 안에서 자르므로 **구간**이 더 정확하다. `discoverMotifs`는 같은 Motif의 반복을 이조·박 내 위치와 무관하게 이어 주므로 **가족 연결**이 강하다.
- 그래서 **구간은 현재 것을 유지하고, 가족 연결 근거만 추가**하는 것을 권한다.
- 결합 방식(union)에는 조정한 값이 없다. `discoverMotifs` 기본값은 BPS 2겹 교차 검증으로 정했다(최소 4음, 이득 기준 16, 경계 가중 0.5, 최대 4마디, 역행 변형).
- 같이 시험했으나 채택하지 않은 것(효과 없음 또는 출현 F1 하락): 공동 경계 확장, 근사 변형(반행·역행 포함 유사도), 정확한 반행·확대·축소, 학습형 "Motif다움" 필터, 이득 기준 확대. 기록 #22–#23 참고.

### API
- `discoverMotifs(notes, options?)` → `{version, params, families:[{id, notes, gain, occurrences:[{startIndex, endIndex, start, end, variant}]}], skipped?}`
  - 철자(spelling 또는 tpc)가 없으면 추측하지 않고 `skipped`를 반환한다.
  - 붙임줄 뒷음은 같은 음높이이고 시간이 이어질 때만 합친다.
- `linkMotifSpanFamilies(notes, spans, discovery)` → 각 span에 `linkedFamily`, `linkSources`를 붙인다. **span의 start/end는 바꾸지 않는다.**
  - span이 discovery 출현에 시간의 절반 이상 덮이면 그 가족으로 연결된다.
  - 두 출처 중 하나라도 연결하면 같은 가족이다.

### Python 원본과의 일치
- 출현 구간이 완전히 같은 곡: BPS 30/32, JKU 5/5
- 혼합 점수는 소수 셋째 자리까지 같다.
- 차이는 못갖춘마디의 박 내 위치(phase) 계산 기준과 호흡층(JS 포트) 미세 차이에서 온다.

### 비용
- O(n²) 시간·메모리(Int16 n×n). 벤치마크 37곡 합계 6.2초, 가장 긴 곡 3,719음에서 0.72초(이 PC, Node)
- 작품별로 캐시해야 한다. 캐시 키는 source SHA + stream + 엔진 버전으로 잡는 것을 권한다.

## 3. 통합 제안 (Codex 판단)
1. 서버: getWork 응답에 `motifDiscovery = discoverMotifs(notes)` 필드를 추가하고 캐시한다. 기존 필드는 바꾸지 않는다.
2. 화면: `buildMotifSpans` 결과에 `linkMotifSpanFamilies`를 적용한 **비교 레이어**로 먼저 도입한다. `familyNumber` 대신 `linkedFamily`로 색과 라벨을 정하는 선택지다. 피드백 ID나 Motif 번호 체계가 바뀌지 않도록 기존 번호는 유지한다.
3. 회귀: 반복 변형, 못갖춘 Motif, 붙임줄 작품. Phrase 레이어와 같은 목록을 쓴다.
4. 주의: union은 가족 정밀도를 낮춘다(BPS 0.95→0.79). 잘못 묶인 가족이 화면에 보일 수 있다. 피드백 검토 대상으로 표시하는 것을 권한다.

## 4. 재현 (musicomp, `K:\Music Analysis\.venv\Scripts\python.exe`)
```
python -m musicomp.tools.motif_benchmark --engines musicomp,discovery,bars
python -m musicomp.tools.motif_benchmark --export-musicsearch <notes.json>
#  -> 이 브랜치에서 임시 vitest 프로브로 buildMotifSpans + discoverMotifs + linkMotifSpanFamilies 실행 -> <out.json>
python -m musicomp.tools.motif_benchmark --score-musicsearch <out.json>
python -m musicomp.tools.motif_tune [--extend|--approx|--salience|--gain]
python -m musicomp.tools.layers_port_check     # Phrase 상위층 DCML 회귀
```
외부 자료(연구용 라이선스): `K:\Music Composition\data\external\{bps_motif, jkupdd, essen, mtc}`
