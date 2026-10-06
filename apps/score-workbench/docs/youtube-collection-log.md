# YouTube 대표 영상 수집 기록

## 2026-09-22 자동 수집 보류

- API 키 설정은 확인했다. Pacific 날짜 2026-09-21 상태는 searchCalls 92/95, cursor 1,344다.
- 기존 상태에 YouTube Search Queries 분당 제한(HTTP 429)이 기록되어 있어 추가 API 호출을 하지 않았다. 신규 매칭과 no-match는 0개다.
- 누적 작품 레코드 1,341개, videoId 보유 1,052개, 고유 videoId 1,025개, no-match 289개다.
- 우회·반복 재시도·검색 DB 동기화는 수행하지 않았다.

## 2026-09-21 제목 검증 보완

- 문제: `FIND THE WAY`에 Bruno Mars의 `Just The Way You Are`가 저장된 것처럼 제목과 무관한 고조회 영상이 채택될 수 있었다. 당시 규칙은 임베드 가능·공개·한국 지역 허용만 필수로 확인했고, 제목 불일치는 후보 탈락 조건이 아니었다.
- 조치: 작품 제목의 식별 단어 일치율을 후보 필수 조건으로 추가했다. 1~2개 식별 단어 제목은 전부, 3개 이상은 75% 이상이 영상 제목에도 있어야 하며, 조회 수는 이 조건을 통과한 후보끼리만 사용한다.
- 캐시 감사: 기존 자동 영상 208개를 `automatic-title-mismatch`로 제거했다. YouTube API 요청은 보내지 않았다. 올바른 영상을 찾지 못하는 작품은 영상 없는 상태로 남겨 다음 수집에서 재시도한다.

## 2026-09-21 자동 수집 중단

- API 키 설정을 확인하고 Pacific 날짜 2026-09-20 기준 95회 한도로 시작했다.
- 92회 호출 뒤 YouTube Search Queries 분당 한도 429 응답을 받아 즉시 중단했다. 추가 호출·우회·검색 DB 동기화는 수행하지 않았다.
- state는 cursor 1,252, searchCalls 92로 보존했다. 다음 실행은 새 Pacific 날짜에 정상 한도부터 재개한다.

## 2026-09-16 자동 수집

- API 키 설정 있음(값 미기록). Pacific date 2026-09-15, searchCalls 0 → 95/95.
- 신규 videoId 94, no-match 1. 누적 videoId 745 / 레코드 780, cursor 780. quota/반복 오류 없음.
- 캐시에 저장 완료. 검색 DB 별도 동기화 없음. 기존 영상 재검색 없음.
- 일일 실패 호출 누락을 방지하도록 요청 전 searchCalls 저장, 파일 lock, 같은 Pacific day 오류 재시도 중지, KR allowed-list 검사 추가. API에서 확인된 embeddable만 수락. 모든 외부 플레이어 환경에서 재생됨을 보증하지는 않음.

## 운영 규칙

- 자동화 ID `ky`의 일일 실행에서 KY 메타데이터 수집 다음 순서로 실행한다.
- YouTube Data API의 Pacific date를 기준으로 하루 최대 95회 search call을 사용한다. 검색 결과 클릭으로 이미 사용한 호출 수도 같은 state에 포함한다.
- 정규화한 곡 제목을 key로 사용하여 solo·duet·trio·quartet 편성은 대표 영상 하나를 공유하고, 이미 `videoId`가 저장된 곡은 다시 검색하지 않는다.
- public, embeddable, syndicated 가능, 한국 지역 비차단 영상만 저장한다. 제목 일치도, official/topic/VEVO/OST 단서와 조회수를 종합해 대표 영상을 선택한다.
- quota 초과나 반복 오류가 발생하면 우회하지 않고 중단한다.
- 저장 위치는 `data/youtube-matches.json`, 진행 상태는 `data/youtube-backfill-state.json`이다.

## 2026-09-06 예약 설정

- 매일 한국시간 오전 9시 KY 수집 후 YouTube 수집을 이어서 실행하도록 기존 heartbeat 자동화에 통합했다.
- 현재 로컬 실행 환경에는 `YOUTUBE_API_KEY`가 설정되어 있지 않다. 키가 없는 동안에는 API 요청을 보내지 않고 설정 필요 상태만 기록한다.
- 검색 DB 반영은 영상 수집과 분리하며, 검증된 동기화 경로를 사용할 때만 수행한다.

