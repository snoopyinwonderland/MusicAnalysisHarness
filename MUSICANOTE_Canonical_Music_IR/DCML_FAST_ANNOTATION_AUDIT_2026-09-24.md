# DCML 화성 주석 654쌍 표·악보 구조 전수 검사 — 2026-09-24

## 범위와 결론

MusicXML 악보 **392쌍**과 MuseScore `.mscx` 악보 **262쌍**에 각각 measures/notes/harmonies TSV가 모두 있는 DCML **654쌍**을 읽기 전용으로 전수 검사했다. 음악21 파싱이나 Canonical IR 생성 없이 TSV의 필드·유리수 시간·마디 참조를 확인하고, MusicXML의 기보 마디 수·인쇄 번호 또는 `.mscx`의 마디 수를 비교했다. MusicXML 270쌍과 `.mscx` 244쌍은 이 **표·악보 구조 수준** 검사에서 일관성이 있었다. 나머지 각각 122쌍·18쌍에는 검토 신호가 있다. 통과한 514쌍도 악보 음표와 화성 주석의 정밀 정렬 또는 음악적 정답성이 검증된 것은 아니다. `.mscx`는 변환 전이므로 인쇄 마디 번호와 음표 대조를 수행하지 않았다.

| 자료량 | 행 수 |
|---|---:|
| 마디표 | 68,053 |
| 음표표 | 983,490 |
| 화성표 | 134,872 |
| 화성표에서 빈칸이 아닌 `label` | 134,872 |
| Cadence 값이 있는 행 | 5,254 |
| `phraseend` 값이 있는 행 | 12,345 |

Cadence 원본 값 분포는 `PAC` 2,623, `HC` 1,487, `IAC` 854, `EC` 157, `DC` 75, `PC` 58이다. 이는 TSV 필드의 빈도이지 악보와 정확히 연결된 종지 수나 모델이 판정한 수가 아니다. `phraseend`에는 `{`, `}`, `}{`, `\\` 등의 표시가 있으며 모두 같은 의미의 프레이즈 경계로 평탄화하지 않는다.

## 검토 신호의 의미

| 신호 | 발생 행 | 영향 받은 쌍 | 다음 조치 |
|---|---:|---:|---|
| MusicXML 인쇄 마디 번호와 TSV `mn` 차이 | 2,899 | 115 | 악장 중간 번호 재시작·`X` 마디 등인지 확인; `mc`/시간·음표 검증 없이 자동 보정 금지 |
| 화성 주석의 `duration_qb` 빈칸 | 430 | 89 | **0박짜리 점 주석으로 해석하지 않음**; 앞뒤 화성·엔딩 표기를 조사해 extent를 보류하거나 제한적으로 복원 |
| 음표표의 마디 밖 onset | 2 | 1 | Beethoven sonata `16-2`의 해당 두 행과 원본 악보 직접 대조 |
| 화성표의 마디 밖 onset | 6 | 2 | `.mscx` 자료의 원본 악보 변환 후 위치를 검토 |

한 쌍에 여러 신호가 나타날 수 있어 영향받은 쌍 수를 더하면 검토 대상 140쌍이 되지 않는다. 마디 번호 차이는 악보 기보 자체와 TSV의 관례 차이일 수 있으므로 곧바로 '잘못된 주석'으로 단정하지 않는다. 빈 duration도 다른 엔딩에서 길이가 정의되지 않은 분석 레코드일 수 있다.

## 구현·산출물

- `src/musicanote_harness/dcml_fast_audit.py`: 빠른 검사기. `Fraction`으로 시간을 비교하고 원본 파일은 수정하지 않는다.
- CLI: `audit-dcml-annotations`.
- 테스트: `tests/test_dcml_fast_audit.py`.
- 결과: `output/dcml-fast-annotation-audit-all-2026-09-24/audit_summary.json`, `pair_audit.jsonl`. 각 쌍의 문제 코드와 최대 5개 예시를 저장한다. 이전의 MusicXML 392쌍만 검사한 출력은 `output/dcml-fast-annotation-audit-2026-09-24/`에 보존했다.

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.cli audit-dcml-annotations `
  'output\classical-corpora-registry-2026-09-24\dcml_pair_candidates.jsonl' `
  --output 'output\dcml-fast-annotation-audit-all-2026-09-24'
```

검사 대상은 DCML의 완비된 654쌍이다. 다른 코퍼스의 JAMS/RomanText 자료와 누락 파일이 있는 DCML 후보는 이 결과에 포함되지 않는다. 라이선스·주석 출처·작품 중복도 아직 확인하지 않았다.

## 다음 정밀 검증

1. MusicXML 392쌍 전체를 `validate-dcml-batch`로 정밀 검증한다. 표 검사에서 검토 대상으로 나온 쌍도 함께 실행하여 실제 IR의 마디·음표 위치, 출처 note ID, 화성 span을 확인한다. 수집한 50쌍의 검증 결과는 adapter version·원본 hash·산출물 파일이 같으면 재사용한다.
2. MusicXML 122쌍의 검토 신호는 원인별로 분리한다. 인쇄 번호만 다른 경우에도 음표·시간축이 일치하면 **명시적인 변환 근거**를 남기고 사용 가능 범위를 넓힐 수 있다. 빈 duration은 명확한 근거 전까지 `ambiguous`로 둔다.
3. `.mscx` 262쌍은 현재 표·마디 수만 확인했다. 변환기 확보와 악보↔변환본 대조 후에 같은 정밀 검증을 실행한다.
4. 좌표 연결이 완료된 뒤에야 화성 레이블 자체의 검토와 맹검 분석 정확도 평가를 한다. Cadence/phraseend 값도 자동 생성 분석기의 입력 정답으로 누출시키지 않는다.
