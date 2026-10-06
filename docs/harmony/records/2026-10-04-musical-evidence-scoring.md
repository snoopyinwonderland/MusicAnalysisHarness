# J2d — 음악적 근거를 실제 공동 선택 점수에 연결

기록 ID: **HARM-DEV-20261004-52** · 2026-10-04. [직전 J2c](2026-10-04-time-boundary-margin-learning.md)에서 발견한 동일 특징 충돌과 raw 분할 편향에 대응한다. 새 weight 학습만 반복하지 않고, 관측 정보를 실제 선택 점수에 연결하는 큰 단위다. 화성 개발 문서이며 인수인계 문서와 별도로 관리한다.

## 실행 전 고정한 범위

동일33악보/19작품군/322문맥, 원 후보망·철자·raw6segment cap과 기존 보류를 유지한다. 원XML/Core/주석, J2a~J2c 코드·예측·권한·운영 화면을 변경하지 않는다. 새 후보를 gold로 삽입하지 않는다. 두 고정 arm을 모두 보고하며 새 학습/Dev tuning/arm 선택/운영 승격은 하지 않는다.

- `harmonic_run_only`: 동일 signature의 raw edge들을 하나의 음악적 run으로 평가한다. 기존 가중치의 `segment_count`만 `harmonic_run_count`로 대체하고 아래 새 음악적 근거의 가중치는 사용하지 않는다.
- `source_evidence_music`: 같은 run 표현에 조표·박절·최저 지속음·실제 동일 성부의 짧은 순차 진행 근거를 함께 추가한다. 개별 근거의 효과를 분리하는 추가 ablation은 아직 아니다.

둘 사이에서 음악적 근거 묶음의 효과를 분리한다. 이전 J2a와는 run 표현과 점수 재료가 모두 달라지므로 특정 규칙 하나의 성과라고 주장하지 않는다. 시간·점수는 Fraction이며 confidence=null이다.

## 1. 구간 분할이 점수를 흔들지 않게 하는 방법

원 후보의 signature는 **근음 철자 + 전체 구성음 철자 집합**이다. 음고 class만 같다고 합치지 않는다. 서로 다른 기능/전위가 아직 signature에 표현되지 않으므로 이 동등성은 현재 root+members 평가 범위에 한정한다.

인접 edge가 같은 signature이면 음표와 시간 구간의 **합집합**으로 missing member/root, 비구성음 노출, 복잡도와 새 음악적 근거를 재계산한다. 분산형에서 앞 조각에는 근음, 뒤 조각에는3음/5음만 있는 경우에도 내부 cut을 추가했다는 이유로 누락 비용이 달라지지 않는다. 실제 음을 삭제하거나 구성음을 발명하지 않는다.

```text
DAG 상태 = 현재 endpoint + raw edge 수 + 현재 run 시작점 + signature
새 signature: 이전 run을 완료하고 새 run 비용 + 전이 비용 추가
같은 signature: 현재 run 비용을 더 긴 합집합 run 비용으로 교체
```

긴 하나의 edge가 원 후보망에 없어도 짧은 동일-signature edge들의 완전 경로를 허용한다. raw edge 수는 여전히 원6segment 제한을 소비한다. 후보 삭제나 cap 우회가 아니다. Candidate blocker는 각 edge의 기존 노출 비용을 계속 더하므로 다른 정상 후보와 합친다고 사라지지 않는다. **분할 불변성은 blocker 노출이 같은 경로의 음악적 run 항목에 적용**한다.

endpoint/raw count만으로는 앞으로 같은 signature가 이어질 때의 합집합 점수가 정해지지 않는다. run 시작점을 상태에 추가해 exact 탐색을 유지한다. 2M transition 초과 시 근사 winner를 내지 않고 보류한다. 새 학습 시 raw count를 음수 보상으로 쓰지 않도록 이 feature version을 구별한다.

## 2. 실제로 점수에 연결한 음악적 근거