## 2026-09-07 실행

- API 키 설정 여부: 미설정.
- search call: 0/95, 신규 매칭: 0, no-match: 0.
- state: Pacific date 미설정, cursor 0, 누적 search call 0.
- YOUTUBE_API_KEY가 없어 외부 요청을 보내지 않았으며 quota는 사용하지 않았다.
- 영상 DB 및 검색 DB 반영은 수행하지 않았다.


## 2026-09-08 실행

- API 키 설정 여부: 설정 완료. 키 값은 로그에 저장하지 않았다.
- Pacific date: 2026-09-07. search call: 95/95, 신규 매칭: 95, no-match: 0.
- public, embeddable, syndicated 가능 및 한국 비차단 조건을 통과한 대표 영상 95개를 `data/youtube-matches.json`에 저장했다.
- quota 오류와 반복 오류는 없었다. 오늘 설정한 안전 한도 95회를 모두 사용했다.
- 영상 검색 DB 동기화는 수행하지 않았다.

## 2026-09-09 실행

- API 키 설정 여부: 현재 자동화 실행 환경에서 미설정.
- search call: 0, 신규 매칭: 0, no-match: 0. 외부 API 호출과 quota 사용은 없었다.
- 기존 state는 Pacific date 2026-09-07, search call 95/95, cursor 95로 유지됐다.
- 영상 DB 및 검색 DB 동기화는 수행하지 않았다.

## 2026-09-09 수동 재실행

- Codex 재시작 후 Windows 사용자 환경의 `YOUTUBE_API_KEY`가 현재 프로세스와 재시작한 개발 서버에 정상 전달되는 것을 확인했다. 키 값은 출력하거나 로그에 저장하지 않았다.
- Pacific date 2026-09-09 기준 search call 99회, 신규 영상 매칭 87개, no-match 12개를 처리했다. 누적 레코드는 194개이며 실제 `videoId`가 저장된 항목은 182개다.
- 100번째 요청 직전에 YouTube Data API의 분당 Search Queries 제한으로 HTTP 429가 발생해 우회하거나 즉시 재시도하지 않고 종료했다. 일일 quota 초과가 아니라 분당 요청 제한이며 state의 cursor는 195로 저장됐다.

## 2026-09-10 외부 재생 불가 영상 교체

- `Beauty and the Beast`에 연결됐던 `pgYEJHJXFB4`는 실제 외부 iframe 재생이 되지 않아 영구 제외 목록에 등록했다.
- YouTube Data API의 `embeddable=true`, public, 한국 비차단 응답만으로 실제 외부 재생 가능 여부를 완전히 보장할 수 없으므로, 사용자 확인 또는 실행 중 재생 오류로 판정된 ID도 별도 제외한다.
- 캐시는 Celine Dion 공식 채널의 `ippaCca4L6A` (`Céline Dion, Peabo Bryson - Beauty and the Beast (Official Audio)`)로 교체했다. 기존 ID는 이후 자동 수집에서도 다시 선택되지 않는다.
- 당일 검색 호출 한도를 이미 사용한 상태여서 추가 Data API 검색 호출 없이 공식 YouTube 검색 결과를 검토해 교체했다.

## 2026-09-12 외부 재생 불가 Moon River 영상 제외

- `Moon River`에 연결된 `EUO34CiTA4o`는 실제 외부 iframe 재생이 실패했지만 YouTube Data API에서는 `public`, `embeddable=true`, 한국 비차단으로 응답했다.
- 해당 ID를 영구 제외 목록에 추가하고 활성 캐시 연결을 제거했다. Pacific date 기준 오늘 호출 상태가 이미 100/100이어서 대체 영상 검색은 다음 수집일로 넘겼다.
- API 상태만으로 실제 iframe 재생을 완전히 판별할 수 없으므로 향후 IFrame Player API 오류 101/150 감지 또는 사용자 실패 신고를 자동 제외 입력으로 연결해야 한다.

## 2026-09-13 자동 수집 확인

