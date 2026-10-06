# 여러 작품·편성으로 확대하는 화성 검증

단계: HARM-DEV-20260930-24. 화성 분석 개발 문서이며 인수인계 문서와 별도로 관리한다.

## 목적과 변경 범위

사용자 요청은 가능한 많은 실제 음악과, 화성 주석이 있는 교향곡·큰 편성을 활용하는 것이다. 직전 최신 실험의 실제 대상은 3악장/3가족이었다. 코드 테스트 수나 한 구간의 후보 조합 수를 작품 수로 세지 않고 **새 작품에서 실제 엔진을 실행**한다.

이번 변경은 일반적인 cohort/관측 계획/실행기와 별도 관현악 준비 감사다. 특정 작품/마디의 정답을 분석 조건에 넣지 않는다. Canonical Core·기존 parser·원주석·dataset manifest/split·운영5173·구조 분석·화면·외부 API·학습 자격은 변경하지 않는다.

## 1. 기존 정책을 지키는 실행 cohort

입력은 `output/dcml-batch-repeat-v2-2026-09-24/prepared_tracks.jsonl`(392개)와 고정된 `output/harmony-dataset-manifest-2026-09-25.json`(43개)이다. **score와annotation의 SHA256이 둘 다 같은 유일한 항목**에서만 기존 정책을 가져온다. corpus/collection/score stem/score_id/ir_document_id도 대조한다.

family·score hash·annotation hash의 split 충돌, 미확인 identity/rights, holdout, quarantine을 차단한다. `internal_research_use`와 `alignment_eligible`은 실제 boolean `true`만 허용한다. manifest가 없거나 다른 판본/주석 계보인 자료를 기존 train으로 묵시적으로 편입하지 않는다.

이번 실행 가능 범위는 **19개 작품 가족의33개 악장/package**다. 같은 작품의 여러 악장은 별도의 작품 가족 수로 중복 집계하지 않는다.

| 자료 | 악장/package |
|---|---:|
| 베토벤 현악4중주 | 3 |
| 베토벤 피아노 소나타 | 5 |
| 쇼팽 마주르카 | 9 |
| 코렐리 트리오 소나타 | 10 |
| 모차르트 피아노 소나타 | 6 |

392개 전체 inventory를 남긴다. blocker는 중복 가능한 이유 집계다: 보호holdout7, quarantine/정렬 부적격59, manifest의 유일한 hash pair 미확인349. non-holdout 기존36개 중 quarantine3(`n01op18-1_02`, `n01op18-1_03`, `01-3`)도 삭제하지 않는다. 정렬 적격333/complete 소나타37이라는 이전 집계가 split·권한·사람 검수 승인을 뜻하지 않는다.

## 2. 참조라벨 없는 전곡 관측 계획

- 원 IR의 전곡 범위와 모든 명시적 part/voice에서 연속3attack onset group을 먼저 열거한다.
- 각 lane별 전체 창 목록의 안쪽 균등 quantile2개를 선택한다. 정답 화음·음형·계산 통과 여부를 보고 좋은 구간을 고르지 않는다.
- lane에 따라 전곡 일부에서만 나타나는 보조 성부/장식음을 포함할 수 있다. 각 lane의 available window 수와 원 plan index를 보존한다. 모든 창을 계산했다거나 시간 균등한 독립 표본이라고 주장하지 않는다.
- 고정된 창이 grace/긴 지속/박자 변화/반복 장벽/계산 한도에 걸리면 그 결과를 그대로 저장한다. 통과하는 다른 창으로 교체하지 않는다.
- 화음 후보와 membership에는 해당 구간의 **전체 part sounding events**를 유지한다. 샘플 lane은 제한된 NCT geometry의 출발점이며 전체 성부의 추론이 아니다.
- 33개 원IR·원악보/주석hash·preparation report를 확인하고 schema를 재검증한 후 IR고정본과 전체`frozen-plan.json`을 저장한다. 모든 package의 계획 고정이 끝나기 전에는 화성 후보 계산을 하지 않는다.

