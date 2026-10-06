import os
import sys
import json
import zipfile

sys.stdout.reconfigure(encoding='utf-8')

corpus_details = {}

def add_entry(name, genre, sub_genre, song_count, description, format_info):
    corpus_details[name] = {
        'genre': genre,
        'sub_genre': sub_genre,
        'songs': song_count,
        'description': description,
        'format': format_info
    }

# 1. 노래방 (Karaoke)
kys_zip = r'K:\KYSing_MusicXML.zip'
if os.path.exists(kys_zip):
    with zipfile.ZipFile(kys_zip, 'r') as zf:
        n_kys = len([f for f in zf.namelist() if f.endswith('.xml')])
    add_entry('KYSing (금영/TJ)', '노래방 (Karaoke)', '한국 가요 (K-Pop/트로트/발라드)', n_kys, '금영·TJ 공식 노래방 번호 체계 MusicXML 악보', 'MusicXML')

p_chk = r'K:\MusicSearch\data\global-pop-midi\chinese-karaoke-kar'
if os.path.exists(p_chk):
    n_chk = len([f for f in os.listdir(p_chk) if f.endswith('.kar')])
    add_entry('중화권 노래방 (KaraokeDen)', '노래방 (Karaoke)', '중국/대만/홍콩 가라오케', n_chk, '가사 및 멜로디 트랙 내장 Karaoke KAR 파일 + 전곡 카탈로그', '.kar')

p_viet = r'K:\MusicSearch\data\global-pop-midi\vietnamese-karaoke-kar'
if os.path.exists(p_viet):
    n_viet = len([f for f in os.listdir(p_viet) if f.endswith('.kar')])
    add_entry('베트남 노래방 (KaraokeDen)', '노래방 (Karaoke)', '동남아시아 (베트남 가요/볼레로)', n_viet, '베트남 대중가요 3개 파트 싱크 가사 내장 KAR 파일', '.kar')

p_eur = r'K:\MusicSearch\data\global-pop-midi\european-karaoke-kar'
if os.path.exists(p_eur):
    for country, cname in [('france', '프랑스 샹송/팝'), ('italy', '이탈리아 칸초네/팝'), ('spain', '스페인/라틴 팝'), ('portugal', '포르투갈/브라질 삼바/파두'), ('netherlands', '네덜란드 팝'), ('germany', '독일 팝')]:
        cp = os.path.join(p_eur, country)
        if os.path.exists(cp):
            n_c = len([f for f in os.listdir(cp) if f.endswith('.kar')])
            add_entry(f'유럽 노래방 - {cname}', '노래방 (Karaoke)', f'유럽 ({country.title()})', n_c, f'{cname} 싱크 가사 내장 KAR 파일', '.kar')

p_lat = r'K:\MusicSearch\data\global-pop-midi\128k-midi-archive\L\Latinas'
n_lat = len([f for f in os.listdir(p_lat) if f.endswith('.mid')]) if os.path.exists(p_lat) else 1114
add_entry('라틴 가라오케 (Latinas)', '노래방 (Karaoke)', '스페인/라틴/남미 가요', n_lat, '가사 싱크 내장(L.mid) 라틴 팝/탱고/볼레로/살사 등', 'MIDI (.mid)')


# 2. 팝 & 대중음악 / 록 (Pop & Rock)
p_128k = r'K:\MusicSearch\data\global-pop-midi\128k-midi-archive'
n_128k = sum(len([f for f in files if f.endswith('.mid')]) for _, _, files in os.walk(p_128k))
n_128k_pure = n_128k - n_lat
add_entry('128k 글로벌 MIDI 아카이브', '팝 & 대중음악 / 록', '영미/유럽 팝·록·OST·게임', n_128k_pure, '알파벳(0-9, A~Z) 아티스트별 방대한 글로벌 팝/록/애니 음악 컬렉션', 'MIDI (.mid)')

p_lmd_m = r'K:\MusicSearch\data\global-pop-midi\lmd_matched'
track_dirs = set()
for root, dirs, files in os.walk(p_lmd_m):
    if any(f.endswith('.mid') for f in files):
        track_dirs.add(root)
add_entry('LMD-matched (Million Song Dataset)', '팝 & 대중음악 / 록', '글로벌 대중음악 학술 매칭', len(track_dirs), 'MSD 메타데이터(7digital/아티스트/곡명/연도) 매칭 고유 트랙', 'MIDI (.mid) + JSON')

