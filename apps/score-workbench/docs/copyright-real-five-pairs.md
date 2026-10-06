# 제공된 실제 음악 5쌍 — 검사 방향·근거·DB 구성

## 확인한 자료

K:/Copyright Infringement Case에서 5개 폴더, MusicXML 10개 및 PNG/PDF/Sibelius/Pages 보조 자료를 확인했다.
이번에는 파일 목록과 MusicXML XML 구조만 읽었고 PNG/PDF/Pages의 주석 내용은 아직 판독하지 않았다.
원본 악보는 변경하거나 웹으로 공개하지 않았다. 인터넷 자료를 검색한 것이며 음악 검색 엔진 검사는 아직 실행하지 않았다.

| 검사 입력 | 비교 참조곡 | 제공 XML 마디 수(입력/참조) |
|---|---|---:|
| Green Day — 21 Guns | Electric Light Orchestra — Telephone Line | 106/73 |
| Chuck Berry — Johnny B. Goode | Louis Jordan — Ain't That Just Like a Woman | 86/64 |
| David Guetta — When Love Takes Over | Coldplay — Clocks | 100/162 |
| Lemon19 — Twinkle | SISTAR19 — Ma Boy | 69/74 |
| Green Day — Jesus of Suburbia | Bryan Adams — Summer of '69 | 387/100 |

모두 XML part 하나를 갖지만 여러 staff/voice가 있을 수 있다. part 수를 단선율이라는 뜻으로 해석하지 않는다.
마디 수는 XML 첫 part의 measure element 개수이며 표시 마디 번호와 다를 수 있다.

## 자료의 의미

검사 방향은 발매 순서와 공개 유사성 비교를 바탕으로 정했다. 이 5쌍을 법원이 인정한 침해 정답 세트로 취급하지 않는다.
이 조사에서 해당 쌍에 대한 침해 확정 판결을 확보하지 못했다는 뜻이지 소송이 전혀 없었다는 보증은 아니다.

- 21 Guns/Telephone Line: [청취 비교 기록](https://www.soundsjustlike.com/82/green-day-sounds-like-electric-light-orchestra/). 비교의 방향/발매 선후 근거이며 법률 판정은 아니다.
- Johnny B. Goode: [1987년 다큐 인터뷰 전사](https://clip.cafe/chuck-berry-hail-hail-rock-n-roll-1987/they-say-thats-a-chuck-berry-song-theres/t/4)에서 Carl Hogan 등을 결합한 영향 관계를 설명한다. [관련 리프 분석 소개](https://guitarsexchange.com/en/psych-out/594/the-10-chuck-berry-intros-that-every-guitar-player-should-learn/)도 참고. 영향 인정과 무허락 침해 확정을 구분한다.
- When Love Takes Over/Clocks: [피아노 유사성에 대한 매체 논평](https://www.virageradio.com/news/rock/12579/coldplay-david-guetta-aurait-il-plagi-clocks). 공통 음형·리듬만으로 과잉 경고하지 않는지 시험할 사례다.
- Twinkle: [Genie 발매 정보](https://www.genie.co.kr/detail/albumInfo?axnm=80869129)로 Lemon19의 2016년 곡임을 확인. 소녀시대 Twinkle이나 동요와 구분. [기존 Musicanote 주석](https://musicanote.com/score/detail/508)은 Twinkle 14–16마디와 Ma Boy 10–12마디의 유사성을 설명한다. 이는 기존 분석 주석이지 독립적인 판결 근거가 아니다. 로컬 XML의 마디 좌표와 대응되는지는 추후 확인한다.
- Jesus of Suburbia: [MusicRadar 논평](https://www.musicradar.com/artists/i-used-everything-i-knew-about-music-how-green-day-exceeded-expectations-with-their-most-ambitious-song)이 두 번째 부분의 Summer of '69 연관을 언급한다. 짧은 부분을 전곡으로 과장하지 않는지 시험한다.

## 기존 DB 읽기 전용 확인

영문 title 부분 일치 검색 기준(표기 변형으로 놓칠 수 있음):
- Clocks: 기존 XML 여러 판본과 KY 존재.
- Ma Boy: SISTAR19 KY 76909 존재. Ma Boy 2/3는 다른 곡이므로 섞지 않는다.
- Summer of '69: Bryan Adams KY 08685 존재.
- Telephone Line / Ain't That Just Like a Woman: 해당 영문 title 검색에서 미발견. 완전한 부재 확정은 아님.
- 검사 입력도 이미 21 Guns KY 60923, Johnny B. Goode 여러 XML 판본, Twinkle(Lemon19) KY 76319가 존재한다.
- When Love Takes Over / Jesus of Suburbia는 동일 title 검색에서 미발견.

동일 곡이라는 제목/아티스트 확인과 제공 XML의 동일 판본 여부는 다르다.
현재 DB에 있는 입력곡 판본은 검사 세션에서 제외해야 자기 자신을 찾는 결과로 평가를 왜곡하지 않는다.
운영 DB 레코드를 삭제하지 않는다. 다른 곡인 Ma Boy 2/3, Johnny Boyle's Jig, 소녀시대 Twinkle 등을 제목 일부만 같다는 이유로 제외하지 않는다.

## 권고: 비공개 검증 레이어

1. 먼저 참조곡 5개만 담은 작은 별도 인덱스로 파싱/성부/구간 대응을 점검한다. 다섯 입력은 업로드 전용으로 분리한다.
2. 이후 기존 대규모 corpus와 이 참조 5개의 별도 레이어를 함께 검색한다. 최종 비교 점수는 공통 기준으로 재계산하고, 레이어별 top1을 임의 합산하거나 정답 곡에 가산점을 주지 않는다.
3. 작은 5곡 DB 성과와 전체 corpus 성과를 따로 기록한다. 희귀도/통계 점수는 작은 DB에서 왜곡되므로 운영 코퍼스 기준 또는 미확인으로 둔다.
4. 참조의 기존 판본이 있더라도 제공 XML은 검증용 정확 판본으로 유지할 가치가 있다. 운영 DB에 덮어쓰지 않는다.
5. 원본 공개·상용 인덱스 영구 편입은 악보 사용 범위를 확인한 뒤 별도 결정한다.
6. full-score 검사와 기존 주석 구간 검사는 분리한다. 주석은 evaluator만 보고 검출기의 구간 선택/순위에는 주입하지 않는다.

아직 인덱스를 새로 만들거나 운영 DB에 추가하지 않았다.
검사 방향/로컬 경로/기존 입력 제외 후보/자료 URL은 evaluation/real-cases/five-pairs/manifest.json에 보존했다.
다음은 10개 XML의 실제 parser/renderer 검사 → 참조 5곡 격리 index → 입력 5곡 전곡 검사다.