주석 파일은 identity/hash 확인에만 사용한다. `source_harmony_context.json`과 주석의 화음 라벨을 분석기에 공급하지 않는다. schema 검증/입력IR 내부 원음 보존은 **원XML과 독립적인 음악적 정확성 검사**가 아니다. 이전 import의 source-note mapping 미해결 상태를 정답 승인으로 바꾸지 않는다.

## 3. 실제 실행 pipeline와 보류

```text
전체 IR → 고정된 연속 attack 창
        → continuous.analyze
        → segment_contrast.build
        → progression_context.build
        → candidate_relation_survey.run(temporal=True)
        → hold_change_context.run
```

기존 엔진의 실제 gate를 통과한다. relation survey가 한도에 걸리면 마지막 단계도 같은 보류를 받으며, 가짜`ready`를 넣어 우회하지 않는다. 전체IR의 사건 ID/pitch/span/source_note_ids를 baseline과 lattice에서 다시 대조한다. 동일 sound의 짧은 유리한 부분만으로 보조음을 확정하지 않는다. 화음 유지/변화에서 원음·유리수 시간 셀·부분 성부 가정을 공유한다.

실행기의 full stage artifact는 재현 가능한 `.json.gz`로 저장한다. 저장 압축은 분석 시간축/스키마의 의미를 바꾸지 않는다. package별 진행 파일은 `complete=false`; 최종 결과만 `report.json`의`complete=true`다. 예외는 표본별로 기록하고 나머지 자료를 계속 검사한다. 입력/code/계획/IR고정본hash가 변하면 전체 실행 성공으로 보고하지 않는다.

이 실행은 기존train/dev의 **비맹검 내부 개발 호환성 검사**다. 원자료 정답에 대한 정확도·독립gold·사람검수·새split·학습 데이터의 승격은 아니다.

## 4. 관현악 주석과 총보를 분리하는 준비 감사

실제 사람이 만든 RomanText와 별도로 있는 총보를 발견한 작품 가족은 다음3개다.

| 작품 | 실제 총보 편성 | 기존 같은 폴더 악보 |
|---|---:|---|
| 하이든 교향곡104번1악장 | 18parts | 1part Reduced Score |
| 브람스 독일레퀴엠Op45 1악장 | 22parts | 총보 remote reference |
| 바흐 B단조미사BWV232 Crucifixus | 10parts | 1part Reduction |

Crucifixus의 해당 총보는 이 자료에서 movement14다. `09b`는 다른 악장이다. Choco에 같은 분석이 재수록돼 있어도 독립 작품/독립 주석 근거로 중복 세지 않는다. Hauptstimme의 주제 주석은 로마자 화성 gold가 아니다. 베토벤/브람스 심포니 총보만 있다고 사람 화성 주석이 있는 것으로 간주하지 않는다.

사람`analysis.txt`, 자동`.rntxt`, 대안`analysis_DT.txt`는 출처/해석 계보를 따로 보존한다. 관현악3가족은 기존43개manifest에 없으므로 **unassigned exploratory readiness**로만 검사한다. user의 로컬 준비 감사 요청이 독립 평가·외부전송·학습·재배포 권한을 새로 승인한 것은 아니다.

현재 formal IR adapter는 written pitch를 concert pitch에 복사하며 `concert_transposition`을 unavailable로 명시한다. 따라서 관현악 총보의 nonzero/잘못된 `<transpose>`가 있으면, 다른 악기의 기보 음을 그대로 수직 화음으로 합쳐 분석하지 않는다. 조옮김의 존재와 실제 part/measure/source refs를 남기고 화성 사용을 보류한다. 축약보 좌표와 맞는 것을 총보의 harmonic readiness로 바꾸지 않는다.

RomanText 좌표 compatibility와 축약보/총보 measure grid를 실제 검사하지만, 마디 번호/offset의 일치만으로 판본 동일성·repeat 의미·전음표 대응·concert pitch·화성 정답을 검증했다는 뜻은 아니다.

## 5. 실행·최종 결과

라벨 없는 전체 관측 목록은36,820창이다. lane별2개 선정 결과는322창이다. r1/r2의 selected sample 객체 전체를 대조해 동일함을 확인했다. 나머지36,498창까지 모두 화성 계산한 것이 아니다.