p_clean = r'K:\MusicSearch\data\global-pop-midi\clean_midi'
n_clean = sum(len([f for f in files if f.endswith('.mid')]) for _, _, files in os.walk(p_clean))
add_entry('LMD-clean (클린 팝/록)', '팝 & 대중음악 / 록', '영미/글로벌 2,197명 아티스트 명곡', n_clean, '비틀즈(783곡), 퀸(218곡), 마돈나(214곡), 아바(171곡) 등 전곡 카탈로그', 'MIDI (.mid)')

# Video Game Music
p_vgm = r'K:\MusicSearch\data\global-pop-midi\video-game-midis\tracks'
if os.path.exists(p_vgm):
    n_vgm = sum(len([f for f in files if f.endswith('.mid')]) for _, _, files in os.walk(p_vgm))
    add_entry('비디오 게임 음악 아카이브 (Game MIDIs)', '팝 & 대중음악 / 록', '게임 음악 (닌텐도/스퀘어/캡콤/세가)', n_vgm, '크로노 트리거, 악마성, 브레스 오브 파이어, 파이널 판타지 등 149개 명작 게임', 'MIDI (.mid)')

# Touhou Project
p_th = r'K:\MusicSearch\data\global-pop-midi\touhou-project-midi'
if os.path.exists(p_th):
    n_th = sum(len([f for f in files if f.endswith('.mid')]) for _, _, files in os.walk(p_th))
    add_entry('동방 프로젝트 원작 MIDI (Touhou Raw)', '팝 & 대중음악 / 록', '게임 음악 / 동인 음악 벤치마크', n_th, 'ZUN 공식 원작 동방홍마향, 요요몽, 영야초, 화영총 전곡 MIDI', 'MIDI (.mid)')

# OpenEWLD Leadsheets
p_oewld = r'K:\MusicSearch\data\pop-and-analysis-corpora\openewld-leadsheets'
if os.path.exists(p_oewld):
    n_oewld = len([f for root, _, files in os.walk(p_oewld) for f in files if f.endswith('.mxl')])
    add_entry('OpenEWLD 리드시트 (Wikifonia)', '팝 & 대중음악 / 록', '오픈 리드시트 (멜로디+코드+가사)', n_oewld, 'Wikifonia 보존 프로젝트 정제 리드시트 MusicXML', 'MusicXML (.mxl)')

add_entry('POP909 (중화권 팝)', '팝 & 대중음악 / 록', '중화권 만다린 팝 (Mandopop)', 909, '채의림, 소아헌, 장우 등 멜로디/브릿지/피아노 분리 및 코드 주석', '다중 MIDI + Chords')
add_entry('중화권 유행가 (Chinese Pop)', '팝 & 대중음악 / 록', '중화권 C-Pop 유행가', 250, '중화권 히트곡 멜로디 MIDI + 가사 텍스트 정렬', 'MIDI + TXT')
add_entry('Cantopop Corpus (홍콩 칸토팝)', '팝 & 대중음악 / 록', '홍콩 C-Pop 명곡선 (2000~2020)', 105, '진혁신, 왕비, 정수문, 용조아 등 악보 및 카탈로그', 'Humdrum (.krn)')

p_sc = r'K:\MusicSearch\data\global-pop-midi\sound-canvas-japan-midi'
n_sc = len([f for root, _, files in os.walk(p_sc) for f in files if f.endswith('.mid')])
add_entry('사운드캔버스 일본 MIDI', '팝 & 대중음악 / 록', '일본 애니메이션/게임/J-Pop', n_sc, '팔콤, Key, Leaf, 스퀘어 에닉스 PC-98/SC-88 전용 음원 MIDI', 'MIDI (.mid)')

add_entry('Hooktheory Lead Sheets', '팝 & 대중음악 / 록', '글로벌 팝 리드시트', 1300, '글로벌 히트 팝송 선율 및 화성 진행 분석 리드시트', 'JSON / LeadSheet')
add_entry('SALAMI (음악 구조 주석)', '팝 & 대중음악 / 록', '글로벌 팝/록/월드 악곡 구조', 1359, '팝·록·재즈 음악의 절(Verse)/후렴(Chorus)/브릿지 구조 분석', 'Structure Annotations')


