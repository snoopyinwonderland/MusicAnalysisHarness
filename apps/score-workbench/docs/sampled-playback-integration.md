# 악기 샘플 음원 통합 — 2026-10-05

## 요청과 범위

Claude Code에서 만든 악기 샘플 음원을 MusicSearch 뷰어에도 연결하되, 기존 재생 기능을 보존한다. 참조 구현은 로컬 `claude/sampled-playback` 브랜치의 `a8adaf8b468fbb65776ed01e447d949dbe60adf9`이다. 브랜치 전체를 병합하지 않고 필요한 음원 자산을 재사용하고 재생 엔진·호출부를 검토해 통합했다.

지원 음색은 피아노·바이올린·비올라·첼로다. Query와 Query 추천은 피아노, 검색 결과와 상세 악보는 실제 재생하는 검색 성부의 악기 정보를 사용한다. 그 외 악기는 피아노로 대체한다. 여러 파트 동시 합주 재생이나 새 템포 해석기를 추가한 작업은 아니다.

검색·순위·DB·원본 MusicXML·Verovio 악보 변환은 변경하지 않는다. 상세 악보의 표시용 Part/Staff/Voice 선택을 실제 재생 성부로 오인하지 않도록 음색 결정은 `work.streamId` 기준으로 한다. 분석용 `structureWork`도 음색 결정에 사용하지 않는다.

## 기존 재생 계약

- `schedulePhrase(events, millisecondsPerBeat = 625, instrument = 'piano')`는 계속 동기적으로 `{ context, stop }`을 반환한다.
- 시작은 기존과 같이 AudioContext 현재 시각 + 0.06초다. 음 길이는 `durationRatio`이며 쉼표도 시간에 포함한다.
- Query·추천·결과·상세 재생은 인접한 동일 pitch 타이를 합친 후 한 번만 발음한다. 셋잇단음표는 실제 비율을 유지한다.
- 악보 재생 위치 막대·seek·마디 이동·이조는 기존 계산을 유지한다. 음원 로딩을 기다리느라 재생 시작이나 위치 타이머를 미루지 않는다.
- 한 번 시작한 프레이즈는 중간에 로딩이 완료되어도 음색을 바꾸지 않는다. 준비되지 않은 음원은 기존 기본 소리로 재생하고 다음 재생부터 샘플을 사용할 수 있다.
- 정지·재시작·화면 이탈 시 이미 시작한 소리와 앞으로 예약된 소리를 함께 중지한다. Query 변경 중에는 이전 Query 소리를 중지한다.

## 구현 연결

| 파일 | 역할 |
|---|---|
| `src/music/samplePlayback.ts` | 음원 manifest·bank 캐시, 악기 이름/GM program 매핑, 샘플 재생·중지, 기본 소리 선택 |
| `src/music/audioPlayback.ts` | 공유 AudioContext, 사전 로딩·gesture warm, 기존 예약 시계·기본 소리 fallback |
| `src/music/playbackInstrument.ts` | 실제 성부의 part-list 메타데이터 조회, UI 명칭·공유 설정 이벤트 |
| `src/components/PlaybackSoundControl.tsx` | 샘플 음색 설정과 준비/로딩/기본 소리 상태 표시 |
| `src/App.tsx` | Query 재생·사전 준비·중지 |
| `src/components/QuerySuggestions.tsx` | 추천 Query 타이 합산·피아노 사전 준비 |
| `src/components/ResultCard.tsx` | 결과 성부 음색·사전 준비; 기존 재생 위치 표시 보존 |
| `src/components/FullScorePage.tsx` | 상세 악보 실제 재생 성부 음색·상태·기존 seek/이조 연결 |
| `public/samples/` | 네 악기 MP3·manifest·출처/라이선스 |

큰 XML 전체를 새로 DOM 파싱하지 않는다. 악기 선택은 최대 256KiB의 앞부분에서 `<part-list>`만 조회하고, 없는 경우 `partName`으로 대체한다. 영문·한글 악기 이름, Vln./Vla./Vc./Pno. 등을 인식한다. MusicXML `midi-program`은 1-based 값으로 다룬다(41 바이올린, 42 비올라, 43 첼로).

## 로딩·실패·설정