관현악 준비 감사의 최종 출력은 `output/harmony-orchestral-readiness-2026-09-30-r2/report.json`이다.

| 작품 | 실제 총보 마디 | 사람 주석 | 정확 좌표 | 모호 좌표 |
|---|---:|---:|---:|---:|
| 하이든104/1 | 295 | 449 | 408 | 41 |
| 브람스Op45/1 | 158 | 394 | 394 | 0 |
| 바흐Crucifixus | 53 | 124 | 124 | 0 |
| 합계 | — | 967 | 926 | 41 |

하이든 축약보는294마디이고 총보는295마디다. 첫17마디의 박자 표기가 축약보/주석2/2 대 총보4/4이므로, 물리quarter 좌표가 비슷해 보여도 엄격한 beat mapping41개는 보류한다. 브람스는 XML22parts가 music21에서23parts로 확장된 것이며 두 수치를 구별한다. 바흐의 축약보/총보 시간 격자는 일치하지만 음표/판본/화성 의미의 동일성 승인이 아니다.

하이든7개와 브람스3개의 nonzero source transpose 선언(클라리넷·호른·트럼펫·콘트라베이스 등)을 발견했다. 해당2작품의 full-score harmonic use를 차단한다. 바흐는 technical coordinate ready이나 세 작품 모두 정책·판본 미검증으로 최종 harmonic use/gold0다. 현재 과제로는 총보 주석 연결 준비를 **실제로 감사**한 것이고, 관현악 화성 예측을 완료한 것이 아니다.

관현악r1에서는 MXL container의 optional`media-type`이 없다는 이유로 source metadata가 보류됐다. 유일한rootfile·안전한archive path·score-partwise를 확인하는 일반 처리로 보강해r2를 새로 실행했다. r1과r2 및입력hash를 보존했다.

확대 계산r1은6package/56기록까지 진행한 최초 진단이다: ready36, baseline 보류6, pair-budget10, edge-budget1, execution error3. 증6후보 표시 예외를 재현한 후 중단했으므로 **완료 결과가 아니다**. 이미 생성됐지만 package checkpoint에 아직 반영되지 않은 artifact도 초기 폴더에 남아 있으며, 최종집계로 더하지 않는다.

공통 표시 함수`harmony_catalog_resolution_trial.label()`은 alternative index가 있어도`root_spelling=None`일 수 있음을 처리하지 못했다. 실제 quartet의`[626,628)` 창에서 정상적인It/Ger/Fr/Ger43 후보가 이 계약을 사용한다. 중앙 helper의 root-present guard와 기존 tonal/raw fallback으로 수정했다. 근음/구성음/원음표를 생성하거나 후보를 제거하지 않았다. 이는 작품 전용 규칙이나 음악적 abstention 추가가 아니다.

최신 확대 실행기는0.1.1이고, 독립package2worker로r2를 재실행했다. 같은322창을 보존하고 계산한도는 높이지 않았다. 최종 `output/harmony-breadth-trial-2026-09-30-r2/report.json`은 `complete=true`, exit0이다.

| 자료 | 실제 실행 창 | 끝단계ready | pair예산 보류 | 앞단계 보류 | interval예산 보류 |
|---|---:|---:|---:|---:|---:|
| 베토벤 현악4중주 | 24 | 19 | 4 | 1 | 0 |
| 베토벤 소나타 | 54 | 40 | 8 | 5 | 1 |
| 쇼팽 마주르카 | 102 | 67 | 15 | 18 | 2 |
| 코렐리 | 80 | 67 | 13 | 0 | 0 |
| 모차르트 소나타 | 62 | 50 | 8 | 4 | 0 |
| 합계 | 322 | 243 | 48 | 28 | 3 |

