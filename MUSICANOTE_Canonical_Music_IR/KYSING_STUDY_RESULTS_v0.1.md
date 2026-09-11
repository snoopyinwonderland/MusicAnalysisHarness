# KYSing 패턴 연구: 첫 실행 결과

## 목적과 입력

가사 단절을 약한 학습 신호로 활용해, 기악곡에도 적용할 수 있는 음악적 특징을 연구한다. 대문자 시작과 capitalization은 경계 증거로 사용하지 않는다.

입력 목록: `K:/MusicSearch/data/kysing-metadata/kysing-valid-lyrics-files.json` (4,025개). 원본: `U:/KYSing_MusicXML`. 목록 전체에서 균등 간격으로 30개를 선택했다. 이 표본은 장르·언어 층화 표본이 아니다.

기존 보고서의 정상 가사 판정은 후보 목록으로 재사용했다. 모든 가사가 완벽히 정렬됐다는 주장은 이번 검사에서 검증하지 않았다. 단어 수 기준으로 선별된 목록은 띄어쓰기가 없는 언어를 과소대표할 수 있다.

## 실행 결과

| 항목 | 수량 |
|---|---:|
| 처리 파일 | 30 |
| 파일 처리 오류 | 0 |
| 음악 특징 프레임 | 41,412 |
| 가사 연결 사례: 음악적 휴지 뒤 진입 | 1,387 |
| 가사 연결 사례: 연속 진입 | 10,668 |
| 연결 사례 중 구두점 포함 | 71 |
| 원본 harmony 요소 | 0 |

사례 수는 곡 수나 고유 프레이즈 수가 아니다. 복수 절 가사, 중복 표기 등이 포함될 수 있다. 구두점은 현재 음절에 기록된 관찰이며 실제 경계 시점은 그 음절과 melisma가 끝나는 위치를 별도로 정렬해야 한다.

30곡 모두 가사를 제거한 뒤 음악 특징 및 원본 화음 관찰이 동일했다. 단위 테스트는 한글·일본어·중국어·아랍어·라틴 문자 분류와 가사 삭제 및 대소문자 변경 불변성을 검사한다. 이는 언어 의미 이해나 실제 프레이즈 정확도 검증이 아니다.

## 구현

`src/musicanote_harness/kysing_study.py`는 source-position reference와 유리수 시간을 사용하는 연구용 추출기다. Canonical IR production parser를 대체하지 않는다.

결과 파일은 `output/kysing-study/`에 저장한다. 각 파일에는 서로 분리된 musical_feature_frames, weak_target_observations, source_harmony_symbols, cases가 있다. 가사 원문은 결과에 저장하지 않는다.

```powershell
$env:PYTHONPATH='src'
& '.\.venv\Scripts\python.exe' -m musicanote_harness.kysing_study 'K:\MusicSearch\data\kysing-metadata\kysing-valid-lyrics-files.json' 'U:\KYSing_MusicXML' 'output\kysing-study' --limit 30
```

## 사례 해석과 개발 순서

1. **휴지 뒤 진입:** 같은 논리 성부의 이전 release와 현재 onset 사이 간격을 측정한다. 이는 실제 호흡 관측이 아닌 음악적 휴지 대용 지표다. 반주와 보컬의 경계를 같은 방식으로 후보화한다.
2. **구두점이 있으나 연속 진행:** 부정 사례 후보로 보존한다. 구두점은 문장 해석의 확정 기준이 아니다.
3. **구두점이 없으나 휴지 존재:** 쉼표 부족을 보완하는 표본으로 조사한다.
4. **휴지 + V/I 도착:** 음표 기반 조성·화음 가설을 연결해야 한다. 조표만으로 장단조를 확정하지 않는다.
5. **V-I이지만 진행 지속:** 내부 종지와 프레이즈 종결을 구별하는 대조 사례로 수집한다.

현재는 사례 관찰까지만 구현됐으며, 약한 정답 라벨 생성·학습·프레이즈 예측은 아직 구현하지 않았다.

학습 전 필수 작업: Canonical IR ID 매핑, 파트별 마디 정렬 검증, tie-chain/melisma 종료 정렬, 동일 onset 화음에서 선율 이전음 선정 정책, written/concert pitch 검증, 독립적인 조성·화음 가설 연결. 현재 pitch_delta는 source 순서로 정의된 값이므로 다성부 선율 특징으로 바로 학습하면 안 된다.

새 언어 확장은 기존 4,025개 목록 밖의 파일도 동일한 Unicode 기준으로 재감사해야 한다. 화음처럼 보이는 짧은 토큰은 자연어일 수 있어 chord_or_word로 보류한다. 대문자 하나만으로 가사 또는 화음을 확정하지 않는다.
