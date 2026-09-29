# 분산화음 구간·화음·비화성음 공동 판정 파일럿

## 구현

`src/musicanote_harness/harmony_joint.py`의 `analyze_joint(ir)`는 Canonical IR의 sounding events, 성부 ID, 박 단위만 사용한다. 음의 시작·끝과 박 격자를 경계 후보로 만들고 최대 8개 기보 박 길이의 구간을 비교한다. Phrase와 원자료 화성 주석은 query 입력에 사용하지 않는다.

각 구간은 장·단·감·증3화음, dominant7/major7/minor7/half-diminished7/diminished7 템플릿을 평가한다. 점수 비용은 비화성음 설명 후 남은 불일치 음의 음가 비중 0.7, 구성음 미충족 0.3, 근음과 베이스 불일치 0.04로 구성한다. 구간당 비용 0.15, 화음 변경 비용 0.04를 더하고 dominant7의 근음에서 다음 후보 근음으로 5도 하행하면 0.06을 할인한다. 초기 수동 가중치이며 데이터로 보정된 확률이 아니다.

성부별 단선율의 앞뒤 음이 화음 구성음인 경우 passing-like/neighbor-like를 조건부 후보로 만들고, 경계 이전부터 유지된 음의 순차 하행 해결은 suspension-like로 기록한다. 같은 성부의 동시 여러 음을 임의의 선율로 연결하지 않는다. 관찰 범위의 gap과 해결 시점을 검사한다. 강박 경과음·전타음·선행음 등은 아직 지원하지 않는다.

구간 길이와 화음 후보를 동적 계획법으로 함께 선택한다. 시점별 상위 12개 상태를 유지하는 근사 탐색이다. 출력은 선택 경로, 경쟁 경로 비용, 구간별 대안, 조건부 NCT 종류와 sounding event 참조다. 근음의 enharmonic spelling과 국소 조성·Secondary 기능은 별도 후속 과제다.

## 검증

- 분산 C–E–G–E를 한 C major span으로 선택.
- C–D–E의 짧은 D를 C major에 대한 passing-like 후보로 설명.
- G7의 F를 구성음으로 유지.
- 명확한 C→G 변화 보존.
- source/phrase label을 추가해도 계산 결과 불변.

새 테스트 5개와 기존 harmony 테스트를 합해 33개 통과했다.

실제 악보 3개 각각 처음 16 quarter만 분석한 진단 결과:

| 악보 | 이전 구간 수 | 공동 판정 구간 수 | 조건부 NCT 수 | 시간 |
|---|---:|---:|---:|---:|
| Beethoven op18-1 1악장 | 6 | 3 | 9 | 0.368초 |
| Chopin op30-2 | 6 | 5 | 4 | 0.264초 |
| Corelli op01n01a | 7 | 6 | 18 | 2.235초 |

이는 실행·동작 진단이며 정답 정확도 평가가 아니다. 구간 수 감소도 개선을 의미하지 않는다. Beethoven에서는 F major7, Corelli에서는 여러 major7을 선택했다. 비화성음을 화음의 7음으로 흡수하는 편향과 과도한 병합을 검사해야 한다. 따라서 Viewer 기본 엔진에는 아직 연결하지 않는다.

출력: `output/harmony-joint-pilot-2026-09-26/report.json` 및 악보별 JSON.
재실행: `python -m musicanote_harness.harmony_joint_pilot` (`PYTHONPATH=src`).

## 다음 검토

1. 3화음+장식음과 7화음의 대안 비교에 박 위치·구성음 지속·성부 준비/해결을 추가.
2. 주석 경계와 비교해 과도한 병합/분할을 계측하고, 같은 표본에서 기존 unfolded와 비교.
3. voice-aware 해결 경로, spelling-aware 근음, Secondary 목표 도착을 결합.
4. 전타음·선행음·계류와 지속 화음의 정교한 판별을 추가.
5. 전곡 성능과 실패를 검증한 뒤 Viewer shadow 결과로 연결.

## 개발 기록

2026-09-26: 공동 span/chord/NCT 판정과 근거 참조, 테스트, 실제 악보 진단을 구현했다. 고정 가중치는 초기 가설이며 검증 전 자동 분석 정확도 상승을 주장하지 않는다.

## 교과서 대조 검토 (2026-09-26)

자료 위치: `K:/MUSICANOTE/musicanote-ai-local/books`. 전체 책을 완독하거나 학습에 투입한 것이 아니다. 아래는 제한된 본문 검토와 목차 조사이며, 원본 PDF와 production 코드는 수정하지 않았다.

### 확인 범위