- API 키 설정 상태에서 worker를 실행했으나 state의 Pacific date는 2026-09-12, search call은 이미 100회로 안전 한도 95회를 초과해 있었다.
- 신규 API 요청 없이 종료했다. 신규 매칭 0, no-match 0, cursor 490이며 quota 오류나 반복 오류는 없었다.
- 기존 영상 데이터와 검색 DB는 변경하지 않았다. 다음 Pacific date가 시작된 뒤 이어서 수집한다.

## 2026-09-14 자동 수집
 
## 2026-09-15 자동 수집 확인

- API 키 설정 있음(값은 출력·기록하지 않음). YOUTUBE_DAILY_SEARCH_LIMIT=95로 기존 worker 실행.
- Pacific date 2026-09-14의 기존 searchCalls=100으로 오늘 한도를 이미 넘어서 신규 API 요청 0회로 종료했다. 기존 100회를 이번 실행이 소비한 것은 아니다.
- 신규 매칭 0, no-match 0, 누적 videoId 651 / 레코드 685, cursor 685. quota/반복 오류 없음.
- 기존 캐시 유지, 검색 DB 동기화 없음. 다음 Pacific date에 이어서 수집한다.

## 2026-09-14 자동 수집 기록

- API 키 설정 완료. 키 값은 로그에 저장하지 않았다.
- Pacific date 2026-09-13 기준 search call 95/95, 신규 매칭 90개, no-match 5개를 처리했다.
- 누적 레코드 585개 중 실제 `videoId` 저장 항목은 560개이며 cursor는 585다.
- quota 오류와 반복 오류는 없었다. 기존 영상 캐시를 보존했고 검색 DB 동기화는 수행하지 않았다.

## 2026-09-16 자동 수집