화면에 진입하거나 실제 악기가 바뀌면 해당 음원을 사전 로딩한다. 로딩만으로 AudioContext를 강제 resume하지 않고 사용자 제스처에서 준비한다. 동일 음원의 동시 요청은 하나로 합친다. 자동 재시도 루프는 두지 않으며 실패한 요청은 후속 명시적 준비/재생 시 재시도할 수 있게 한다. 일부 샘플만 실패한 bank도 정상 디코딩한 샘플을 유지하고 누락된 파일만 다시 시도한다. 로딩 실패·잘못된 음원·안전한 샘플 범위 밖의 음은 기본 소리로 대체한다. `ready`는 사용 가능한 샘플이 있다는 뜻이며 모든 음높이가 샘플로 연주된다는 보장은 아니다.

`샘플 악기 소리` 체크를 해제하면 기존 기본 소리를 사용한다. 기본값은 켜짐이며 `musicanote.sampledPlayback` localStorage에 저장한다. 저장소 사용이 불가능하면 세션 내 설정을 유지한다. 설정 변경은 모든 재생 호출부에 전달하여 이전 음색의 소리와 새 설정의 소리가 겹치지 않게 한다.

MP3는 서버의 로컬 정적 자산으로 제공한다. 외부 음원 서비스/API·추가 npm 의존성·검색 DB 동기화는 필요하지 않다. 배포 시 `public/samples`를 누락하지 않아야 한다. Vite의 `BASE_URL`을 반영한다.

## 자산과 한계

- 자산은 80개 파일(78개 MP3 + manifest + README), 총 1,876,285 bytes다. 원출처와 CC BY 3.0/Frank Wen 표기는 `public/samples/README.md`와 manifest에 보존한다.
- 샘플 피치 이동은 가까운 반음 범위로 제한한다. 긴 현악기 음은 pitch rate를 고려해 루프를 적용한다. 샘플을 새로 녹음하거나 라이선스를 재정의한 작업이 아니다.
- 실제 발음은 브라우저·출력 장치별로 다를 수 있다. 목업 AudioContext 테스트는 청취 품질 보증이 아니다.
- 기존 단일 검색 성부의 pitch/time 데이터 계약은 유지한다. 모든 악기의 GM bank, 타악기, 합주 믹싱, MusicXML 전역 tempo/표정/실음 이조의 새 해석은 이 범위에 포함하지 않는다.
- 이번 작업은 외부 YouTube 영상과 악보의 시간 정렬 기능을 추가하지 않는다.

## 재현과 검증

```powershell
pnpm exec vitest run src/music/audioPlayback.test.ts src/music/samplePlayback.test.ts src/music/playbackInstrument.test.ts src/components/PlaybackSoundControl.test.tsx server/sample-assets.test.js --no-file-parallelism
pnpm exec vitest run src/search/features.test.ts src/music/display.test.ts src/music/mei.test.ts src/music/queryImport.test.ts src/music/queryEdit.test.ts src/components/FullXmlNotation.test.ts src/components/FullXmlNotation.render-contract.test.ts src/score-tools/verovioTransposition.integration.test.ts --no-file-parallelism
pnpm exec vitest run src/components/FullScorePage.test.ts -t "full score playback navigation" --no-file-parallelism
pnpm run build
```

최종 검증은 새 음원/상태/자산 63개 + 기존 악보 회귀 55개 + 상세 재생 이동 2개 = 120개 통과다. TypeScript와 production build가 통과했고 실행 중인 Vite에서 manifest·MP3 HTTP 200, `audio/mpeg` 제공과 배포 결과의 80개 자산을 확인했다. 빌드는 기존 Verovio browser-external/큰 chunk 경고를 유지한다.

브라우저 검증 도구는 샌드박스 helper 초기화 오류로 두 차례 연결에 실패했다. 따라서 실제 브라우저 클릭/스크롤/청취 기반 검증은 수행하지 못했다. 목업 테스트와 빌드 성공을 실제 청취 확인으로 표현하지 않는다. `FullScorePage.test.ts` 전체에는 이번 작업 전부터 알려진 Motif 분석 2개 실패가 있으므로 재생 테스트와 구별한다([기존 기록](motif-family-integration.md)).

수동 확인 순서: 타이 Query 한 번 발음 → 쉼표·셋잇단음표 → 결과 재생 위치 → 상세 Play/Stop·seek·1/5마디 이동 → 이조 음높이 → 샘플 체크 on/off → 빠른 정지/재시작·화면 이탈. 첫 재생 로딩 상태와 로드 실패 시에도 재생이 끊기지 않는지 확인한다.
