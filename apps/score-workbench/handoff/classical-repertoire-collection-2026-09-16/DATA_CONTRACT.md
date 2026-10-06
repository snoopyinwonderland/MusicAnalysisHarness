# Data Contract Between Repertoire Collection and MusicSearch

새 프로젝트에서 MusicSearch로 작품/XML을 전달할 때 다음 필드를 보존한다.

## 작품 단위 필수 필드

| 필드 | 설명 |
|---|---|
| `collectionWorkId` | 새 프로젝트가 관리하는 안정적인 작품 ID |
| `composerCanonical` | 권위형 작곡가명 |
| `composerAliases` | 언어·철자·음역 표기 변형 |
| `titleCanonical` | 작품 권위명 |
| `titleAliases` | 번역명·통용명·원어명 |
| `catalogueNumber` | BWV, K/KV, Hob., D, Op. 등 |
| `movement` | 악장 번호와 표제. 전곡과 악장을 구분 |
| `arrangementOf` | 편곡이면 원작 작품 ID |
| `editionOrSource` | 판본·편집자·원본 저장소와 URL |
| `rightsStatus` | public-domain / permission-required / internal-search-only / unknown |
| `rightsJurisdiction` | 판단 관할과 기준일 |
| `xmlQuality` | normal / partial-parse / rendering-error / excluded |
| `collectionStatus` | waiting / source-checked / downloaded / parsed / registered / held |

## 파일 단위 필수 필드

- 원본 파일명과 SHA-256.
- 원본 다운로드 URL과 다운로드일.
- 파일 형식(MusicXML, MXL, MIDI 변환 등).
- 변환 여부와 변환 도구/버전.
- part/staff/voice 보존 여부.
- 파싱 경고와 렌더링 검증 결과.
- 동일 파일/동일 작품의 중복 관계.

## 금지 원칙

- 제목만 같다고 동일 작품으로 확정하지 않는다.
- 한 악장을 전곡 보유로 처리하지 않는다.
- 편곡판을 원곡 보유로 합치지 않는다.
- 작곡가 사망 후 75년만으로 모든 관할·판본·편집 저작권을 자동 확정하지 않는다.
- `rightsStatus=unknown`인 전체 악보를 공개하지 않는다.

## MusicSearch 전달 형식 권장

XML 파일과 같은 디렉터리에 JSONL manifest를 둔다. 한 줄이 파일 하나를 나타내며 위 필드와 상대 파일 경로를 포함한다. MusicSearch는 manifest를 원본으로 읽고 자체 workId/streamId를 반환한다. 반환 매핑은 새 프로젝트가 다시 저장한다.