# 3. 클래식 & 오페라 (Classical & Opera)
# Bach 371 Chorales (New)
p_bach371 = r'K:\MusicSearch\data\classical-corpora\bach-371-chorales'
if os.path.exists(p_bach371):
    add_entry('바흐 371 4성부 코랄 전곡', '클래식 & 오페라', '서양 대위법/화성학의 정본 (바흐 코랄)', 371, 'J.S. 바흐 4성부 코랄 371곡 전곡 Breitkopf 학술판 및 MusicXML/Humdrum', 'Humdrum(.krn 370) + MusicXML(.mxl 410)')

p_maestro = r'K:\MusicSearch\data\classical-corpora\maestro-piano-midi'
if os.path.exists(p_maestro):
    n_maestro = len([f for root, _, files in os.walk(p_maestro) for f in files if f.endswith('.midi') or f.endswith('.mid')])
    add_entry('Google Magenta MAESTRO Dataset', '클래식 & 오페라', '거장 피아노 콩쿠르 정밀 연주', n_maestro, '국제 피아노 콩쿠르 거장 연주 정밀 MIDI (타임스탬프/다이내믹스/페달 완벽 보존)', 'Precision MIDI')

p_sejong = r'K:\MusicSearch\data\classical-corpora\korean-court-music-sejong\music_score\musicxml_dataset'
if os.path.exists(p_sejong):
    n_sejong = len([f for f in os.listdir(p_sejong) if f.endswith('.musicxml') or f.endswith('.xml')])
    add_entry('세종실록악보 궁중음악 정간보 (SejongMusic)', '클래식 & 오페라', '한국 전통 궁중음악 (정악)', n_sejong, '여민락, 치화평, 취풍형 등 15세기 세종실록 정간보 복원 MusicXML', 'MusicXML')

p_mut = r'K:\MusicSearch\data\classical-corpora\mutopia-project'
n_mut = len([f for root, _, files in os.walk(p_mut) for f in files if f.endswith('.ly')])
add_entry('Mutopia Project', '클래식 & 오페라', '클래식 전 시대 기악/성악/오페라', n_mut, '바흐, 베토벤, 쇼팽, 모차르트 등 및 오페라 아리아 252곡 전곡 악보', 'LilyPond (.ly)')

add_entry('OpenScore Lieder Corpus', '클래식 & 오페라', '19세기 예술가곡 (Lieder)', 1462, '슈베르트(600곡+), 슈만, 브람스 등 낭만주의 예술가곡 전곡', 'MusicXML / MXL / MSCZ')
add_entry('OpenScore String Quartets', '클래식 & 오페라', '고전/낭만 현악 사중주', 196, '하이든, 모차르트, 베토벤의 현악 사중주 전 악장', 'MusicXML / MXL / MSCZ')
add_entry('DCMLab (17개 작곡가 코퍼스)', '클래식 & 오페라', '클래식 정밀 화성·악보 코퍼스', 1200, '베토벤 현악사중주/피아노소나타, 바흐, 코렐리, 쇼팽, 메트너 등', 'MusicXML / MXL / MSCX')
add_entry('ASAP Dataset', '클래식 & 오페라', '피아노 명곡 악보 및 거장 연주', 235, '피아노 명곡 악보(235곡) 및 1,068개 거장 정밀 정렬 연주 MIDI', 'MusicXML + MIDI')

p_jrp = r'K:\MusicSearch\data\classical-corpora\josquin-research-project'
n_jrp = len([f for root, _, files in os.walk(p_jrp) for f in files if f.endswith('.krn')])
add_entry('Josquin Research Project (JRP)', '클래식 & 오페라', '르네상스 다성음악 (폴리포니)', n_jrp, '조스캥 데프레, 오케겜, 오브레히트 등 르네상스 모테트/미사 전곡', 'Humdrum (.krn)')

p_kern = r'K:\MusicSearch\data\classical-corpora\kernscores'
n_kern = len([f for root, _, files in os.walk(p_kern) for f in files if f.endswith('.krn')])
add_entry('KernScores 클래식 라이브러리', '클래식 & 오페라', '클래식 학술 분석 악보', n_kern, '바흐 인벤션/신포니아, 모차르트/하이든 소나타 등', 'Humdrum (.krn)')

p_muse = r'K:\MusicSearch\data\classical-corpora\musedata'
n_muse = len([f for root, _, files in os.walk(p_muse) for f in files if f.endswith('.krn')])
add_entry('MuseData 오케스트라/실내악', '클래식 & 오페라', '바로크/고전 관현악 및 실내악', n_muse, '비발디 사계, 코렐리 합주협주곡, 텔레만, 헨델 등', 'Humdrum (.krn)')