| 특징 | 계산 | 실행 전 고정 weight | 뜻하지 않는 것 |
|---|---|---:|---|
| `key_signature_foreign_member` | 해당 시간 조표의 letter/alter와 후보 구성음의 차이 비율, 시간 적분 | +1/10 | global/local key, Secondary/전조 판정 |
| `metric_nonmember_exposure` | 비구성음 지속시간 × 원 attack 박절 강도 / 문맥 총 note-time | +1/4 | 강박음은 반드시 chord tone이라는 확정 |
| `lowest_nonmember_exposure` | 각 sounding cell의 실제 최저 음이 비구성음인 시간 / 문맥 길이 | +1/4 | structural bass 또는 확정 전위 |
| `conditional_step_ornament_exposure` | 아래 엄격한 경과/보조 후보의 실제 비구성음 노출 | −1/2 | NCT 확정·음 삭제·구성음 면제 |

기존 raw nonmember 비용 weight1을 그대로 둔다. 마지막 특징은 최대 그 실제 노출의1/2만 보조 bonus로 반영하고 다른 강박/베이스 비용은 남긴다. 저장된 낙관 NCT 상계나 다른 assignment에서 가져온 witness를 더하지 않는다. 동일 run에서 양립하는 실제 원음표3개의 근거만 쓴다.

### 조표와 박절

- 조표는 관찰이다. `mode_hint`나 source annotation의 local key를 사용하지 않는다. fifths−7~7 외/동시 충돌 조표는 unknown이다. 조표가 바뀌는 구간은 정확한 유리수 시간으로 적분한다. minor leading tone·borrowed/applied chord도 이 soft prior에 비용을 받을 수 있으며 금지하지 않는다.
- 박절은 마디 시작2, beat grid1, grid 밖1/2의 제한적 관측 가중치다. 6/8·9/8·12/8은 점4분음표 단위, 그 외는 분모 단위를 쓴다. 연주 악센트/하이퍼미터는 판단하지 않는다. 복합/변박·pickup의 강도 해석에는 추가 검증이 필요하다.
- 최저 pitch는 onset마다 하나를 뽑지 않고 attack/release가 바뀌는 cell마다 지속음을 모두 살핀다. 같은 최저음의 철자가 여러 개면 그 관측을 모두 보존한다. pitch 미지원은 unknown이다.

### 준비·해결이 실제 연결되는 경과/보조 후보

기존 `prepare_voice_geometry`와 `spelled_height`를 재사용한다. 범위는 아직 polyphonic voice matching 전체가 아니라 **명시 part/voice에 하나씩 이어지는 음**이다.

1. Sound의 모든 원 note ID가 존재하고 같은 명시 part/voice이며, concert spelling/MIDI가 일관돼야 한다.
2. 원 note의 onset·duration이 gap/overlap 없이 sound 전체 span을 재현하고 최초 note가 attack이어야 한다. 타이 chain/source clock 불일치는 그 성부 근거만 보류한다.
3. 준비음→현재음→해결음이 실제로 contiguous해야 하며3음 중 어느 음도 같은 voice의 다른 sounding 음과 겹치지 않아야 한다. 가장 가까운 pitch로 polyphonic chain을 추정하지 않는다.
4. 준비·해결음은 해당 후보 run의 철자 구성음, 가운데음은 비구성음이다.3음의 전체 sounding extent가 그 run 안에 있어야 한다.
5. 가운데음이 기준 beat의1/2 이내이며 강도1 이하, 양쪽 diatonic step이±1이고 반음 거리1~2여야 한다. 같은 철자 pitch로 돌아오면 neighbor-like, 같은 방향이면 passing-like다.
6. 모든 사례는 conditional이고 `confirmed_nct=false`, `membership_exempted=false`다. 연결 근거가 없으면 NCT가 없다는 반증으로 쓰지 않는다. Polyphonic/불명확 타이/더 긴 지연·전타·계류·이중 보조는 후속 범위다.