- API 키 설정 있음(값은 출력·기록하지 않음). `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다.
- 신규 검색 호출 95/95, 신규 매칭 88개, no-match 7개, quota·반복 오류 없음.
- 누적 레코드 875개, 실제 `videoId` 833개, no-match 42개, cursor 875.
- 공개·embeddable·syndicated 조건을 통과한 대표 영상만 저장했으며 검색 DB 동기화는 수행하지 않았다.

## 2026-09-18 자동 수집 시도

- KY 단계 저장 오류 반복으로 중단했다. YouTube 실행은 하지 않았고 API 호출·quota 사용·캐시 변경은 0이다.
- 검색 DB 동기화는 수행하지 않았다.

## 2026-09-18 재개 시도 (continuation)

- KY 재개가 정상 완료된 뒤 YouTube를 실행했다. Pacific 날짜는 2026-09-17, `YOUTUBE_DAILY_SEARCH_LIMIT=95`였다.
- API 검색 호출 3회, 신규 매칭 2개, no-match 0개. 두 매칭은 저장되었고 세 번째 호출 결과는 저장 전에 중단되었다.
- 누적 레코드 877개, unique videoId 797개, state cursor 878, state searchCalls 3.
- `data/youtube-backfill-state.json` 저장 시 `UNKNOWN: unknown error, open ...` 오류가 발생해 안전 중단했다. API 키는 로그에 기록하지 않았고 재시도·우회·검색 DB 동기화는 수행하지 않았다.

## 2026-09-18 재개 완료 (원자적 저장 적용 후)

- 앞선 파일 열기 오류를 해결하기 위해 같은 폴더의 임시 파일에 기록·동기화한 뒤 교체하는 저장 방식을 적용하고, 일시적인 파일 열기 오류에는 제한된 재시도를 적용했다. 기존 캐시와 상태 파일은 보존했다.

## 2026-09-19 자동 수집

- API 키 설정을 확인하고 Pacific 날짜 2026-09-18 기준 95회 한도를 모두 사용했다.
- 신규 검색 95회 중 대표 영상 91개를 저장했고 4개는 조건을 만족하는 embeddable 영상을 찾지 못했다. quota·차단·반복 오류는 없었다.
- 누적 작품 레코드는 1,064개, videoId 보유 레코드는 1,012개(고유 videoId 960개), no-match 52개, state cursor 1,065다.
- 기존 캐시만 갱신했으며 검색 DB 동기화는 수행하지 않았다. API 키 값은 기록하지 않았다.

## 2026-09-19 자동 수집

- API 키 설정을 확인하고 Pacific 날짜 2026-09-18 기준 95회 한도를 모두 사용했다.
- 신규 검색 95회 중 대표 영상 91개를 저장했고 4개는 조건을 만족하는 embeddable 영상을 찾지 못했다. quota·차단·반복 오류는 없었다.
- 누적 작품 레코드는 1,064개, videoId 보유 레코드는 1,012개(고유 videoId 960개), no-match 52개, state cursor 1,065다.
- 기존 캐시만 갱신했으며 검색 DB 동기화는 수행하지 않았다. API 키 값은 기록하지 않았다.
- Pacific 날짜 2026-09-17의 남은 한도에서 92회 검색을 추가 실행해 state의 `searchCalls`는 95/95에 도달했다. 이 재개 구간에서 87개는 대표 영상을 저장했고 5개는 embeddable 결과를 찾지 못했다.
- 최초 중단 전의 3회 중 1회는 저장 직전 오류로 결과가 지속되지 않아, 이번 날짜에 영속적으로 기록된 결과는 영상 89개와 no-match 5개, 합계 94개다. 호출 수 95와의 한 건 차이는 그 초기 저장 실패의 불확실한 호출을 뜻하며 재호출로 보정하지 않았다.
- 현재 누적 레코드는 969개, 실제 고유 `videoId`는 879개, cursor는 970이다. quota·차단 오류는 없었고 API 키는 출력·기록하지 않았다. 검색 DB 동기화는 수행하지 않았다.

## 2026-09-22 구형 캐시 전면 격리

- HAKUNA MATATA에 몇 초 길이의 무관한 쇼츠가 연결된 사례를 기준으로 전체 활성 캐시를 감사했다.
- videoId 보유 1,053개 중 `composerVerified=true`는 1개뿐이었고, 최소 16개는 제목에 shorts/viral/trending 등 명백한 스팸·쇼츠 단서가 있었다.
- 1,053개 전부를 `data/youtube-quarantine/youtube-matches-2026-09-22T05-45-30-281Z.json`에 보존하고 활성 캐시는 0개로 초기화했다. 이것은 복구 가능한 격리이며 API quota를 사용하지 않았다.
- 이후 수집 규칙은 validation v2, 공개·외부 재생 허용·한국 재생 가능 외에 90초 이상, 쇼츠/바이럴 표기 없음, 제목 일치, 작곡가 메타데이터가 있을 때 작곡가 일치를 모두 요구한다.
- 구형 validation 필드가 없는 레코드는 활성 캐시에 남더라도 UI에서 표시하지 않는다.
- Pacific 날짜 2026-09-21의 남은 8회(93–100/100)를 validation v2로 재수집했다. 7개 작품에 영상을 저장했고 1개는 엄격 조건에서 no-match였다.
- 이 실행 중 파일 순번 제거식이 `10,000 Hours`, `13 Jours en France`, `2 Become 1`의 실제 선두 숫자까지 지우는 문제를 발견했다. 이후에는 `3. 제목`처럼 숫자 뒤에 점과 공백이 있는 파일 순번만 제거한다. 이미 고른 5개 영상은 제목·작곡가·90초 조건이 정확했으므로 저장 제목만 원래 숫자로 교정했다.
- 다음 날짜부터 검색 DB의 대표 `P1/Staff 1/Voice 1` 레코드에서 title·composer·sourceId를 함께 읽어 수집한다. 같은 제목이라도 source 또는 작곡가가 다른 작품은 별도 검증한다.

## 2026-09-23 자동 수집

- API 키 설정을 확인하고 Pacific 날짜 2026-09-22 기준 `YOUTUBE_DAILY_SEARCH_LIMIT=95`의 95회 한도를 모두 사용했다.
- 95개 작품 레코드 중 대표 영상 82개를 저장했고 13개는 엄격한 제목·작곡가·90초·외부 재생 조건에서 no-match였다. 신규 고유 videoId는 31개다.
- validation v2 활성 캐시는 누적 103개 작품 레코드이며 videoId 89개, no-match 14개, 고유 videoId 34개다. state cursor는 103이고 quota·rate-limit·저장 오류는 없었다.
- 검색 DB 동기화는 수행하지 않았고 API 키 값은 기록하지 않았다.
- 편성별 work가 같은 videoId를 공유해 저장되기는 했지만, 정규화 제목이 같은 solo~quartet 레코드가 API 호출 전 캐시를 재사용하지 않고 각각 검색된 것을 확인했다. 다음 실행부터 정규화 제목+작곡가가 같은 validation v2 결과를 API 호출 전에 재사용하도록 수정했고 관련 회귀 7개가 통과했다. 같은 날의 no-match도 편성 간 재사용하되 다음 Pacific 날짜에는 다시 시도할 수 있다.

## 2026-09-24 자동 수집

- API 키 설정을 확인했다. Pacific 날짜 2026-09-23의 YouTube 검색 호출 95/95를 사용했고 quota·반복 오류는 없었다.
- 정규화 제목과 작곡가가 같은 편성은 API 결과를 재사용했다. 오늘 처리한 작품 레코드 263개 중 217개에 영상을 저장했고 46개는 no-match다. 신규 고유 videoId는 78개다.
- 활성 캐시 누적은 작품 레코드 366개, videoId 보유 306개, no-match 60개, 고유 videoId 112개다. cursor는 366이며 마지막 오류는 없다.
- 검색 DB 동기화는 수행하지 않았다. API 키 값은 기록하지 않았다.

## 2026-09-25 자동 점검

- API 키는 설정되어 있다. Pacific 날짜 2026-09-24의 state는 검색 호출 95/95, cursor 630이며 `quotaExceeded`(HTTP 429)가 기록되어 있다.
- 이미 하루 한도에 도달했으므로 이번 자동화에서는 API를 호출하지 않았다. 신규 매칭 0개, 신규 no-match 0개다.
- 활성 캐시는 작품 레코드 629개 중 videoId 보유 543개(고유 193개), no-match 86개다. 기존 캐시와 검색 DB는 변경하지 않았다.
- quota가 재설정되고 Pacific 날짜가 바뀐 뒤에만 재개한다. API 키 값은 기록하지 않았다.

## 2026-09-26 자동 수집

- API 키가 설정되어 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다. Pacific 날짜 2026-09-25에 94회 검색 호출까지 진행했다.
- 이번 실행 결과는 매칭 217개, no-match 34개이며, 편성 캐시 재사용을 포함한 처리 레코드는 251개다. 금일 처리 결과의 고유 videoId는 79개이며, 기존 캐시와 중복을 제외한 고유 videoId 순증은 77개(193→270)다.
- Search Queries 분당 quota HTTP 429가 발생해 즉시 중단했다. state의 searchCalls는 실패 호출을 포함한 94/95이며 cursor는 882다. 우회·재시도하지 않았고 오류를 상태에 보존했다.
- 활성 캐시는 작품 880개(매칭 760, no-match 120), 고유 videoId 270개다. 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-09-27 자동 수집

- API 키가 설정되어 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다. 실제 Pacific 날짜는 2026-09-26이며 검색 호출 95/95를 사용했다(실패 호출 없음).
- 처리 결과는 매칭 214개, no-match 39개이며 편성 캐시 재사용 포함 처리 레코드는 253개다. 금일 결과의 고유 videoId는 81개, 기존 캐시 대비 고유 videoId 순증은 78개(270→348)다.
- 활성 캐시는 작품 1,133개(매칭 974, no-match 159), 고유 videoId 348개이며 state cursor는 1,135다. quota·rate-limit·반복 오류는 없었다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.


## 2026-09-28 자동 수집

- API 키가 설정되어 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다. 실제 Pacific 날짜는 2026-09-27이며 실패 호출을 포함해 검색 호출 95/95를 사용했다.
- 처리 결과는 매칭 253개, no-match 39개이며 편성 캐시 재사용을 포함한 신규 처리 레코드는 292개다. 기존 캐시 대비 고유 videoId는 78개 순증했다(348→426).
- 95번째 호출에서 YouTube Search Queries 분당 quota HTTP 429가 발생해 즉시 중단했다. 재시도·우회하지 않았고 오류를 state에 보존했다.
- 활성 캐시는 작품 1,425개(매칭 1,227, no-match 198), 고유 videoId 426개이며 state cursor는 1,428이다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.


## 2026-09-29 자동 수집

- API 키가 설정되어 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다. 실제 Pacific 날짜는 2026-09-28이며 실패 호출을 포함해 검색 호출 94/95를 사용했다.
- 처리 결과는 매칭 249개, no-match 42개이며 편성 캐시 재사용을 포함한 신규 처리 레코드는 291개다. 기존 캐시 대비 고유 videoId는 79개 순증했다(426→505).
- 94번째 호출에서 YouTube Search Queries 분당 quota HTTP 429가 발생해 즉시 중단했다. 재시도·우회하지 않았고 오류를 state에 보존했다.
- 활성 캐시는 작품 1,716개(매칭 1,476, no-match 240), 고유 videoId 505개이며 state cursor는 1,720이다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-09-30 자동 수집

- API 키가 설정되어 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 실행했다. 실제 Pacific 날짜는 2026-09-29이며 검색 호출 95/95를 사용했고 quota·rate-limit·반복 오류는 없었다.
- 처리 결과는 매칭 257개, no-match 43개이며 편성 캐시 재사용을 포함한 신규 처리 레코드는 300개다. 기존 캐시 대비 고유 videoId는 80개 순증했다(505→585).
- 활성 캐시는 작품 2,016개(매칭 1,733, no-match 283), 고유 videoId 585개이며 state cursor는 2,020이고 마지막 오류는 없다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-01 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-09-30 기준 95/95 호출을 정상 완료했다.
- 처리 결과는 매칭 241개, no-match 55개이며 편성 캐시 재사용 포함 신규 처리 레코드는 296개다. 기존 캐시 대비 고유 videoId는 76개 순증했다(585→661).
- 활성 캐시는 작품 2,312개(매칭 1,974, no-match 338), 고유 videoId 661개이며 state cursor는 2,316이다. quota·rate-limit·반복 오류는 없었다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-02 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-10-01 기준 95/95 검색 호출을 완료했다.
- 처리 결과는 매칭 290개, no-match 36개이며 캐시 재사용 포함 신규 처리 레코드는 326개다. 기존 캐시 대비 고유 videoId는 82개 증가했다(661→743).
- 활성 캐시는 작품 2,638개(매칭 2,264, no-match 374), 고유 videoId 743개이며 state cursor는 2,642다. quota·rate-limit·반복 오류는 없었다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-03 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-10-02 기준 검색 호출 95/95건을 완료했다. 신규 매칭 272개, no-match 27개, 누적 works 2,937개(매칭 2,536, no-match 401), 고유 videoId 827개, cursor 2,941이다.
- quota·rate-limit·반복 오류는 없었고 lastError는 null이다. 기존 제목 캐시를 재사용했다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.
## 2026-10-04 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-10-03 기준 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 검색 호출 95/95건을 완료했다.
- 누적 works 3,250개(매칭 2,814, no-match 436), 고유 videoId 911개, state cursor 3,254이며 lastError는 null이다. 기존 제목·편성 캐시를 재사용했다.
- 신규 처리 313개(매칭 278개, no-match 35개), 고유 videoId는 827개에서 911개로 84개 증가했다.
- quota·rate-limit·반복 오류는 없었고, 공개·embeddable·syndicated·KR 허용·제목/작곡가·최소 길이 검증을 유지했다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-05 자동 수집

- API 키가 설정된 상태에서 Pacific 날짜 2026-10-04 기준 `YOUTUBE_DAILY_SEARCH_LIMIT=95`로 검색 호출 95/95건을 완료했다.
- 신규 처리 313개(매칭 264개, no-match 49개), 누적 works 3,563개(매칭 3,078, no-match 485), 고유 videoId 988개(911→988, +77), cursor 3,567, lastError null이다.
- 기존 제목·편성 캐시를 재사용했고 공개·embeddable·syndicated·KR 허용·제목/작곡가·최소 길이 검증을 유지했다. quota·rate-limit·반복 오류는 없었다.
- 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

## 2026-10-06 자동 수집

- API 키 설정 상태에서 Pacific 날짜 2026-10-05 기준 93/95 검색 호출 후 quotaExceeded(HTTP 429)로 즉시 중단했다. 우회·재시도는 하지 않았다.
- 신규 처리 312개(매칭 266개, no-match 46개), 누적 works 3875개(매칭 3344, no-match 531), 고유 videoId 1065개, cursor 3880, lastError는 quota exceeded이다.
- 기존 제목·편성 캐시를 재사용했고 공개·embeddable·syndicated·KR 허용·제목/작곡가·최소 길이 검증을 유지했다. 원본 XML과 검색 DB는 변경하지 않았고 API 키 값은 기록하지 않았다.

