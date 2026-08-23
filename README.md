# MUSICANOTE MusicXML Harness Prototype

이 저장소는 대화에서 합의한 `Claim + Evidence + Alternative + Decision` 원칙을 실행 가능한 형태로 만든 최소 프로토타입입니다.

현재 범위는 다음과 같습니다.

- MusicXML을 결정론적으로 파싱하여 원본 위치로 역추적 가능한 Canonical Music IR 생성
- 기보 음표 조각과 타이로 연결된 실제 sounding event를 분리
- 유리수 시간 좌표와 반열린 구간 `[start, end)` 사용
- measure grid, harmonic atom, parser policy 및 validation report 생성
- `music21`을 관찰·후보 생성 도구로 사용하되 결과를 절대 정답으로 취급하지 않음
- 전역 조성, harmonic span 후보, phrase boundary 후보와 confidence/evidence 저장
- 분석 결과로부터 프레이즈 단위 편곡 계획 생성
- 원본 XML과 분석/계획 결과를 별도 파일로 보존

## 실행

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
.\.venv\Scripts\python.exe -m musicanote_harness.cli inventory .\musicxml -o .\output\corpus_inventory.json
.\.venv\Scripts\python.exe -m musicanote_harness.cli validate-corpus .\output\corpus_inventory.json -o .\output\corpus_validation --limit 100
.\.venv\Scripts\python.exe -m musicanote_harness.cli parse .\example.musicxml -o .\output
.\.venv\Scripts\python.exe -m musicanote_harness.cli analyze .\example.musicxml -o .\output
```

`parse`는 음악적 추론 없이 Canonical IR과 검증 보고서만 만듭니다. `analyze`는 그 위에 provisional 화성·경계 후보와 편곡 계획을 추가합니다.

출력:

```text
output/
├── canonical_ir.json
├── analysis_hypotheses.json
├── arrangement_plan.json
├── validation_report.json
└── run_manifest.json
```

## 중요한 설계 경계

`music21`의 `chordify`, key estimation, Roman-numeral 결과는 후보 생성기의 입력입니다. 클래식 음악의 비화성음, 성부 진행, 국소 조성, 전조, 프레이즈 문맥을 완전히 판정하는 음악학적 분석기로 간주하지 않습니다. 현 단계의 편곡 출력도 음표 생성이 아니라 **프레이즈별 기능·텍스처 계획**입니다. 다음 단계에서 Harmony–NCT 반복 추론, Cadence–Phrase 상호 검증, human annotation/case retrieval, 실제 음표 realization을 독립 모듈로 추가해야 합니다.

## 모델 라우팅 권고

- 결정론적 파싱, 좌표 계산, 스키마 검증: LLM을 사용하지 않음
- 복수 화성/프레이즈 가설 비교, 어려운 악보 검토: 가장 강한 reasoning 모델
- 대량 후보 요약, 주석 정규화, 단순 변환: 균형형/저비용 모델
- 코드 구현·리팩터링·테스트: 강한 coding 모델, 반복 작업은 균형형 coding 모델
- 편곡 초안 생성: 강한 reasoning 모델로 분석·계획 후 생성 모델 호출; validator는 별도 결정론적 코드

모델명은 코드에 고정하지 말고 작업 정책으로 주입해야 모델 교체와 비용/품질 실험이 가능합니다.