명시 IR voice는 대위 성부의 확정 인증이 아니다. 현재 source-clock/철자 gate를 통과한 직접 연결의 제한적 geometry만 이용하며 곡 전체 NCT 분석 완료라 하지 않는다. 가장 낮은 음의 역할 역시 pedal/structural bass와 구별한다.

## 3. 전곡 원자료와 문맥의 연결

새 입력은 직전322문맥이 사용했던 **동결 full IR**다. 원 package를 새 parser로 읽거나 최신 파일로 교체하지 않는다. 기존 integration report의 physical SHA→명시 measure revision sidecar→pinned parent/candidate IR을 확인하고, working IR content hash/ID와 bundle의 hash/ID가 일치해야 한다. 원XML bytes/SHA도 확인한다.

full IR의 extension/기존 harmonic labels/곡 제목/`mode_hint`는 scoring에 사용하지 않는다. 전곡 identity/음표·마디 Core만 읽고 평가 주석은 두 arm의 선택을 끝낸 뒤 evaluator에 전달한다. 전곡 IR을 읽는 것은322개 문맥을 전곡 정확도로 승격시키는 일이 아니다.

첫 실제 smoke에서 lattice event가 문맥 오른쪽 끝을 넘어 원 sound의 전체 span을 보존하고 있음을 확인했다. 새 binding의 처음 가정인 clipped extent 검사를 고쳐 **원 전체 span**과 일치시키고, 비용 계산 때만 run과의 교집합을 쓴다. 이 수정은 원 음가를 자르는 변경이 아니다. 해당 회귀 검사를 추가했다.

## 4. 구현·검증 상태

- [별도 scorer/decoder](../../../src/musicanote_harness/harmony_evidence_scoring.py), [동결 비교 실행기](../../../src/musicanote_harness/harmony_evidence_scoring_trial.py).
- [음악적/탐색 검사](../../../tests/test_harmony_evidence_scoring.py), [physical runner 검사](../../../tests/test_harmony_evidence_scoring_trial.py).
- 최초 신규23+기존109=132검사 통과. 이후 source extent·조표 변화/충돌·원 octave·microtone/unknown·쉼 gap·입력 불변·XML physical guard를 추가하여 신규32검사 통과했다. 최종 관련 회귀 결과는 실제 실행 뒤 기록한다. Physical 테스트의 상위 receipts는 합성이고 corpus 실험과 구별한다.
- 작은 DAG의 모든 완전 경로를 열거해 exact 최소 점수와 tie-break가 일치함을 확인한다. Whole edge와 같은 signature의 여러 edge가 동일 score인지, whole edge 없는 원 경로도 유지되는지 확인한다.

최종 **신규35+기존109=144검사/1.409초**와Python4파일 AST가 통과했다. Triplet grid의 exact score, 정상 tie 준비음과 cross-voice tie 보류, cache cold/reuse의 동일 결과도 확인했다. 기존 파일5개의 LF→CRLF 예고 외 `git diff --check` 오류는 없다. 모든 회귀나 전체 음악 정확도 검사를 마쳤다는 뜻은 아니다.

최초 두 실제 실행은 각각40/322까지 진행 후 중복 계산 비용 때문에 중단했다(exit1, 최종 output 생성0). 부분 정확도를 결과로 저장하거나 후보를 줄이지 않았다. 큰 Sonata02-2 문맥을 별도 profiling한 결과21point/9,218edge에서2M transition 보류,141.460초/252,274,535call이었다. 반복 `feature_cost`/`transition`이 주된 비용임을 확인했다. Profiling1개를322문맥 성과에 더하지 않는다.