- Aldwell/Schachter/Cadwallader, *Harmony and Voice Leading*: 인쇄 pp.373–374, 376–379, 381–384, 392–393 본문 확인. PDF 페이지는 인쇄 페이지+11이다. p.381(PDF 392)의 악보·본문을 렌더링하여 확인했다. 핵심 절: Unit 21 §§2–3, 5–7, 10–14; Unit 22 §§1–2.
- Horton/Byrne/Ritchey, *Harmony Through Melody*: PDF pp.6–12 목차·서문 확인. 후속 본문 대상은 ch.14 Tonicization, ch.17 Nested Melodic Figures, ch.20 Accompanied Melody, ch.22 Harmonic Rhythm and the Metric Framework. 아직 이 절들의 내용을 검증했다고 취급하지 않는다.
- Berkman, *The Jazz Harmony Book*: PDF p.4 목차 및 pp.8,10 서문/도입 확인. 후속 대상은 ch.2 diatonic seventh, ch.3 secondary dominant, ch.10 reharmonization, ch.19 pedals, ch.22 incomplete chords. 재즈의 실제 7화음을 제거하지 않기 위한 양식별 비교 자료이며 세부 규칙 도출은 본문 검토 후 수행한다.

### 본문에서 확인한 개념과 구현 제안의 구별

| 출처 | 확인한 개념(요약) | Harness에 대한 제안 — 아직 미구현 |
|---|---|---|
| H&VL pp.373–374 | 분산 진행은 비인접 음 사이의 암시적 성부 연결을 포함할 수 있다. | XML voice의 바로 앞뒤 음뿐 아니라 음역·진행 연속성을 근거로 한 잠재 성부 경로를 비교한다. 경로도 가설로 보존한다. |
| H&VL pp.376–377 | 경과 진행은 한 화음 내부 또는 화음 사이를 연결한다. 보조 진행에는 강박·협화적 형태도 있다. | 앞뒤 음이 동일 후보 화음 구성음이어야 한다는 제한을 완화하되, 앞/뒤 화음 후보 각각에 대한 연결 근거가 필요하다. |
| H&VL pp.381–383 | 강박의 장식음 때문에 박 위 음만으로 화음을 정하면 잘못된 해석을 만들 수 있다. | 강박·음가를 절대 판정으로 쓰지 않고 성부 진행과 해결을 함께 점수화한다. 전타음 용어는 출처별 정의 차이를 기록한다. |
| H&VL pp.392–393 | 계류는 준비·지연·해결의 시간적 관계이며 재타격된 형태도 있다. | tie 존재만으로 계류를 확정하지 않는다. 준비/지연/해결의 화음 후보와 상대 강세를 검사하고 재타격형도 후속 지원한다. |

장식적 성부 기능과 화음 구성음 여부는 동일 개념이 아니다. 특정 음이 템플릿에 속한다는 이유만으로 장식적 역할 검사를 건너뛰지 않는다. 위 표는 책의 내용을 알고리즘으로 직역한 규범이 아니라 검증할 설계 가설이다.

### 현재 major7 편향 진단과 연결

Beethoven op18-1_01의 선택 구간 [0,7.5) quarter에서 F major 비용은 0.11909, F major7은 0.08136이었다. E는 네 성부 관측에서 F–E–F의 가운데에 있지만 major7 후보에서는 구성음이므로 NCT 비교를 건너뛴다. F major에서는 보조음 설명 후에도 잔여 비용이 발생한다. 또한 A가 없는 상태에서 coverage가 2/3에서 3/4로 증가한다. 이는 7화음의 독립적 지지보다 관측 음 추가 흡수를 보상하는 비대칭이다.

해당 구간은 원자료의 I [0,3), V [3,6), I [6,9) 일부를 합친다. 따라서 major7 라벨 교체만이 아니라 경계의 과도한 병합도 검증해야 한다. 원자료 주석은 비교 근거이며 모든 해석을 무조건 확정하는 oracle은 아니다.

수정 순서 제안:
1. 동일 구간에서 `3화음+장식적 성부 진행`과 `실제 7화음`을 대칭적으로 비교한다. 단순한 major7 금지/일괄 벌점은 사용하지 않는다.
2. 화음 핵심 구성음의 지지, 추가 음의 독립적 지속/반복, 성부별 준비·해결, 양식별 허용을 분리한다. 구성음 생략 가능성도 유지한다.
3. 국소 화음 변화 근거를 보존하고 합친 구간과 나눈 구간을 비교한다. Phrase 경계를 화성의 정답으로 입력하지 않는다.
4. 화음 경계를 건너는 경과 진행과 잠재 성부를 확장한다. 같은 pitch class 전체를 일괄 비화성음으로 분류하지 않는다.
5. 비용 차이가 작은 경우 대안·불확실성을 유지한다. 수동 비용을 확률 confidence로 표시하지 않는다.

### 데이터화와 검증 계약

교과서 규칙은 Canonical Core가 아니라 versioned rule/evidence 자료로 둔다. 각 항목에 source/edition/printed_page/pdf_page/section, 적용 양식, 관찰 조건, 지지·반대 증거, 예외, competing hypotheses, 검증 상태, 테스트 ID를 기록한다. 책 전문을 저장소에 복제하지 않는다. 악보 예시는 직접 확인·전사·검증한 것만 event fixture로 등록하며, PDF 텍스트 추출 결과를 음표 데이터로 간주하지 않는다.