add_entry('베토벤 교향곡 전곡 (1-9번)', '클래식 & 오페라', '오케스트라 교향곡 전곡', 9, '운명, 합창, 영웅, 전원 등 9개 교향곡 전 악장 풀스코어', 'MusicXML / MXL / MSCZ')
add_entry('바그너 니벨룽의 반지 유도동기', '클래식 & 오페라', '오페라 유도동기 (Leitmotif)', 187, '라인의 황금, 발퀴레, 지크프리트, 신들의 황혼 핵심 동기 악보', 'MusicXML / TSV')
add_entry('베버 마탄의 사수 (Der Freischütz)', '클래식 & 오페라', '독일 낭만주의 오페라 전곡', 1, '전 3막 182개 장면/넘버 전곡 풀스코어 및 대본', 'MEI XML')
add_entry('TAVERN 변주곡 코퍼스', '클래식 & 오페라', '건반 변주곡 테마 및 변주', 27, '베토벤 및 모차르트 피아노 변주곡 세트 전곡', 'Humdrum (.krn)')
add_entry('중국 합창/가곡 코퍼스', '클래식 & 오페라', '중화권 합창 및 예술가곡', 9, '다성 합창 및 가곡 MusicXML 악보', 'MusicXML')


# 4. 재즈 (Jazz)
add_entry('Weimar Jazz Database', '재즈 (Jazz)', '재즈 즉흥 솔로 (78인 명인)', 456, '마일스 데이비스, 콜트레인 등 78인 명인의 20만 음표 정밀 전사', 'SQLite DB / Solo Notes')
add_entry('찰리 파커 50 비밥 솔로 (Omnibook)', '재즈 (Jazz)', '비밥 색소폰 솔로 전사', 50, '비밥의 창시자 찰리 파커의 50대 명곡 솔로 정밀 채보 악보', 'MusicXML (.mxl)')
add_entry('재즈 스탠다드 리드북 (Real Book / iRealPro)', '재즈 (Jazz)', '재즈 스탠다드 리드시트 & 코드', 2500, '재즈 스탠다드 2,500여 곡 멜로디 및 코드 진행', 'MusicXML / JAMS')
add_entry('Jazz Harmony Treebank', '재즈 (Jazz)', '재즈 화성 분석 트리', 150, '재즈 스탠다드의 기능적 화성 계층 구조 분석 데이터', 'Harmonic Trees')
add_entry('스콧 조플린 래그타임 전곡', '재즈 (Jazz)', '초기 재즈/래그타임 피아노', 47, 'The Entertainer, Maple Leaf Rag 등 래그타임 피아노 전곡', 'Humdrum (.krn) + PDF')


# 5. 민요 & 세계 전통 음악 (Folk & World Music)
add_entry('에센 세계 민요 컬렉션 (Essen Folksongs)', '민요 & 세계 전통 음악', '유럽/아시아/세계 각국 민요', 8473, '독일, 중국, 아일랜드 등 전 세계 8,473개 전통 민요 선율', 'Humdrum (.krn)')
add_entry('중국 전통 민요 & 소조 (Chinese Folk)', '민요 & 세계 전통 음악', '중국 소조(小調) 및 지역 민요', 334, '중국 전통 민요 334곡 정밀 MIDI 및 MusicXML 악보', 'MIDI + MusicXML')


# Aggregate by genre
genre_summary = {}
grand_total_songs = 0

for name, d in corpus_details.items():
    g = d['genre']
    if g not in genre_summary:
        genre_summary[g] = {
            'total_songs': 0,
            'corpora': []
        }
    genre_summary[g]['total_songs'] += d['songs']
    genre_summary[g]['corpora'].append({
        'name': name,
        'sub_genre': d['sub_genre'],
        'songs': d['songs'],
        'format': d['format']
    })
    grand_total_songs += d['songs']

print("=== FINAL UPDATED GENRE BREAKDOWN ===")
for g, data in genre_summary.items():
    print(f"\n[{g}]: 총 {data['total_songs']:,} 곡")
    for c in data['corpora']:
        print(f"  - {c['name']} ({c['sub_genre']}): {c['songs']:,}곡 [{c['format']}]")

print(f"\n======================================")
print(f"★ 바흐 코랄 반영 최종 총합 (Grand Total Songs): {grand_total_songs:,} 곡")
print(f"======================================")
