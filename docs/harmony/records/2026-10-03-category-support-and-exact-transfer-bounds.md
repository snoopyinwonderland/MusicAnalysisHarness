# 단계39 — 후보 역할 지원 집합과 정확한 유리수 저장 상계

화성 분석의 **개발 문서**다. [메인 문서](../README.md), [개발 로그](../DEVELOPMENT_LOG.md), [직전 실측](2026-10-03-whole-request-storage-resource-pilot.md)과 연결한다. 사용자의 주석 평가 질문에 답한 뒤 원래 개발 순서로 이어간 작업이다.

## 목적과 범위

직전 실제 원 요청은 전체 저장 예약3,881,314,476B가 기본2GiB를 초과하여 비교를 시작하지 않았다. 모든 pair에 역할6종류의36조합과 느슨한 분모 폭을 예약하는 항목이 주 병목이었다. 이번에는 **실제 비교 결과를 먼저 보지 않고**, 같은 owned 후보의 원 row와 endpoint에 근거하여 그 항목의 상계를 좁혔다.

원음표·음가·타이·철자·후보·비화성음 가설·분모·pair JSON·음악적 판정 규칙은 바꾸지 않는다. 실제 출력 크기를 압축하거나 음악 해석을 개선했다는 뜻도 아니다. 과도한 사전 예약량을 정교화하는 연구용 library이며, 기존 writer/coordinator는 그대로다.

## 일반 규칙과 수학적 근거

### 역할 종류의 지원 집합

- 각 entry의 owned `pair_index.source_rows`를 전부 검사한다. 현재 그 후보의 조건부 역할 설명에 존재하는 category들의 집합을 구한다. 계정의 credit가0/null이라는 이유로 row를 삭제하지 않는다.
- 왼쪽 집합L과 오른쪽 집합R을 가지는 pair에서 발생 가능한 transfer 종류 수는 `min(|L|×|R|, sound_atoms)` 이하다. 원 row의 정확한 종류를 유지하며 종류가 같다는 이유로 음표/row occurrence를 합치지 않는다.
- 현재 닫힌6종류 밖의 category는 조용히 제외하지 않고 오류로 처리한다. 새 종류 추가는 별도 버전/계약 변경과 검증이 필요하다.
- 이 검사는 최종 화음/NCT 정답을 선택하는 작업이 아니다. 모든 기존 가설을 같은 방식으로 검사한다.

### 정확한 분모와 분자 상계

1. 모든 sound endpoint 분모의 최소공배수D를 구한다. 반복된 분모를 계속 곱하여 자릿수를 늘리지 않는다.
2. 각 endpoint를D 단위의 정수로 정확히 변환하고 순서를 확인한다. Float나 ‘보통 음악의 분모는 작다’는 추측을 쓰지 않는다.
3. 각 sound의 마지막−첫 endpoint 길이를D 단위로 더한M을 구한다. 모든 transfer는 각 sound 안의 겹치지 않는 비음수 구간들의 합이다. 따라서 기약 분모는D의 약수이고 기약 분자는M 이하다. Sound에 빈 구간이 있더라도 전체 span을 쓰므로 더 보수적일 뿐 누락하지 않는다.
4. 실제D와M의 십진 자릿수로 rational JSON 상계를 만든다. GCD/나눗셈/곱셈/덧셈·정수/문자열 할당은 **실행 전에** 비용 및 bit/scratch 한도를 검사한다. 한도를 넘으면 전체 보류이며 확인되지 않은 상계는null이다.

Bigint work와 scratch는 명시적 보수 비용 모델이다. CPU 시간/RSS의 수학적 최대값으로 해석하지 않는다. 기본 proof 한도는 work1B, integer8192bits, arithmetic scratch proxy128KiB, retained proof8MiB이며 caller는 강화만 가능하다. 기존 Core/group/source/block/output 한도를 늘리지 않았다.

### 전체 JSON 상계 보존

기존 동결된 stream schema 상계의 **`category_transfer_note_time` 항목만** 대체한다. 나머지 assumptions·변화 pointer·bass pointer·음가 계정·null·ID·SHA·괄호/쉼표·block header 상계는 그대로 사용한다.

- Block 상계 = 기존 block 상계 − 모든 pair의 안전한 항목 절감 합.
- 최대 pair 상계 = 기존 최대 pair 상계 − 해당 block의 최소 pair 절감. 서로 다른 pair의 최대치를 임의로 빼지 않는다.
- 구 상계와 신 상계는 둘 다 유효하므로 두 항목 상계 중 작은 것을 쓴다. Byte hold만 새 상계로 재판정하며, 기존 work hold/unknown을 성공으로 바꾸지 않는다.
- 원 task의 source/group/refinement/entry inventory SHA, 범위·예정 pair 수와 정확한 owned proof를 확인한다. 공개 JSON/descriptor로 권한을 복원하지 않는다.

## 구현과 API

- [새 library](../../../src/musicanote_harness/proof_shared_transfer_bounds.py): `prepare_transfer_bounds(prepared)`로 같은 group에 연결된 immutable `TransferProof`를 발급한다. `proof_info(proof)`는 진단용이며 `task_stream_bound(proof, task)`는 전체 task의 새 상계를 계산한다.
- [신규 검사](../../../tests/test_proof_shared_transfer_bounds.py): 합성 MusicXML에서 실제 준비된 source/group을 사용한다. Source 지원 집합·LCM·공통 단위 분자·반례와 byte/work hold, 다른 group/가짜 descriptor, 여러 pair의 합/최대치를 검사한다.
- [소형 실행기](../../../tmp/transfer_bound_fixture_pilot_20261003.py):4개 합성 XML group의 상계를 먼저 구한 뒤6개 실제 작은 pair 결과가 그 안에 드는지 확인한다. 기존 실제 corpus runner나 운영 분석기가 아니다.