회귀 테스트에는 F–E–F 보조형과 실제 분산 major7의 대비, dominant7 보존, 화음 경계를 지나는 D–E–F, 강박 장식음, tie/restruck 계류, 같은 음높이의 서로 다른 역할, 핵심 구성음 부족 시 불확실성, 이조 및 박 단위 스케일 변형을 포함한다. 정답 NCT 주석이 없는 코퍼스에 대해서는 화음 라벨만으로 NCT 정확도를 주장하지 않는다. 먼저 train/dev로 검증하고 holdout은 조정에 사용하지 않는다.

이 검토에서는 엔진/Viewer 동작 변경이나 성능 개선을 완료한 것이 아니다. 교과서 대조에 따른 수정안과 테스트 요구를 기록했다.

## 화음 유지 / 변화 경계 진단 구현 (2026-09-26)

사용자 제안: 수직 관측으로 후보를 만들고 앞뒤 진행과 음의 지속을 확인하여, 새로운 음이 기존 화음의 장식인지 화음 변화인지 비교한다. onset은 시작 시점이고 지속 범위는 sounding event의 release까지다. 타이로 지속되는 음이 있어도 화성은 바뀔 수 있으며, 계류·페달 가능성 때문에 지속음 자체를 화음 유지의 확정 근거로 삼지 않는다.

### 이번 구현 범위

- `src/musicanote_harness/harmony_boundary_probe.py`: Canonical IR만 입력받는 오프라인 진단기. 원자료 화성 주석이나 Phrase 결과를 후보 입력으로 쓰지 않는다.
- 경계에서 새 attack / 경계를 넘어 지속 / 경계에서 release되는 sounding event와 원본 ID를 각각 기록한다.
- 기존 joint scorer를 재사용해 앞 구간, 뒤 구간, 합친 구간의 화음·NCT 후보를 비교한다. 아직 수직 후보 생성부터 전후 문맥 추론까지 완성한 새로운 분석기는 아니다.
- `continue` 비용 = 전체 박 길이 × 합친 구간 후보 비용. `change` 비용 = 앞 박 길이 × 앞 후보 비용 + 뒤 박 길이 × 뒤 후보 비용 + 0.15. 서로 다른 라벨의 변화만 비교한다. 수동 비용이며 확률이 아니다.
- 각 창 상위 5개 후보를 사용한다. 전체 상위 6개와 별개로 최선의 유지/변화 대안을 각각 보존한다. `automatically_selected=null`, `review_required`, `calibrated=false`를 명시한다.
- 관측 문맥은 이전·현재·다음 마디로 제한한다. 문맥 바깥에서 시작하는 미래 음은 이웃 연결에 넣지 않는다. 혼합 박자 창은 건너뛴다. 6/9/12박의 관습적인 3분할 묶음은 실제 지각 박과 같다고 보장하지 않는다.
- pedal과 연주 시간은 추정하지 않으며 기보 및 tie 기반 release를 사용한다. 기존 production 분석기와 Viewer는 변경하지 않았다.

### 실행 결과와 한계

`output/harmony-boundary-probe-2026-09-26/mozart.json` (K281-1), `beethoven.json` (03-2)에 각각 16개, 합계 32개 진단을 저장했다. 이번 표본은 각 악보 처음부터 선택한 onset/release 시점이며, 앞선 sonata audit의 복잡도 상위 구간 표본과는 다르다. 전곡 성능 검증이나 정답 대조 정확도가 아니다.

모차르트의 처음 세 진단에서 유지 후보가 Bb:major7로 나온다. 기존 7화음 흡수 편향이 아직 남아 있으므로 이 결과를 개선된 정답으로 승격하지 않는다. 변화 후보가 있다는 것만으로 실제 경계가 검증된 것도 아니다. 다음 단계는 3화음+장식과 7화음을 대칭적으로 평가하는 비용 개선 및 주석 경계와의 대조다. 그 뒤 복잡도 높은 구간과 전곡으로 검증 범위를 확대한다.

검증: `test_harmony*.py` 45개, `test_tonal_foundations.py` 13개, `test_foundation_sonata_audit.py` 4개, 총 62개 통과. 새 경계 진단 테스트 5개는 attack/지속/release, 두 대안 보존, 주석·Phrase 입력 비의존성, 문맥 밖 미래음 제외, 잘못된 범위 거부를 검사한다. 이는 음악적 정확도 평가와 구별한다.

재실행 예 (`PYTHONPATH=src`):

```powershell
& '.venv/Scripts/python.exe' -m musicanote_harness.harmony_boundary_probe --ir output/dcml-batch-2026-09-24/pairs/mozart-sonatas/K281-1/canonical_music_ir.json --output output/harmony-boundary-probe-2026-09-26/mozart.json
```