같은 규칙/가중치를 유지하며 measure binary search, 같은 Evidence 객체의 metric/run-feature cache, 전이 비용·blocker 비용 cache를 추가했다. 원 Fraction 비용에 보수적 공통분모를 곱하고 **정확히 나누어지는지 검사한 정수 score unit**으로 DAG 덧셈만 수행한다. Float/반올림/음가 grid 변경이 아니며 출력은 원 Fraction으로 되돌린다. Cache cold/reuse와 exhaustive 최소 점수·lexicographic tie-break를 확인했다. 캐시는 IR/Core/주석 파일에 저장하지 않는다. 별개의 실행 중 피아노 평가 프로세스는 읽기 전용 확인만 하고 중단하지 않았다.

## 5. 실제 동일 자료 비교 — 완료

최종 세 번째 실행은 **494.7084386초/exit0**,33악보/19작품군/322문맥을 모두 처리했다. 완전 평가256/부분·미지원66, train270/dev52와 기존 root+members 평가 분모를 유지한다. eligible time은7,895/8quarter이며 문맥이 겹치므로 고유 악보 길이나 전곡 수로 환산하지 않는다.

| 지표 | J2a 고정 joint | run 표현만 | run + 음악적 근거 |
|---|---:|---:|---:|
| 선택/전체322 | 291 | 288 | 288 |
| 문맥 전체 일치/완전256 | 50 | 50 | 51 |
| 근음 시간 일치 | 40.47% | 39.64% | 40.11% |
| 근음+철자 구성음 시간 일치 | 30.15% | 29.56% | 30.46% |
| 작품군 macro 시간 일치 | 38.35% | 37.46% | 37.59% |
| 의미 경계 precision | 72.82% | 72.24% | 71.09% |
| 의미 경계 recall | 47.18% | 45.82% | 47.18% |
| 의미 경계 F1 | 57.26% | 56.08% | 56.72% |

Music arm은 run-only 대비 시간+0.90percentage point, 전체 일치+1로 제한적 이익을 보인다. 그러나 **J2a 대비 시간+0.32pp/전체+1뿐이며 macro·근음·경계F1은 낮다.** 음악적 근거 연결은 완료했지만 전반적 정확도 개선 또는 운영 승격 근거로는 부족하다. 두 새 고정 arm을 모두 보존하며 **운영 적용 보류**다. Dev 상승만 골라 모델을 채택하거나 weight를 tuning하지 않는다.

| Split/지표 | J2a | run-only | music |
|---|---:|---:|---:|
| Train 전체 일치/205 | 44 | 44 | 44 |
| Train 시간 일치 | 30.08% | 29.36% | 30.11% |
| Train macro | 39.59% | 38.54% | 38.39% |
| Train 경계F1 | 56.42% | 54.84% | 55.14% |
| Dev 전체 일치/51 | 6 | 6 | 7 |
| Dev 시간 일치 | 30.45% | 30.45% | 32.04% |
| Dev macro | 31.71% | 31.71% | 33.34% |
| Dev 경계F1 | 59.89% | 59.89% | 61.54% |

### 새 자원 보류와 해석

기존28 `baseline_not_ready`와3 `edge_budget_abstention_no_pruning`을 그대로 유지하고, 아래 train3문맥에서 **추가2M transition 보류**가 생겼다. run-start를 상태에 더한 exact 탐색은 더 큰 상태 공간을 갖는다. Cap를 높이거나 일부 후보를 지워 해결하지 않았다. 보류를 평가에서 빼지 않아322 전체 분모에 남아 있다.

- Sonata01-2 `cont_e6f3ff5ae8ce7b43c727`, `[67/2,149/4)`.
- Sonata02-2 `cont_e92872bb2c18325ddcfa`, `[3,8)`.
- MozartK281-2 `cont_06279642b89b17cd3fe0`, `[545/6,94)`.

공통으로 선택이 나온288문맥만의 **보조 진단**에서는 J2a49.57%→run-only49.74%→music51.25% 시간 일치다. 이는 위 전체 수치를 대체하지 않으며 보류를 제거한 새로운 headline 정확도로 쓰지 않는다. 첫 학습에서 학습 가능했던110문맥이 새 decoder에서도 전부 추론 가능하다고 가정하지 않는다. 원 candidate oracle132/256도 실제 새 선택51/256과 구별한다.

