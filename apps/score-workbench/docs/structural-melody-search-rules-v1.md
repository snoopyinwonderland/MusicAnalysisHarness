# 기둥음 보존·장식 변형 검색: 연구 근거와 일반 규칙 v1

작성: 2026-09-15. 상태: 설계/검증 계약. 이 문서 작성으로 production 검색 점수나 인덱스는 변경되지 않았다.

## 1. 목적과 비목적

사용자 요구: Twinkle–Ma Boy처럼 기둥 진행이 비슷하고 장식이 다른 사례를 탐지하되, 특정 작품에 맞춘 강화 없이 일반적인 규칙을 만든다. 원음표를 기본으로 삼으며 설명 가능한 축약만 허용한다.

목표는 Schenker-informed local structural similarity다. 완성된 Schenker 분석, Ursatz 탐지, 작곡가 의도 판독, 침해 여부의 자동 확정이 아니다. 기능적 조성이 약한 음악에서도 직접 선율 검색은 유지한다. 화성 정보가 부족하면 분석 범위와 확신을 줄이지, 알려지지 않은 화성을 임의로 채우지 않는다.

핵심 원칙: 기둥음만 먼저 골라 나머지를 버리지 않는다. 원음 전체에서 어떤 음이 어떤 앞뒤 음에 종속되는지를 설명하고, 그 설명이 허용하는 범위에서만 축약한다.

## 2. 확인한 연구와 적용 범위

아래 연구 요약과 이후의 MUSICANOTE 설계 제안은 구분한다. 제안하는 수치/게이트는 논문에서 검증된 우리 서비스용 정답이 아니다.

