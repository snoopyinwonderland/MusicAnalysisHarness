# 배치 사이의 진행 후보 대비 — 구현·검증 기록

2026-10-03. 화성 분석 개발 기록이며 인수인계 문서가 아니다.
선행 [설계](2026-10-03-cross-batch-progression-contrast-plan.md)와
[전체 실제 replay](2026-10-03-fresh-replay-resource-preflight.md)를 이어간다.

## 이번 기능의 목적과 완료 범위

직전 단계에서 원 두 등록 구간의 8,050개 native/role 요청을 504개 배치에
저장했다. 이번에는 저장 배치가 다르더라도 같은 구간·조성 후보·원 성부
연결 가정 안에서 진행 후보들을 비교할 수 있는 기반을 구현한다.
저장 단위가 음악의 화음 경계나 후보 비교 범위를 결정하지 않게 하는 작업이다.

이번 단위는 새 saved-only admission과 비교 core, 작은 XML의 exact equivalence
검사, 실제 저장자료의 metadata admission까지다. 전체 corpus 대비 실행기는
아직 없으며 전체 1,652,640쌍·570개 block의 실제 대비는 **미실행**이다.
작은 테스트의 비교 실행과 실제 corpus의 비교 실행을 혼동하지 않는다.
기존 public 분석기/정책의 256요청 제한은 바꾸지 않는다.

음악적 support threshold나 교재 규칙을 새로 적용한 단계는 아니다.
동일한 근거를 더 큰 후보 집합에서도 정확하게 비교하는 계산 계약을 구현한
단계다. 화음/NCT/key/cadence의 최종 선택·정답률·화면 개선으로 승격하지 않는다.

## 파일과 책임

- `src/musicanote_harness/cross_batch_progression_admission.py`:
  phase29 저장자료의 생성 당시 입력/코드 SHA, 부모 목록, 원 요청/배치/terminal
  연결을 검증한다. 원 성부 producer나 후보 producer를 실행하지 않는다.
- `src/musicanote_harness/cross_batch_progression_contrast.py`:
  한 group의 source profile·역할 clause·union을 검증하고 immutable facet와
  공통 rational refinement를 만든다. 원 row pointer를 이용해 작은 block을
  비교하며 기존 pair 설명을 정확히 복원한다.
- `tests/test_cross_batch_progression_admission.py`:
  한도·생성 시점 계약·위조/누락/미완료·원순서 및 작은 genuine XML 저장 검증.
- `tests/test_cross_batch_progression_contrast.py`:
  기존 대비와의 exact equality·타이/재발음·철자 alias·유리수·null·block coverage.

이 파일들은 새 계층이다. 기존 parser/Core/XML/주석/분석기/생성기와 과거 산출물을
대규모 변경하거나 migration하지 않았다. 원본을 새 authority로 재발급하지 않는다.

개발 API는 `load_saved_plan → metadata_prepared/source_prepared →
iter_validated_completion_entries → finish_admission`과
`preflight_saved_group → prepare_saved_group → iter_blocks/compare_block →
materialize_pair`다. 앞의 iterator를 일부만 받은 자료로 원 group 전체 완료를
주장하지 않는다. Catalog export는 JSON 교환용 복사본이며 materializer의
검증 handle을 대체하지 않는다.

Metadata-only 확인 명령은 다음과 같다. 새 비교/출력/producer는 실행하지 않는다.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -B -m musicanote_harness.cross_batch_progression_admission --parent output/fresh-source-progression-evidence-2026-10-03-r1
```

## 데이터 흐름과 권한

```text
frozen phase29 archive
  → exact creation SHA / ordered original request admission
  → batch별 native·role·selector position join
  → 한 원 completion/key의 전체 entry inventory
  → source profile / clause / union intrinsic validation
  → immutable shared catalog + rational refinement
  → bounded pair blocks, not a winner
  → [별도 개발 예정] 저장/중단 ledger·전체 coverage terminal