**ready는 이 창에서 계약상 계산을 수행했다는 뜻이며 화성이 맞았다는 뜻이 아니다.** relation pair가 없거나 반복 최저음 chain이 없어도 조사 자체가ready일 수 있다. 끝단계243과보류79를 정답/오답으로 변환하지 않는다. 실행오류0/preflight오류0, 전체33고정IR의schema를재검증했다. 322창은 전곡완전분석이나322독립음악이 아니다. 기존3pilot가족/3악장은 이33package에 포함되므로 추가30package/16가족으로 계산한다.

continuous 계산가능294창에서 해당범위의모든part event ID/pitch/span/source_note_ids와note-time 보존을 확인했다. lattice291/interval예산3,relation243/pair예산48이다. 앞단계28보류는sample/grace범위9,context10,voice열거6,조건×assignment예산3이다. 전체원음은 삭제하지 않는다.

실제relation질의15,195개와 hold/change조건부비교66개를 수행했다. 중복될 수 있는 후보별질의·성부가정별비교이며, 작품/정답 수가 아니다. 기본raw/contrast/lattice/relations/hold_change전체결과는322개의gzipartifact와원본IR고정본으로재현가능하다. 계산구간의elapsed합과독립package병렬wall-time를혼동하지않는다. 본실행계산구간wall-time835.459초는preflight시간제외이며동시테스트/profile가있어성능benchmark로보지않는다.