Music의 완전 문맥 이동은 기존 정답 유지45, 정답→오답5, 오답→정답6, 양쪽 오답200이다. Run-only는 완전 정답 집합50이 그대로지만 부분 시간 판단/자원 보류가 달라졌다. 순증1개는 총6개 회복과5개 퇴행의 결과이며 큰 성능 상승이라고 하지 않는다.

### 저장한 실제 사례와 미해결 문제

[selection-changes.json](../../../output/harmony-evidence-scoring-2026-10-04-r1/selection-changes.json)에10행/9sample ID의 개선·퇴행을 원 context/search physical SHA, full IR content SHA, 원 event ID·유리수 범위·근음/철자·조건부 근거·reference와 연결했다. Corelli의 같은 범위를 다른 lane에서 뽑은 표본은 서로 독립된 악곡으로 세지 않는다. 가장 큰 이익/손실을 각각 최대3개씩 사후 진단용으로 뽑았으며 weight나 arm 선택에 사용하지 않았다.

- **Corelliop01n01c** `cont_f5dc32136f62850616aa`, Dev `[71,74)`: Ddim→E7→A였던 선택이 Dminor→Ehalf-diminished7→A의 원 reference와 일치했다. 시간1→3quarter. 조표 prior 등 **근거 묶음**의 효과이며 개별 feature의 인과 효과는 아직 분리하지 않았다.
- **MozartK281-1** `cont_2d62be18e313bc907551`, train `[13/2,10)`: Bbaug였던 앞부분이 Bbmajor로 바뀌어 A diminished triad로 이어지는 reference와 전체 일치했다. 시간1→7/2quarter. 선택된 두 run에서 실제3음 passing-like 후보를 각각 기록했지만 NCT 정답 검증은 아니다. 동일 signature의5raw edge는2harmonic run으로 해석하며 raw5를 경계5개라 하지 않는다.
- **ChopinBI105-3op30-3** `cont_168e4f0c2dd2344b6027`, Dev `[359/2,187)`: 시간2→0으로 퇴행했다. 비구성음 노출을 줄이는5구성음 F-root 후보들이 경쟁 진행을 흡수했다. 마지막 imported reference도 root/기능을 맞추지 못했다. 원본 imported annotation `ann_2ebe8c3312ff_102`를 읽기 전용으로 확인하니 raw label은 `V(64)/vi`, source root4/changes64이고 reference는 **root F + members Bb/Db/F**다. 이는 표면 Bbminor3화음의 root와 다른 dominant-origin6–4 해석이므로 단순 reference 오류나 잘못된 MIDI로 단정하지 않는다. **큰 음 집합의 장식 흡수 편향과 표면 root/기능적 root의 분리 부족**을 남긴다. 특정 마디 예외로 고치지 않는다. 이 raw label은 사후 진단에만 읽었고 inference 입력이 아니다.
- **Sonata02-2** 위 자원 보류는 기존4quarter 일치가0으로 계산된다. 음악 이름 판단 실패와 계산 자원 실패를 구별해 저장했다.

선택된 run에 neighbor-like29/passing-like29의 **조건부58개**가 있다. 겹친 문맥/반복 표본을 포함한 occurrence 수이며58개 정답 NCT가 아니다. 명시 voice의 직접 연결 밖에 있는 장식·지연·Secondary/7음 해결·local key는 여전히 미지원이다.

[feature-separation.json](../../../output/harmony-evidence-scoring-2026-10-04-r1/feature-separation.json)은 같은 시간 구간의 **옛 emission 특징만 같은** 경쟁 group을 새 관측 특징으로 구별한 예시12묶음이다. 전체33,039묶음을 구별했지만 이는 후보 pair 수/정답 수가 아니며, 옛 transition까지 포함한 전체 path vector가 모두 같았다는 주장도 아니다. 새 구별 가능성이 정확도로 바로 이어지지 않았음을 위 실제 결과와 함께 해석한다.