| 연구·읽은 범위 | 확인된 내용 | 채택할 아이디어 / 주의점 |
|---|---|---|
| [Kirlin & Jensen 2015, Learning to Uncover Deep Musical Structure](https://ojs.aaai.org/index.php/AAAI/article/view/9476), 공식 초록 | 계층 분석의 확률 모형, 학습 및 평가 | 하나의 결정적 규칙 대신 대안 분석과 신뢰도를 보존. 우리 데이터의 성능 보장은 아님 |
| [Kirlin & Yust 2016, Analysis of Analysis](https://www.cs.rhodes.edu/~kirlinp/papers/kirlin16analysis.pdf), 본문 §2–6 | 화성·선율·박자·시간 척도를 함께 평가. 사용된 Schenker41은 장조·비전조의 제한된 발췌 자료이며 분석 수준에 따라 유효한 특징이 달라짐 | 강박 점수를 Schenker 점수로 대체할 수 없음. 국소 장식과 마디 간 구조를 별도 취급. 고전 자료 결과를 대중가요에 그대로 이식하지 않음 |
| [Marsden 2010, Schenkerian analysis by computer](https://eprints.lancs.ac.uk/id/eprint/34349/), 기관 저장소 초록 | 문법/차트 파싱으로 축약 대안을 만들지만 가능한 분석이 매우 많고 계산 부담 및 선택 기준 문제가 있음 | 작은 구간과 제한된 가설 수부터 시작. 전체 DB에 모든 축약 조합을 생성하지 않음 |
| [Yust 2015, Voice-Leading Transformation and Generative Theories of Tonal Structure](https://www.mtosmt.org/issues/mto.15.21.4/mto.15.21.4.yust.php), 계층·변환 논의 | 단순한 diminution 관계와 성부진행 변환을 구별하여 설명 | passing/neighbor 축약과 register transfer/성부 이동을 같은 삭제 연산으로 만들지 않음 |
| [Hu & Arthur 2021, A Statistical Model for Melody Reduction](https://arxiv.org/abs/2105.05385), 저자 초록 | 박자 위치·음가·진입/이탈 음정을 이용한 chord-tone 예측, TAVERN 사용 | 설명 가능한 국소 특징 설계 참고. chord tone과 작품의 주요 기둥음은 동일 개념이 아님 |
| [Ni-Hahn et al. 2024, A New Dataset, Notation Software, and Representation for Computational Schenkerian Analysis](https://arxiv.org/abs/2408.07184), 저자 초록 | 발표 시점 140개 초과 발췌와 이종 edge 그래프 표현 제안 | source event를 연결하는 typed graph와 사람의 분석 연결에 적합. 데이터/코드 라이선스와 실제 형식은 도입 전 별도 확인 |

2016 연구는 단순히 downbeat 가중치를 높일 근거가 아니다. 본 서비스의 검색 정확도와 분석 그래프의 정확도도 다른 지표다. 첨부된 교재 원문을 이번 단계에서 새로 읽거나 데이터로 복제하지 않았다. 연구 데이터에 해당 교재 분석이 포함되었다는 사실은 원전 전체 검토를 대체하지 않는다.

## 3. 기존 구현 감사

- `server/search-api.mjs`의 `annotateStructural`: 박자·지역 음가·tie·쉼표 경계·passing/neighbor 형태를 휴리스틱으로 결합한다. 화성 의존 관계 그래프는 없다.
- `structuralReduction`: weight .68 이상을 선택하고 부족하면 상위 최대 3음을 채운다. `metricalSkeleton`도 부족할 때 최대 4음을 채우는 fallback이 있다. 새 계층에서는 최소 개수를 억지로 채우지 않는다.
- `metricalSkeletonEvidence`: 축약본을 alignLocal로 다시 정렬한다. strongCoverage는 대응 여부 중심이므로 정확한 기둥 음높이·도착 위치 보존율과 구분해야 한다.
- `sparseAlignmentAllowed`는 short/weak/auxiliary 설명을 사용하지만, 모든 생략에 양쪽 anchor와 관계 증명이 붙는 구조는 아니다. explicitStructural 경로도 새 검증을 우회해서는 안 된다.
- `server/preclearance-musical-evidence.mjs`의 `sourceAnchors`는 상대 곡을 받지 않고 두 가지 지지 단서를 요구한다. 새 구현의 독립 분석 원칙에 적합하나, 화성 부재와 음가/박자 단서의 상관성은 남는다.
- 같은 파일의 metric 추정은 분자 3의 배수로 복합박을 추정하는 경로가 있다. 6/8과 6/4의 실제 grouping, 3/2, 혼합박을 명시 계약으로 통일해야 한다.
- tieStop 플래그만으로 attack을 배제하는 경로는 tie 병합 이벤트와 의미가 일치하는지 회귀 검증이 필요하다. 실제 확인 전 현재 모든 타이를 오류라고 단정하지 않는다.
- 이미 후보에서 탈락한 작품은 skeleton 보너스로 복구되지 않는다. 검색 후보 회수와 최종 비교를 분리해서 개선해야 한다.

## 4. 입력 및 원본 보존 계약

각 event: sourceHash, partId, staffId, voiceId, xmlNoteId, measureOrdinal, originalMeasureLabel, onsetQ/durationQ의 유리수, MIDI pitch, 원래 spelling, tieChainId, attack 여부, grace/cue, rest, meter/grouping, 원본 좌표를 유지한다.

1. XML 원문은 보존하고 분석은 sidecar overlay에 저장한다. 최소 핵심 구간 앞뒤 2마디, phrase를 판단하는 데 필요하면 해당 phrase 및 인접 경계까지 저장한다. 개인정보/배포 정책은 별도 유지한다.
2. 같은 part라도 독립 voice를 섞지 않는다. 동일 voice의 cross-staff는 명시적인 연결 정보와 시간 연속성이 있으면 유지할 수 있다. 불명확하면 별도 가설로 보류한다.
3. chord onset에서 최고음만 선택한 기존 stream은 내성부 관계의 근거가 아니다. 필요한 경우 원 XML에서 동시 성부를 다시 읽는다.
4. tie chain은 한 sounding event로 비교하되 모든 표기 음표 ID로 역매핑한다. 강박을 통과하는 sustain과 그곳에서 새로 울린 attack은 분리한다.
5. 쉼표는 무음 구간이며 prolongation용 음높이가 없다. 쉼표 너머를 자동으로 passing 연결하지 않는다.
6. 조옮김 비교용 sounding pitch와 악보 재현용 written pitch를 구별한다. 이명동음은 pitch 비교에서는 같아도 diatonic step 판정에서는 spelling/조성 불확실성을 남긴다.
7. 분석 실패/정보 부족은 null 또는 insufficient-evidence로 저장한다. 0점 불일치와 구분한다.

## 5. 음 하나의 중요도보다 관계를 판정하는 규칙

모든 축약 후보는 `leftAnchor, interiorEvents, rightAnchor, ruleId, support, contradictions, confidence, contextRange`를 반환해야 한다. 인접하지 않은 음을 연결할 때 사이의 모든 event가 설명 대상이다. 끝점 선택 역시 상대 곡을 보지 않고 결정한다.

| ID | 허용 조건 | 축약 방식 | 금지/반례 |
|---|---|---|---|
| R01 tie | 동일 음·성부의 유효한 tie chain | attack 하나, duration 합, 표기 ID 전부 보존 | 새로 반복한 같은 음을 tie로 합치지 않음 |
| R02 passing | 같은 선율선에서 두 끝점 사이를 일관된 순차 진행으로 연결; 끝점 지지와 내부의 낮은 구조 지지 | 내부를 passing 관계로 귀속 | 짧다는 이유만으로 도약음을 삭제, 해결 전 phrase 경계, 새 화성/주요 도착음은 보호 |
| R03 neighbor | A–B–A의 이탈·복귀, B는 문맥상 인접음; 시간/화성 지속과 부합 | A의 elaboration, B와 복귀 ID를 유지 | B가 길고 독립 도착/강한 반복 요소이면 자동 축약하지 않음 |
| R04 repeated pitch | 같은 음의 재타격이 하나의 국소 기능을 분할하며 새 화성·phrase 기능이 없음 | pitch plateau와 attack pattern을 동시에 보존 | 반복 횟수/리듬이 motif의 특징이면 버리지 않음; tie와 별도 |
| R05 anticipation | 다음 화성/도착음의 선행 출현으로 설명되고 실제 다음 도착으로 연결됨 | 도착 관계를 기록, 원 onset은 유지 | 약박이라고 anticipation 확정 금지; 미확인 화성이면 provisional |
| R06 suspension/appoggiatura | 준비/불협화/해결 또는 문맥상 지연 해결이 확인됨 | tension–resolution 쌍으로 저장 | 강박 비화성음을 무조건 주요 기둥 또는 무조건 장식으로 결정하지 않음 |
| R07 arpeggiation | 같은 화성의 음역 전개와 일관된 성부 흐름; 화성 지지가 있음 | chord-space 전개 관계 | 분산화음의 첫 음만 남기기 금지; 화성 바뀌거나 개성적 선율이면 보존 |
| R08 register transfer | 동등한 기능의 옥타브 이동이 지속 문맥/성부 연결로 설명됨 | 원 음역과 기능 음높이 병행 | 각 음을 독립적으로 mod12 정규화하여 도약을 모두 없애지 않음 |
| R09 chromatic elaboration | 조성/spelling 또는 해결 방향 근거가 있는 반음 접근 | chromatic passing/neighbor 가설 | 반음이라는 이유만으로 blue note·주요 변화음 삭제 금지 |
| R10 phrase boundary | 쉼표·종지·반복 단위·지속 해결 등 복수 문맥과 외부 분석기 근거 | opening/closing 확률과 소속 저장 | 마디 첫 음/긴 음 하나만으로 새 phrase 확정 금지 |

R02/R03의 step은 원칙상 diatonic adjacency를 우선하고 반음 간격은 보조로 쓴다. 조성/표기가 불확실할 때 1–2반음 근접 형태를 후보로만 만들며 확정 비화성음이라고 쓰지 않는다. 0반음은 passing이 아니라 repeat다.

R05–R09는 초기 검색에서 자동 할인 범위를 넓히는 규칙이 아니라 보수적 연구/검증 항목이다. 앞뒤 3음의 모양만으로 복잡한 성부진행이나 중경층을 주장하지 않는다.

## 6. 기둥 지지·보호·보류 규칙

서로 다른 지지군을 사용한다: A 화성/해결, B 선율 관계/국소 도착, C 박자, D 상대 음가/지속, E 반복되는 phrase 내 안정 위치, F phrase 분석 문맥. 동일한 downbeat 사실을 여러 필드에서 읽어 중복 가산하지 않는다.

- 강박과 긴 음은 지지이지 충분조건이 아니다. 화성음이라는 이유만으로 기둥도 아니다.
- 짧은 음도 음역 정점, 화성 변화, 주요 해결, 반복되는 특징 음이면 보호한다.
- 약박의 anticipation이나 syncopated anchor도 기둥 후보다. 실제 attack phase와 지지하는 beat를 별도 저장한다.
- 반복되는 phrase의 같은 상대 위치에서 유지되는 음은 지지 근거지만, 분석은 해당 작품 내부에서만 한다. 비교 상대와 같아서 중요해졌다는 순환 논리를 금지한다.
- 충돌하는 근거가 있으면 untouched 가설을 유지한다. 근거 부족을 상위 3음 선택으로 메우지 않는다.
- high/medium/low는 규칙 지지 수준이며 학습·교정 전 확률 %로 표시하지 않는다.
- 외부 Phrase 분석기의 경계를 강제 벽으로 쓰지 않는다. 경계 확신이 낮으면 연속 window 경로도 유지한다.

## 7. 박자와 시간 규칙

- meter timeline은 해당 event의 실제 박자를 사용한다. 4/4를 fallback 사실처럼 주입하지 않는다.
- 6/8·9/8·12/8은 확인된 복합박 grouping을 사용하고, 5/8·7/8은 2+3 / 3+2 등의 표기 또는 복수 가설을 사용한다. 6/4는 숫자만 보고 자동 동일 처리하지 않는다.
- 못갖춘마디의 표시 0과 내부 ordinal을 분리한다. pickup의 첫음은 자동 downbeat가 아니다.
- tuplet 시간은 rational 좌표로 유지한다. 반올림된 .333/.332를 서로 다른 구조로 판단하지 않는다.
- 기본 tempo scale은 구간별 하나의 비율로 추정한다. 이후 국소 시간 변형은 제한된 보정으로 기록하며 무제한 warp를 금지한다.
- 음가, onset 간격, 무음 길이, 기둥 도착 간격을 따로 비교한다. tie의 긴 음을 여러 짧은 attack과 완전 같은 리듬으로 간주하지 않는다.
- 한 마디 한 음인 후보의 모든 음이 downbeat여도, Query의 약박 분포와 대응하지 않으면 박자 일치 100점의 근거가 아니다.

## 8. 다층 표현과 검색 흐름

L0: 원 attack/rest 전체. L1: 검증된 국소 장식 관계만 축약. L2: 충분한 문맥이 있는 기둥 연쇄. L2 부재는 허용한다. 이 이름은 자동으로 foreground/middleground의 학술적 완성도를 뜻하지 않는다.

각 층당 상위 소수 대안(초기 최대 3개)을 독립 분석 점수로 선택한다. 상대와 가장 비슷해지는 분석을 무제한 탐색하지 않는다. 대안 수/선택 근거/원본 복원 경로를 모두 기록한다.

검색 단계:

1. 기존 surface 후보 회수는 유지한다.
2. offline 독립 분석에서 기둥 interval + 도착 간격 + 장식 구간 profile을 작은 별도 인덱스로 만든다.
3. 구조 후보 회수 결과를 합집합으로 추가하되 경로별 후보 예산과 탈락 이유를 기록한다.
4. 최종 비교에서 L0 원음과 모든 생략 관계를 다시 검증한다. 구조 일치 때문에 원음 검사를 생략하지 않는다.
5. 직접 일치와 구조 변형 일치를 구별해서 표시한다. 골격만 같아 Exact로 승격하지 않는다.

anchor가 너무 적거나 공통적인 3음 진행만 남으면 구조 단독 회수는 보류한다. 초기 실험 최소 4 anchor와 서로 다른 도착 관계를 요구하는 설정부터 비교하되, 짧은 Query는 기존 검색 경로로 처리한다. 이 숫자는 검증 전 설정이지 음악 이론 정리가 아니다.

## 9. 정렬 비용 제안

기본 비용은 동일한 전체 조옮김 T에서의 note residual을 사용한다: `r_i = candidatePitch_j - queryPitch_i - T`. 고립된 한 음 변경이 앞뒤 interval 둘을 동시에 크게 벌점받는 현상을 줄인다. 인접 interval은 독립 중복 벌점이 아니라 진행 보존의 보조 근거로 둔다.

`C = pitchResidual + anchorDeletion + unexplainedSkip + arrivalTiming + ornamentProfile + transformationComplexity`.

- anchorDeletion은 설명된 ornament 변경보다 비싸게 한다. 근거 없는 생략은 짧은 음이어도 싸게 만들지 않는다.
- pitchResidual은 작은 편차에 완만하되 큰 기둥 변경에는 감점을 유지한다. 정확 비교 옵션은 완화하지 않는다.
- ornamentProfile에는 원음 수, attack density, 순차/도약/이탈복귀, 내부 방향, rest occupancy, 도착 전 리듬을 보존한다.
- 전체 transposition, global inversion, 제한된 register transfer는 별도 변환이다. 위치마다 마음대로 반전하는 정렬은 허용하지 않는다.
- 기둥의 음정·음높이·contour가 상관된 만큼 같은 사실을 세 번 가산하지 않는다.
- 정렬 이후 confidence, 설명 가능 생략률, 기둥 보존율, query/후보 양쪽 coverage를 별도로 보고한다. 비용을 곧바로 침해 확률로 해석하지 않는다.

첫 실험은 점수 합산보다 규칙의 작동/실패와 feature별 원자료를 우선한다. 계수는 holdout으로 선택하며 사용자 지정 작품 순위로 수동 조정하지 않는다.

## 10. 여러 구간과 작품 수준 비교

- overlapping window, 양방향 검색, 같은 phrase 반복, 여러 판본은 독립 증거로 중복 계산하지 않는다.
- 서로 다른 phrase 가족의 대응, 원곡 양쪽에서 차지하는 attack/시간 coverage, 대응 순서 및 상대 간격을 분리한다.
- 일정한 조옮김/변형이 이어지는지와 각 구간마다 전혀 다른 변형이 필요한지를 구분한다.
- 순서를 유지하는 비중복 구간 사슬을 찾고, 추가 구간의 기여는 포화되도록 설계한다. 한 구간 점수 × 등장 수는 사용하지 않는다.
- 흔한 scale/arpeggio/반복음 골격은 배경 빈도로 보정하되 판본 중복을 작품 빈도로 세지 않는다.
- 구조 유사성 발견과 법적 침해 판단은 별개다. Twinkle–Ma Boy의 사용자 평가는 관찰 기록이며 학습용 확정 양성 라벨이 아니다.

## 11. 보존 데이터 계약

별도 내보내기가 가능한 versioned JSON + 재현용 XML/이벤트를 사용한다. 필요한 공통 IR subset을 정의하되 외부 Canonical IR 전체 도입이 전제는 아니다.

필수 필드:

- caseId, sourceHash, sourceContext, originalQuery, mutationType, generatedQuery, sourceToQueryMap.
- generatorPreservedAnchors와 analyzerInferredAnchors를 다른 필드로 보관.
- analysisVersion, parserVersion, phraseAnalyzerVersion, model/ruleConfigHash, meter/harmony provenance.
- reductionGraph: event nodes, typed dependency edges, support/contradictions, untouched alternative, layer.
- retrievalTrace: 경로별 회수, shortlist, 탈락, 최종 순위, 원곡/판본 식별, 정렬 원음 ID.
- review: 사용자 원문, 관찰 구간, 가설, 자동 측정, 전문가 판정, 상태를 분리.
- issues: 유형, 재현 절차, 개선안, 적용 commit, regression 결과. 이전 실패 기록을 덮어쓰지 않음.

외부 Phrase 분석기가 업데이트되면 dependency hash가 바뀐 해당 분석/인덱스만 무효화한다. 사람 주석을 삭제하지 않고 이전 분석을 참조한 기록임을 유지한다. Motif는 선택 입력이며 필수 의존성으로 만들지 않는다.

## 12. 100개 검증과 대조군

20개 원본 × 5유형: passing 추가, neighbor 교체, 재타격 분할/병합, 기둥 도착을 유지한 내부 리듬 변화, 두 종류 결합. 원본마다 12–32음 범위의 문맥 있는 구간을 우선하고, 다양한 박자/음역/장르를 층화한다. 정확한 표본 수와 분포는 suite 생성 전에 동결한다.

별도 대조군: 원본 20개, 기둥 변경 20개, 흔한 골격만 같은 비관련 구간 20개. 대조군을 100개 변형 성공률 분모에 섞지 않는다. 기둥 변경이 반드시 검색에서 사라져야 하는 것은 아니며, 동일 크기의 장식 변경보다 구조 점수가 적절히 낮아지는지 검사한다.

필수 반례: 약박 기둥, 강박 suspension, 긴 neighbor, 반복음 hook, 못갖춘마디, 혼합박, tuplets, tie sustain, cross-staff 동일 voice, 독립 voice 섞임, 화성 변경, 불명확한 조성, 흔한 분산화음, global inversion, 국소 옥타브 이동.

검증 분리:

1. 생성기가 보존한 anchor를 알고 있다는 사실은 분석기가 그것을 찾아냈다는 뜻이 아니다.
2. 생성기와 분석기를 독립 평가하고 실패 가설/기각 이유도 저장한다.
3. 원곡 가족/판본을 기준으로 개발/holdout을 분리한다. 같은 원본의 다섯 변형을 나누어 누수시키지 않는다.
4. 현재 검색 baseline을 먼저 실행한 뒤 후보 회수만 추가, 정렬만 변경, 둘 다 변경을 비교한다.
5. Recall@1/5/20/100, source-window coverage, 기둥 precision/recall(검토된 부분만), 구조 오탐률, 추가 후보 수, p50/p95, timeout을 기록한다.
6. 붉은 note ID/타이 전체/원음 복원은 자동 검사; 실제 악보 배치와 청취 평가는 별도 표본 검토로 구분한다.
7. 상위 결과가 원곡이 아니라는 사실만으로 오탐이라고 판정하지 않는다. 경쟁 결과의 특징과 정당성을 blind review한다.

배포 게이트: 동일 표본 baseline보다 구조 변형 회수 개선, 대조군 precision 악화 없음, 기존 exact 회귀 없음, 전체 p95 비용 보고. 통계적으로 판단하기 부족하면 확대 검증하며 임의로 통과 선언하지 않는다.

## 13. 실행 순서 및 미완료 사항

1. 본 규칙/버전/반례 계약 확정 및 기존 코드 테스트 목록 작성 — 문서 완료, 구현 미착수.
2. 공통 event/tie/meter 계약과 관계 후보 생성기 구현; 기능 flag 기본 OFF.
3. 원본·변형·대조군 suite 동결 및 현행 baseline 실행.
4. L1 설명 가능한 국소 축약 + source-independent anchor 가설 구현.
5. 구조 후보 인덱스 파일럿, 원음 재검증, ablation.
6. holdout·반례·기존 검색 회귀·표시 검증 후 적용 여부 결정.
7. 화성 추정과 외부 Phrase layer 결합, R05–R09 고급 규칙 검증.
8. 다구간 순서/coverage 집계와 리포트 통합.

이번 변경은 연구 검토 및 일반 규칙 설계다. 새 100개 실행, 본격 Schenker 분석기, 점수 계수 학습, 새 인덱스 생성은 아직 하지 않았다.