Source/catalog 전체 export·DAG decode·pair atom run·결과/압축 샘플을 상계의 입력으로 사용하지 않는다. 생성된 proof를 기존 writer의 JSON 계획에 덮어쓰거나 monkeypatch하여 한도를 우회하지 않는다. 다음 단계에서 정확한 owned proof를 소비하는 별도 버전의 저장 연결이 필요하다.

## 검사와 소형 결과

- 최종 신규 **21개/20.304초 PASS**. 처음19개/9.807초 후, 여러 pair와80개 고정 seed 분수/역할 조합 property 검사 및 fixture 격리 복사를 추가했다. 중간21개/19.926초와 최종 재검사를 별도 신규 수로 더하지 않는다.
- 기존 `test_proof_shared_progression_streaming`16개 + `test_proof_shared_source_progression_contrast`34개 = **50개/72.904초 PASS**. 기존 frozen 코드/test를 수정하지 않았다.
- 공개 검사 외부로 추가 subagent를 실행하지 않았다. 이번 검수는 root 코드/수식 검토와 자동 검사다. 이전 단계의 독립 검수 결과를 이번 신규 코드에 소급하지 않는다.
- 보존 검사 도구의 첫 비교는 SHA 배열을 path key로 조회하여49개를 잘못 변경으로 표시했다. 인덱스로 바로잡아49/49 동일함을 확인했다. 실제 파일 변경은 없었으며 제품 오류나 성공 검사 수로 세지 않는다.
- 소형 실행20.222295초/exit0,4개 합성 group/9entry/6pair. [결과 정본](../../../output/proof-transfer-bound-fixtures-2026-10-03-r1/report.json)은8,731B이며 시작/끝6code SHA가 동일하다.

| 합성 예제 | 후보별 역할 종류 수 | 정확한D | 구 block 상계B | 신 block 상계B | 실제 block B |
|---|---|---:|---:|---:|---:|
| Passing-like candidate controls |2,2|1|4,911|4,521|4,106|
| Rational timing |2,3|3|4,946|4,820|4,064|
| Ordinary-first adverse transition |3,3|2|6,183|5,637|4,200|
| Three-entry partition comparison |2,3,2|2|17,130|11,085|8,959|
| 合계 |9entry/6pair|—|33,170|26,063|21,329|

소형 상계 절감7,107B(약21.43%)는 **이4개 예제에만 해당**한다. 기존 실제1,710후보/291,555pair/105task에 이 비율을 외삽하지 않는다. 실제 JSON21,329B가 새26,063B 이하임을 확인했으며 JSON 내용은 기존 비교 core가 생성했다. Source-once 전체 저장, 기존 실제 요청의2GiB fit, 화성 정확도나 화면 적용 완료를 뜻하지 않는다.

## 동결·보존

| 신규 파일 | SHA256 |
|---|---|
| `src/musicanote_harness/proof_shared_transfer_bounds.py` | `5ececf0c0e8422ac10a70bb475de4a6c706255a95da674fc89c2de3426bfdda9` |
| `tests/test_proof_shared_transfer_bounds.py` | `684dc59ddfb2f7c5cb0001c58a45895d586558be0f373156ba2323c79f3a12e3` |
| `tmp/transfer_bound_fixture_pilot_20261003.py` | `b03d1ac025d399aec35ede56258798d6f55cde539fe8e57b0720201619d0931b` |

Report SHA256: `1cc993933f127039de0a2b99a768ecff1e51304239dd4b0554142938e9fdb196`.

신규/기존 구별: 위3파일과 새 output만 추가하고 화성 메인/로그/이 상세 기록을 갱신한다. 원XML/Core/주석/과거 output·기존 writer/coordinator·Git/서버/UI는 수정하지 않는다. 최종 선행SHA·3AST·UTF-8/로컬 링크 검사는 개발 로그에 기록한다.

## 다음 개발 단위와 아직 남은 것

1. 별도 버전의 저장 연결에서 **같은 owned proof**를 task bound·전체 예약·실행 때 사용한다. 원 source-once/catalog/manifest 비용·current-code 및 output 보호·partial/unknown·원/선택/생략 분모를 그대로 연결한다. 외부 숫자를 저장 권한으로 사용하지 않는다.
2. 같은 source1/completion0의1,710후보/5group/105task를 새 전체 상계로 fresh 재검증한다. 모두 기본 한도에 들어갈 때만 비교·저장을 시작한다. 결과가 아직 보류여도 후보 삭제·cap 증가·좋은 prefix로 우회하지 않는다.
3. 전체 후보 대비의 음악적 선택 정책과 다양한 작품의 blind 주석 대조로 넘어간다. 최근 검사 통과 수와 이 상계 개선은 화성 정답률이 아니다.

기존 실제 요청은 여전히 단계38의 저장 예약 보류 상태다. 이번21검사/6합성 pair를 실제 corpus 완료나 전곡 기능·NCT·cadence 정확도로 승격하지 않는다.