최종실행의source/code/plan/원본IR/IR고정본hash감사는 `inputs_unchanged=true`, changed paths0이다. 미완료`progress.json`은forensic진행용이며 최종정본은완료report다.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m musicanote_harness.harmony_breadth_trial --prepared-tracks output/dcml-batch-repeat-v2-2026-09-24/prepared_tracks.jsonl --manifest output/harmony-dataset-manifest-2026-09-25.json --output output/harmony-breadth-trial-2026-09-30-r2 --samples-per-lane 2 --workers 2
.venv/Scripts/python.exe -m musicanote_harness.harmony_orchestral_readiness --corpus-root 'K:/MusicSearch/data/classical-corpora' --dataset-manifest output/harmony-dataset-manifest-2026-09-25.json --output output/harmony-orchestral-readiness-2026-09-30-r2
```

## 6. 검증·미해결·다음

독립 코드 검토에서 XML숫자 문자열을 rational-dict용 함수에 넘기는 결함, 엄격boolean이 아닌 적격 검사, 종료 시 code/plan/frozenIRhash 검사 누락을 발견해 실행 전에 보강했다. analyzer의 in-memory IR변경을 감지하고 창별 복사본으로 다음 표본의 오염을 방지한다.

위 재현 명령은 기존 출력을 덮어쓰지 않는다. 재실행 시 새로운 output 폴더를 지정한다.

신규 테스트: cohort/계획/pipeline/변조/복사/worker29, rootless label5, 관현악19. 실제2worker는 임시2악보/4구간을 같은 pipeline으로 검사한다. display-only 수정의 후보·member·null root·IR불변과 모든 네 증6가족 보존을 검사한다.

전체 Python1,899테스트/33.924초 통과. 기존 engraving layout warning1건은 유지한다. `git diff --check` 및 새 코드/테스트/doc의 trailing-whitespace 검사 통과(기존 파일의CRLFwarning만).

### 실제 계산 비용의 원인과 다음 최적화

완료한r2 quartet `n03op18-3_02`의 `cont_430a54b0461da51341d1`을 라벨 없이 한 번 별도로 profile했다. 입력IR에는2,847sounds가 있고 실제 창에는11sounds가 있다. 관계 질의209개는 정확한context span5종류(67/52/40/25/25중복)에 속하지만 전체 악보의성부`prepare`를209번 반복했다. 원 실행22.23초 대 profile61.775초이며 profiler overhead/다른실행과의동시CPU사용이 있어 이 둘을속도향상 지표로쓰지않는다. profile에서relation survey53.453초/voice_links43.927초이고 `validate_ir`는 약0.15초다.

다음 성능 작업은 고정IR의 source mapping/Fraction/lane정렬을 한 번 준비하고 정확한유리수span별 **기하 정보만** 재사용하는 것이다. 후보209개와 원음·구간밖overlap/successor검사·보류·순서를 모두 유지한다. 캐시는 IRhash와코드version을키로삼고, 현재frozen결과의 전체JSON 의미/순서가 같아야 한다. 아직 이 캐시를 구현하거나 실행한 것은 아니다.

관현악 사용은 written/concert정규화, 하이든2/2↔4/4/추가마디의 source기반대조, 실제판본/반복/주석계보와 내부정책 검토 이후에 같은pipeline으로 넣는다. 브람스의22XMLparts→23parsedparts 매핑도 확인해야 한다. 주석대조·사람검수·독립평가 자격은 별도이며, 여러 후보의관계검사가통과했다고 최종기능/화음/종지를 확정하지 않는다.

이번 단계는 관측 범위와 실패 유형을 넓히는 것이며 후보 수/기술 검사 통과 수를 정확도로 바꾸지 않는다. 원주석 라벨과의 후행 의미 대조·음악적 검수·독립 평가·정답률은 아직 측정하지 않았다.

### 최종 독립 재검사

실행 담당과 별도의 읽기 전용 검토에서 다음을 다시 확인했다. 이 검사는 저장 결과의 재현성과 내부 계약을 확인한 것이며 새로운 화성 계산이나 음악적 정답 승인 절차가 아니다.

- 322개 artifact의 byte SHA256, gzip 해제, JSON 파싱과 고정 sample/index가 모두 일치했다. 33개 악보의 참조 라벨 없는 geometry 계획을 재생성해 고정 계획과 동일함을 확인했다.
- 전역 입력 3개, 코드 243개, 원악보·주석 66개, preparation report 33개, 원본 IR 33개, 고정 IR 33개의 현재 해시가 실행 계약과 일치했다. 관현악 r2의 입력 14개·코드 4개도 일치했다.
- 전체 part의 event/note-time 보존을 baseline 294개와 lattice 291개에서 독립 대조했다. 이는 입력 IR 내부의 보존 검사이며 원XML의 모든 음악 정보와 독립적으로 동등하다는 인증은 아니다.
- 모든 artifact에서 정답 라벨 사용·정확도 측정·기능/종지/전조 확정·운영 변경 플래그가 false다. `selected`는 null 또는 false이며 승자/선택된 assignment는 null이다.

실제 후보 관계 15,195개에서 직접 해결 검사의 상태는 아래와 같다. 서로 겹칠 수 있는 후보별 질의이므로 사건/작품/정답 수로 해석하지 않는다.

| 직접 해결 질의 상태 | 수 |
|---|---:|
| 전제 부족 | 13,249 |
| 호환 가능한 성부 연결 witness 존재 | 578 |
| 호환 가능한 witness 없음 | 288 |
| 기존 gate에서 보류 | 916 |
| nonpositive duration 미지원 | 164 |

같은 관계 목록의 별도 시간 경로 검사에서는 **조건부 가능성 16개**(V7 9, V 4, vii 3), identity 전제 보류 14,030개, 공동 witness 없음 69개, 기존 gate 보류 916개였다. nonpositive duration 164개는 명시적 미지원 상태를 유지하며 temporal query 자체가 없으므로 실제 시간 증거 검사에 포함했다고 주장하지 않는다. witness는 해당 후보 관계를 가정했을 때 같은 명시적 part/voice 안의 호환 가능한 **부분 대응 assignment가 하나 이상 존재**한다는 뜻이다. 실제 성부의 확정 연결이나 전체 대위 진행의 검증이 아니다. 직접 witness 578개나 시간 경로 가능성 16개는 선택된 화음/최종 기능/독립 양성 정답이 아니다. 후속 단계에서 실제 음표·경쟁 후보·반례를 함께 점검할 새로운 개발 진단 근거다.

hold/change 비교는 감사 가능한 3개 분할에서 공통 assignment 비교 66개, 동일 화음 복제 불변 검사 66개, 빈 assignment 비교 33개를 수행했다. 세 분할의 여러 조건부 비교이며 66개 독립 음악 사례가 아니다. 최종 322개 artifact의 논리 JSON 집계 SHA256은 `2e844dbfd15a1b093480c07723b363c453fa7fd3ef18db432b89f63f72fb0039`다.