### 산출물·동결 검사

실제 폴더는 [output/harmony-evidence-scoring-2026-10-04-r1](../../../output/harmony-evidence-scoring-2026-10-04-r1/report.json)이다.3파일 총9,623,473B. **841고유 입력/코드 SHA가 종료 및 사후 검사에서 모두 불변**이다. 새 code2개도 이841에 포함되므로843개라고 중복 합산하지 않는다. 원 source/Core/주석·후보·이전 코드/예측·권한·운영UI/서버/Git와 별개 tracked 수정은 유지했다.

| 파일 | Bytes | 물리SHA256 |
|---|---:|---|
| report.json | 9,168,221 | `808b72c6db9d66bf91fc79ad58b3d0249fb34757dd5490ce09cfd445656aa928` |
| selection-changes.json | 401,875 | `f2d12a47b024c38670d175c2356a88e7c7b94c6b2e9c810a02675b74798b64f2` |
| feature-separation.json | 53,377 | `1beaf51c0ddf61ebf0bb6b8cfb1123a37269a83f528f38083693e8b152392c1a` |

새 scorer SHA `d2c87c81a467738e6e66c85e5d6567e348a103db853e648b01e8880db810b3e2`, trial SHA `b4abe928c370b048706d9455fb2687294fe91638ace511e3222e1c272c7e9400`.

재현은 `python -B -m musicanote_harness.harmony_evidence_scoring_trial --help`의 mandatory arguments를 따른다. Recall SHA `f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb`, J2a report `e197fc16b2199f985a39c780aa2468606cdaf8188c4fc7aad920b8e777c49825`, J2c report `abea4f003bc6dae1947ede55b23ed2c7da9944e079e59015f957ec472d378193`, integration report `22ff64ceb522cfde5039d07dc28935179e8c12add14ed52aaa0295f90e1bcebe`를 pin한다. 새 output 폴더를 지정해야 하며 기존r1은 overwrite하지 않는다.

## 6. 결정과 다음 큰 단계

새 음악적 특징은 실제 선택을 바꾸었고 제한적 이익/퇴행을 함께 검증했다. **새 score 채택은 보류하고 기존 운영을 유지한다.** 연구용15특징 계약을 확보했지만 순증1개이고 `V(64)`에서 표면/기능적 root 차이가 실제 병목임을 확인했다. 다음 큰 작업은 기존 교재 기반6–4/적용화음 규칙이 **실제 후보 공급과 선택 점수**에 들어가는지 연결하고 candidate ceiling을 같은 자료에서 재측정하는 것이다. 특정 악곡의 label을 삽입하지 않고, surface template root와 분석 root/역할 가설을 구별하며 실제 bass·지속·뒤 해결과 경쟁 해석을 보존한다. 자료 관리나 모든 이론 재작성으로 확대하지 않는다.

그 공급 계약을 고정한 뒤 run 합집합 특징의 train-only 학습으로 진행한다. 옛 edge-additive learner에 import만 바꾸지 않는다. 같은 원자료·사용 조건·분모를 유지하고 실제 추론 가능한 train 범위와 resource 보류를 따로 기록한다. Resource 비용은 exact한 상태 dominance/공유 등 의미 보존 방법으로 다루며 cap를 우회하지 않는다.

학습에서도 경쟁 해석/누락·complexity/역할을 함께 대조하고 Dev weight tuning으로 좁은 사례를 맞추지 않는다. 새 지표가 작거나 퇴행하면 가중치 실험을 무한 반복하지 않고 큰 음 집합의 과선택과 주요 후보 누락, 실제 Secondary/7음·local-key 근거로 이동한다. 원 candidate ceiling132/256 밖의 오류를 score 개선으로 해결했다고 주장하지 않는다. 독립 작품 split/전곡 공통 evaluator와 공개 모델 비교, 전체 Roman/전위/NCT·조성·작곡편곡 연결·UI 승격은 남아 있다.