```

Metadata admission은 모든 body 의미를 검증했다는 뜻이 아니다.
`finish_admission()`의 `all_indexed_batches_join_validated`는 모든 completion
iterator가 terminal 검증까지 소진했을 때만 참이다. 마지막 batch를 받아도
iterator를 일찍 닫으면 완료가 아니다. `all_saved_bodies_validated`는 admission에서
항상 거짓이며 profile/clause/union 검증은 비교 core의 책임이다.

두 모듈 모두 검증 결과를 소유한 handle과 공개 복사본을 구별한다.
외부 summary나 seal만 다시 만든 JSON은 검증 완료 권한이 아니다.
Core는 physical file SHA와 원 selector membership을 검증하는 loader가 아니므로
반드시 admission과 원 group의 전체 position ledger를 통과해야 한다.
Python 내부 변수에 대한 완전한 보안 격리를 주장하지 않으며 정상 public API에서
미검증/수정된 handle을 계산 자료로 받지 않는 계약이다.

빈 core group은 pair/task 0을 뜻한다. 그 자체로 등록 key/bundle의 빈 요청이라는
증거는 아니다. 그런 group의 원 key·completion·분모는 admission/향후 실행기가
외부 ledger에서 보존해야 하며, 누락이나 budget hold를 빈 group으로 바꾸지 않는다.

## 음악적으로 보존하는 일반 규칙

1. 같은 exact source/scope/lattice/key/bundle/**원 completion request** 안에서만
   비교한다. 같은 bundle이 나온 별개 원 요청도 합치지 않는다.
2. 다른 native origin이 같은 근음/구성음 signature를 가져도 provenance alias로
   보존한다. 같은 complete logical tuple의 중복과 signature alias는 다르다.
3. 원 음표 ID·철자·음가·full tie·attack·source-note closure와 `[start,end)`의
   유리수 좌표를 유지한다. 타이 continuation을 새 attack으로 계산하지 않는다.
4. 공통 refinement는 계산 좌표이며 새로운 화음 segmentation이 아니다.
   각 sound의 원 source-segment row index와 별도 bass-cell index를 보존한다.
5. Pair 복원에서 양쪽 **원 row index 쌍이 같은 경우만** 합친다. Category가
   같다는 이유로 원 cut을 지우지 않으며 제3후보의 cut이 다른 두 후보의 설명에
   새로운 cell로 남지 않게 한다.
6. 여섯 관측 category의 delta와 transfer는 Fraction 기반 음표-시간 계정이다.
   동시에 울리는 여러 음의 multiplicity를 유지하며 악곡 clock duration과 다르다.
7. Conditional explanation credit가 미상이면 credit delta도 `null`이다.
   여섯 관측 category 계정까지 미상으로 없애거나 미상을 0으로 바꾸지 않는다.
   계산된 0과 미계산·음악적 미판정·기술적 보류를 구분한다.
8. Candidate-only, transition-only, 두 조건 변경, partition 대비를 보존한다.
   실제 bass 관찰을 structural bass로 확정하지 않는다.
9. 설명량·구성음 수·cut 수·pair 승리 수로 winner를 자동 선택하지 않는다.
   `selected/rank/confidence/musical_outcome`은 미승격 상태다.

특정 음악 제목·마디·사용자 정답에 따른 분기나 특수 threshold는 추가하지 않았다.

## 사전 분모와 자원 경계

원 제출 분모를 그대로 유지한다.

| 범위 | entry/한 completion·key | group | 예정 pair | 예정 block |
|---|---:|---:|---:|---:|
| Sonata 등록 구간 | 463 | 10 | 1,069,530 | 360 |
| Quartet 등록 구간 | 342 | 10 | 583,110 | 210 |
| 합계 | 발생 8,050 | 20 | 1,652,640 | 570 |

이는 두 작품의 전곡이나 8,050곡이 아니라 **두 등록 구간/4원 요청**이다.
원 322문맥/1,013raw lanes·선택2/7·미실행320/1,006·등록 pool5·전체 후보 경로와
제안/미제안 경로의 선행 분모를 유지한다.

Admission 기본 cumulative decoded cap은 기존처럼 1GiB다. Catalog 1,024개,
origin 200,000개, source2·group128·completion별 entry4,096·batch2,048 상한을
명시한다. 한도를 넘으면 원 전체 요청 분모를 보존한 whole hold이며 유리한
prefix를 진행시키지 않는다. 한 번에 한 batch body를 읽되 이 cap은 누적 decode
한도이지 RSS 상한이 아니다. 기본 cap을 무조건 높여 full run을 허용하지 않는다.

Core는 count/pair/block 한도를 O(1)로 먼저 검사하고, 이미 초과하면 큰 body나
O(block²) task 목록을 만들지 않는다. 이때 세부 비용은 0이 아니라 `null`이다.
그 다음 source별 refinement/vector/work와 shared catalog의 보수적인 encoded
상계를 계산한다. Block size는 최대64, 한 block 최대4,096쌍이다.
Pair 및 block의 실제 encoded 한도 초과는 그 block 전체를 보류하고 prefix를
반환하지 않는다. 전체 output bytes와 final manifest reserve를 포함하는
**corpus 저장 사전 계획은 별도 실행기에서 추가해야 한다.**

Core preflight를 통과한 것이 full corpus의 CPU/RSS/저장 용량 admission을 뜻하지
않는다. 최대 group과 첫/max-cost block의 실제 계측이 다음 단계이며, 기존
900pair 시간에 비례해 전체 시간을 확정하지 않는다.

## 개발 중 발견한 문제와 교정

- **과거 생성 inventory와 현재 코드 혼동:** 기존 predecessor loader가 오늘의
  Python 파일을 glob하여 새 모듈까지 과거 inventory에 넣을 수 있었다.
  기존 코드를 바꾸거나 monkeypatch하지 않고 parent 생성 snapshot+원 replay
  4파일의 정확한 union을 검증하는 새 direct loader를 만들었다.
- **과거 부모 chain 누락/재정렬 위험:** 원 ordered ancestor inventory를 exact
  대조한다. 실제 부모 목록 6/7/7/148와 phase29 1,025파일을 보존한다.
- **mutable ledger의 거짓 완료:** 공개 dict의 완료 flag를 바꿔도 내부 완료가
  되지 않도록 owned handle/복사 export/iterator terminal 검증으로 분리했다.
- **한도 설정만 있고 검사 누락:** independent audit에서 catalog/origin cap의
  미적용을 발견했다. Intrinsic origin 검증 전에 whole count gate를 넣고 원
  `native_inventory`와도 exact 대조한다. 낮춘 cap의 반례를 추가했다.
- **봉인된 body라도 role 순서를 바꿀 수 있음:** 원 selector/native/role의
  ordinal을 exact zip 검증하고, 임시 genuine-XML fixture의 role 배열을 뒤집어
  재봉인·새 physical SHA를 만들더라도 거부하는 테스트를 추가했다.
- **검증하지 않은 core handle 위조:** 독립 검토에서 공개 객체를 직접 만들면
  완료 pair를 낼 수 있는 위험을 발견했다. 검증 factory만 내부 상태를 등록하고
  consumer가 소유 상태를 확인하도록 보완했다. Frozen container·handle/state
  인증, 공개 복사본과 내부 catalog의 분리, plain JSON만 허용하는 검사를 추가했다.
  Mutable Fraction cache는 builtin 정수 `(numerator,denominator)` tuple로 바꾸고
  계산할 때만 Fraction을 재구성한다. Python 자체의 악의적인 내부 코드 실행을
  격리하는 보안 경계라는 뜻은 아니다.
- **block마다 모든 task 재생성:** `tuple(iter_blocks())`로 task membership을
  확인하면 block size1에서 pair 수만큼의 목록을 매번 만드는 문제가 있었다.
  원 range·크기·digest의 O(1) 산술 검증으로 교정하고 전체 task scan을 금지하는
  반례를 추가했다. Pair 계산 시 Fraction 재구성의 비용도 사전 work에 포함한다.
- **이미 불가능한 byte 한도:** pair가 존재하는데 output cap이 0처럼 분명히
  부족하면 facet 계산 전에 whole group을 보류한다. 그 밖의 실제 positive
  encoded byte 초과는 해당 block의 whole hold이며 유리한 prefix를 내지 않는다.
- **초기 fixture 기대 오류:** 첫 slot의 C-triad 대안 부재, zero-budget의 closed-form
  geometry가 미상이 된다는 오해, `bad_attack`을 graph withholding과 혼동한
  기대를 교정했다. 실제 grace-point bundle withholding으로 null을 검증한다.
  Producer/support 규칙을 테스트에 맞춰 바꾸지 않았다.

## 검사와 실제 저장자료 admission

중간 같은 suite의 재실행은 새로운 테스트 수에 합산하지 않는다.

- Admission 최종16개/39.186초 PASS: pure6개와 작은 genuine tied XML에서
  생성된 native/role packet을 사용하는 storage10개. Ancestor admission은 fixture
  mock이며 full 역사 chain은 아래 실제 저장자료의 read-only 검사로 구별한다.
- Core 최종 고정 버전25개/40.820초 PASS, AST2개 PASS다. Genuine XML/native
  후보·rational/partition/transition·타이/재발음·alias·제3후보 cut에서 기존
  `_pair`와 exact equality를 검증했다. Pure3개와 genuine fixture 기반22개다.
  초기21개/37.550초·root 동일21개/39.157초, 중간23개/38.025초와25개 재실행을
  최종25개에 더하지 않는다. Root 고정 SHA 재검사 결과는 최종 QA에 기록한다.
- Independent arithmetic/refinement 대조: pure3개 PASS와 무작위 유리수 partition
  2,000세트의 pair6,000개를 원 pair union과 exact 대조했다. 실제 corpus나 음악
  정답률 검사가 아니며 unit test 수에 더하지 않는다.
- 실제 metadata admission 최종52.8299268초/exit0: 34파일·438,689,440decoded
  bytes, 원4completion·8,050entry·20group·1,652,640예정pair·570예정block이다.
  source catalog/origin cap 교정 후 direct historical closure를 재검수했다.
  모든 입력/코드 SHA와 원1,025output 및 ordered6/7/7/148 inventory가 유지됐다.
  이 실행의 validated body batch/entry·computed pair는 모두0이고,
  `all_indexed_batches_join_validated/all_saved_bodies_validated`는 거짓이다.
  Producer·쓰기·선택·음악 정확도/Gold/생성 준비 flags도 모두 거짓이다.
  중간53.5224656초 재검사 등 같은 metadata 재실행을 새로운 성과로 합산하지 않는다.

## 운영 및 보존 상태

새 corpus 대비/저장·정책·winner·확률 보정·학습/Gold·악보 UI·구조 분석·편곡/작곡
승격은 **미실행**이다. 이번 turn의 Git 변경/commit/push는 요청되지 않았다.
기존 별개 tracked5파일의 사용자 수정을 보존한다. 새 개발 문서는 화성 폴더에만
추가하고 기존 구조 분석 기록과 인수인계 문서는 이번에 수정하지 않는다.

동결 기준은 직전 원 입력/코드 union4,788 SHA, phase29 정확1,025파일,
원 parent6/7/7/148 목록과 기존 core/runner/test4파일·report/index/plan3파일이다.
최종 root QA: 고정 SHA의 core25개/38.981초·admission16개/39.186초 PASS다.
신규 서로 다른 검사41개이며 같은 suite 재검사를 중복 합산하지 않는다.
네 새 파일 AST PASS, 기존 core/runner/tests4와 원 report/index/plan3의 총7
동결 SHA 변경0을 재확인했다. 세 화성 개발 MD의 strict UTF-8/text 및146개
로컬 링크 검사도 오류0이다. Read-only `git diff --check`는 exit0이며 기존
별개 tracked5파일의 LF→CRLF 경고/사용자 수정은 그대로 유지했다.
실제 metadata admission에서 보호4,788SHA와 원 inventory의 전후 일치도
확인했다. 이번 검사/기록이 과거 전체 actual replay를 다시 실행한 것은 아니다.

최종 새 코드/테스트 동결 SHA256:

```text
cross_batch_progression_admission.py
5e8f231ac68e1856f917fb4f84e50b2795b94138e4a67d279b6cb1188f851c68
test_cross_batch_progression_admission.py
a21b1d68b31d7e6be76e98be7507d159e0d7a6496a8ddf1f33f4d2742765cf04
cross_batch_progression_contrast.py
5e8a876f885cb5663948e55d5aa23f458defb670b0eee5239cd95f2570f8bd88
test_cross_batch_progression_contrast.py
9abb7810f2523ee498daa5868042bb195d946a0f50596fa3b8e0f7bb7d4acc02
```

독립 최종 검토에서 admission의 count cap·whole denominator·original body
join과 core의 exact refinement/nullable credit/alias·owned state·bounded task
계약에 추가 차단 결함은 발견하지 않았다. 검토는 실제 corpus 비교·음악적
정답률·전체 output 저장 예약을 포함하지 않는다.

## 다음 큰 단계와 완료 조건

1. 저장 실행기에 원 group/selector/block/pair coverage ledger, exclusive write,
   입력과 creation inventory 보호, 누락/중단 complement, output/manifest bytes
   예약을 구현한다. 압축 catalog는 새 생성 계약이며 기존 저장을 바꾸지 않는다.
2. 작은 synthetic/mock storage에서 중단·partial write·누락/중복 block·held-empty·
   known-zero와 미상·변조 반례를 검증한다. Shared catalog 재로드도 원 physical
   SHA/원 membership을 재검증하며 summary를 권한으로 받지 않는다.
3. 실제 자료의 첫/max-size group을 결과와 무관하게 선정해 admission·facet·
   encoded bytes/RSS·첫/max-cost block 비용을 측정한다. 원 whole denominator를
   유지하고 부족한 비용은 미상으로 남긴다.
4. 예산을 확인한 뒤 전체 20group/570task/1,652,640pair를 실행하고 exact coverage와
   terminal을 독립 검수한다. 현재의 두 등록 구간을 전곡/다양한 음악 평가로
   확대하지 않는다.
5. 그 뒤 전체 scope의 제안·보류 정책과 별도 음악적 검수/악보 표시를 진행한다.
   Candidate 비교 완료와 최종 자동 화성 분석 완료는 다른 milestone이다.

화성 후보와 비화성음 근거를 같은 조건에서 설명할 수 있는 기반이지만, 이것만으로
분산화음의 정답이나 편곡 품질을 보장하지 않는다. 최종 기능/역할/질감의 해석과
구조·작곡·편곡 연결은 [장기 로드맵](../MUSICAL_SEMANTICS_AND_GENERATION_ROADMAP.md)에서
별도 완료 기준을 유지한다.
