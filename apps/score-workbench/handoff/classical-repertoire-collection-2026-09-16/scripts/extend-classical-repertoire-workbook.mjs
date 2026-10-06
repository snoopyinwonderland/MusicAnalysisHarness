import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const [sourcePath, outputPath, previewDir] = process.argv.slice(2);
if (!sourcePath || !outputPath || !previewDir) throw new Error('Usage: node extend-classical-repertoire-workbook.mjs <source.xlsx> <output.xlsx> <preview-dir>');

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
await fs.mkdir(previewDir, { recursive: true });
const before = await workbook.render({ sheetName: '우선 등록', range: 'A1:H35', scale: 1.2, format: 'png' });
await fs.writeFile(`${previewDir}/before-summary.png`, new Uint8Array(await before.arrayBuffer()));

const navy='#20364B', blue='#315B75', cream='#F5F1E8', gold='#C99A3D', lightBlue='#E8F0F4', lightGold='#F8EBCB', lightRed='#F6DEDA', green='#DDEBDD';
const title=(sheet,range,text)=>{sheet.getRange(range).merge();sheet.getRange(range.split(':')[0]).values=[[text]];sheet.getRange(range).format={fill:navy,font:{name:'Arial',size:15,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:30};};
const header=range=>{range.format={fill:blue,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:32,borders:{preset:'inside',style:'thin',color:'#FFFFFF'}};};
const finish=(sheet,range,widths,freeze=2)=>{sheet.showGridLines=false;sheet.getRange(range).format.verticalAlignment='center';sheet.getRange(range).format.wrapText=true;for(const [col,width] of Object.entries(widths))sheet.getRange(`${col}:${col}`).format.columnWidth=width;sheet.freezePanes.freezeRows(freeze);};
const addTable=(sheet,range,name)=>{sheet.tables.add(range,true,name).style='TableStyleMedium2';};

const supplements = [
 ['B','초기 낭만주의',1805,1847,'Fanny Mendelssohn','독일','여성 작곡가','Das Jahr; Piano Trio in D minor, Op. 11','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','초기 낭만주의',1804,1875,'Louise Farrenc','프랑스','여성 작곡가','Symphony No. 3; Nonet, Op. 38','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','후기 낭만주의',1867,1944,'Amy Beach','미국','여성·미국','Gaelic Symphony; Piano Concerto','관할별 검토','Wikidata·Library of Congress 검증 필요'],
 ['B','20세기',1887,1953,'Florence Price','미국','여성·흑인 작곡가','Symphony No. 1; Adoration','관할별 검토','Wikidata·Library of Congress 검증 필요'],
 ['B','후기 낭만주의',1858,1944,'Ethel Smyth','영국','여성 작곡가','The Wreckers; Mass in D','관할별 검토','IMSLP·Wikidata 검증 필요'],
 ['B','20세기',1893,1918,'Lili Boulanger','프랑스','여성 작곡가','D’un matin de printemps; Psalm 130','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','20세기',1892,1983,'Germaine Tailleferre','프랑스','여성 작곡가','Piano Concerto No. 1; Harp Concertino','권리 검토','Wikidata·권리자 검증 필요'],
 ['B','20세기',1886,1979,'Rebecca Clarke','영국·미국','여성 작곡가','Viola Sonata','권리 검토','Wikidata·권리자 검증 필요'],
 ['B','20세기',1901,1953,'Ruth Crawford Seeger','미국','여성·미국','String Quartet 1931','관할별 검토','Wikidata·권리자 검증 필요'],
 ['B','20세기',1895,1978,'William Grant Still','미국','흑인 작곡가','Afro-American Symphony','권리 검토','Wikidata·권리자 검증 필요'],
 ['B','후기 낭만주의',1875,1912,'Samuel Coleridge-Taylor','영국','흑인 작곡가','Hiawatha’s Wedding Feast','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','고전주의',1745,1799,'Joseph Bologne, Chevalier de Saint-Georges','프랑스·과들루프','카리브·흑인 작곡가','Violin Concertos; Symphonies concertantes','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','후기 낭만주의',1860,1941,'Ignacy Jan Paderewski','폴란드','중동부 유럽','Minuet in G; Piano Concerto','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','고전주의',1752,1832,'Muzio Clementi','이탈리아·영국','교육 레퍼토리','Gradus ad Parnassum; Piano Sonatas','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','고전주의',1760,1812,'Jan Ladislav Dussek','체코','중동부 유럽','Piano Sonatas; Piano Concertos','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','고전주의',1747,1818,'Leopold Koželuch','체코','중동부 유럽','Keyboard Sonatas; Piano Concertos','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','고전주의',1739,1799,'Carl Ditters von Dittersdorf','오스트리아','고전주의 보완','Symphonies after Ovid','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','고전주의',1749,1801,'Domenico Cimarosa','이탈리아','오페라 보완','Il matrimonio segreto','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['C','낭만주의',1850,1900,'Zdeněk Fibich','체코','중동부 유럽','Poème; Šárka','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','초기 낭만주의',1804,1857,'Mikhail Glinka','러시아','러시아 음악사','Ruslan and Lyudmila Overture','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','후기 낭만주의',1880,1951,'Nikolai Medtner','러시아','피아노 레퍼토리','Forgotten Melodies; Piano Sonatas','관할별 검토','IMSLP·Wikidata 검증 필요'],
 ['B','낭만주의',1842,1912,'Mykola Lysenko','우크라이나','우크라이나','Taras Bulba; Piano and vocal works','퍼블릭 도메인 후보','IMSLP·Wikidata 검증 필요'],
 ['B','20세기',1893,1987,'Federico Mompou','스페인','이베리아','Música callada','권리 검토','권리자·Wikidata 검증 필요'],
 ['B','20세기',1882,1949,'Joaquín Turina','스페인','이베리아','Danzas fantásticas','관할별 검토','IMSLP·Wikidata 검증 필요'],
 ['B','20세기',1899,1940,'Silvestre Revueltas','멕시코','라틴아메리카','Sensemayá','관할별 검토','Wikidata·권리자 검증 필요'],
 ['C','전후 현대음악',1953,null,'Takashi Yoshimatsu','일본','동아시아','Memo Flora Concerto; Symphony No. 5','권리 검토','공식 사이트·권리자 검증 필요'],
 ['B','전후 현대음악',1917,1995,'Isang Yun','한국·독일','한국·동아시아','Réak; Cello Concerto','권리 검토','윤이상 관련 공식 아카이브 검증 필요'],
 ['C','전후 현대음악',1914,2006,'Akira Ifukube','일본','동아시아','Japanese Rhapsody; film music','권리 검토','공식 카탈로그·권리자 검증 필요'],
 ['B','전후 현대음악',1953,null,'Chen Yi','중국·미국','여성·동아시아','Duo Ye; Momentum','권리 검토','공식 사이트·권리자 검증 필요'],
 ['A','전후 현대음악',1957,null,'Tan Dun','중국·미국','동아시아','Water Concerto; Crouching Tiger, Hidden Dragon','권리 검토','공식 사이트·권리자 검증 필요']
];

const supplementSheet=workbook.worksheets.add('보완 작곡가');
title(supplementSheet,'A1:L1','보완 작곡가 수집 큐');
supplementSheet.getRange('A2:L2').values=[['제안 등급','시대','출생','사망','작곡가','지역','보완 목적','대표 작품','권리 1차 분류','검증 메모','수집 상태','담당 메모']];header(supplementSheet.getRange('A2:L2'));
supplementSheet.getRange(`A3:L${supplements.length+2}`).values=supplements.map(r=>[...r,'대기','']);
addTable(supplementSheet,`A2:L${supplements.length+2}`,'SupplementComposersTable');
supplementSheet.getRange(`K3:K${supplements.length+2}`).dataValidation={rule:{type:'list',values:['대기','검증 중','검증 완료','XML 수집 중','등록 완료','보류']}};
supplementSheet.getRange(`A3:A${supplements.length+2}`).conditionalFormats.add('containsText',{text:'A',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});
supplementSheet.getRange(`A3:A${supplements.length+2}`).conditionalFormats.add('containsText',{text:'B',format:{fill:lightGold,font:{bold:true,color:'#6B5018'}}});
finish(supplementSheet,`A1:L${supplements.length+2}`,{A:11,B:16,C:9,D:9,E:32,F:18,G:22,H:48,I:20,J:35,K:14,L:28});

const catalogues=[
 ['Johann Sebastian Bach','S','BWV','Bach-Werke-Verzeichnis','Bach Digital smart','https://smart.bach-digital.de/','연구 기반 작품 검색','확인'],
 ['Wolfgang Amadeus Mozart','S','K / KV','Köchel-Verzeichnis; Neue Mozart-Ausgabe','Digital Mozart Edition','https://dme.mozarteum.at/DME/nma/start.php?l=2','악보·비평 보고서의 대량 재사용 제한 확인','확인'],
 ['Ludwig van Beethoven','S','Op.; WoO; Unv','Kinsky-Halm catalogue and updates','Beethoven-Haus Bonn','https://www.beethoven.de/en/work/search','작품 번호·날짜·자료 검색','확인'],
 ['Franz Schubert','S','D','Deutsch catalogue','Schubert Online','https://schubert-online.at/activpage/index.php?lang=E','자필·초판 이미지 중심','확인'],
 ['Franz Joseph Haydn','S','Hob.','Hoboken catalogue','RISM·IMSLP 교차검증','https://rism.online/','전용 공개 권위 DB 추가 조사','조사 필요'],
 ['Antonio Vivaldi','S','RV','Ryom-Verzeichnis','RISM·IMSLP 교차검증','https://rism.online/','RV 최신판과 원전 식별 검증','조사 필요'],
 ['George Frideric Handel','S','HWV','Händel-Werke-Verzeichnis','RISM·IMSLP 교차검증','https://rism.online/','HWV와 판본 식별 검증','조사 필요'],
 ['Felix Mendelssohn','S','MWV / Op.','Mendelssohn-Werkverzeichnis','RISM·IMSLP 교차검증','https://rism.online/','MWV 범위 검증','조사 필요'],
 ['Frédéric Chopin','S','Op.; B; KK','다중 카탈로그','Fryderyk Chopin Institute','https://chopin.nifc.pl/en/','복수 카탈로그 매핑 필요','조사 필요'],
 ['Robert Schumann','S','Op.; WoO','작품번호·무번호 작품','Schumann Portal','https://www.schumann-portal.de/','전작 테이블 제공 여부 조사','조사 필요'],
 ['Franz Liszt','S','S; LW','Searle / Liszt-Werkverzeichnis','IMSLP·RISM 교차검증','https://imslp.org/wiki/Category:Liszt,_Franz','편곡·원곡 관계 별도 관리','조사 필요'],
 ['Giuseppe Verdi','S','Op. 비중 낮음','오페라·성악 작품 중심','IMSLP·RISM 교차검증','https://imslp.org/wiki/Category:Verdi,_Giuseppe','판본·오페라 번호 체계 조사','조사 필요'],
 ['Richard Wagner','S','WWV','Wagner-Werk-Verzeichnis','IMSLP·RISM 교차검증','https://imslp.org/wiki/Category:Wagner,_Richard','WWV 검증','조사 필요'],
 ['Johann Strauss Jr','S','Op.','작품번호 중심','IMSLP·RISM 교차검증','https://imslp.org/wiki/Category:Strauss_Jr.,_Johann','동명 작품·편곡 구분','조사 필요'],
 ['Johannes Brahms','S','Op.; WoO','작품번호·무번호 작품','Brahms-Institut','https://brahms-institut.de/','작품 DB 접근 방식 조사','조사 필요'],
 ['Pyotr Ilyich Tchaikovsky','S','Op.; TH','Tchaikovsky Handbook catalogue','Tchaikovsky Research','https://en.tchaikovsky-research.net/','TH 번호·편곡 관계 검증','조사 필요'],
 ['Antonín Dvořák','S','Op.; B','Burghauser catalogue','Dvořák official site','https://www.antonin-dvorak.cz/en/','B 번호 검증','조사 필요'],
 ['Giacomo Puccini','S','Op. 비중 낮음','오페라·성악 작품 중심','Centro Studi Giacomo Puccini','https://www.puccinimuseum.org/en/','공식 전작 DB 조사','조사 필요'],
 ['Gustav Mahler','S','작품명 중심','교향곡·가곡 작품 목록','Mahler Foundation','https://mahlerfoundation.org/','판본·초고 구분 조사','조사 필요'],
 ['Claude Debussy','S','L','Lesure catalogue','Centre de documentation Claude Debussy','https://www.debussy.fr/','L 번호 판본 확인','조사 필요'],
 ['Maurice Ravel','S','M','Marcel Marnat catalogue','IMSLP·RISM 교차검증','https://imslp.org/wiki/Category:Ravel,_Maurice','편곡·관현악판 관계 관리','조사 필요'],
 ['Igor Stravinsky','S','K / 작품명','작품명·개정판 중심','Paul Sacher Stiftung 등','https://www.fondation-sacher.org/','현대 판본과 권리 별도 검토','조사 필요'],
 ['George Gershwin','S','작품명 중심','무대·관현악·가곡 목록','Library of Congress','https://www.loc.gov/collections/george-and-ira-gershwin-collection/','저작권과 편곡판 검토','조사 필요']
];
const catSheet=workbook.worksheets.add('전작 카탈로그');title(catSheet,'A1:I1','S등급 작곡가 전작 카탈로그 연결');
catSheet.getRange('A2:I2').values=[['작곡가','등급','약호','카탈로그','우선 출처','URL','사용 메모','확인 상태','내부 매핑 상태']];header(catSheet.getRange('A2:I2'));
catSheet.getRange(`A3:I${catalogues.length+2}`).values=catalogues.map(r=>[...r,'미연결']);addTable(catSheet,`A2:I${catalogues.length+2}`,'CompleteCatalogueTable');
catSheet.getRange(`H3:H${catalogues.length+2}`).dataValidation={rule:{type:'list',values:['확인','조사 필요','접근 제한','대체 출처 필요']}};
catSheet.getRange(`I3:I${catalogues.length+2}`).dataValidation={rule:{type:'list',values:['미연결','식별자 매핑 중','부분 연결','완료']}};
finish(catSheet,`A1:I${catalogues.length+2}`,{A:29,B:8,C:14,D:34,E:31,F:56,G:38,H:14,I:16});

const representative=[
 ['바로크','Johann Pachelbel','Canon and Gigue in D major','합주·대중 인지도','A','퍼블릭 도메인 후보'],['바로크','Tomaso Albinoni','Oboe Concertos','바로크 관악','B','퍼블릭 도메인 후보'],['바로크','Jean-Joseph Mouret','Rondeau from Suite de symphonies','의식·교육','B','퍼블릭 도메인 후보'],['고전주의','Luigi Boccherini','Minuet, Op. 11 No. 5','실내악','A','퍼블릭 도메인 후보'],['고전주의','Leopold Mozart','Toy Symphony','교육·관현악','B','작곡자 귀속 검증'],['고전주의','Muzio Clementi','Sonatinas, Op. 36','피아노 교육','A','퍼블릭 도메인 후보'],['초기 낭만주의','Fanny Mendelssohn','Das Jahr','피아노·여성 작곡가','A','퍼블릭 도메인 후보'],['낭만주의','Jacques Offenbach','Orpheus in the Underworld: Can-Can','오페레타','A','퍼블릭 도메인 후보'],['낭만주의','Léo Delibes','Coppélia','발레','A','퍼블릭 도메인 후보'],['낭만주의','Amilcare Ponchielli','Dance of the Hours','오페라·관현악','A','퍼블릭 도메인 후보'],['낭만주의','Émile Waldteufel','The Skaters’ Waltz','왈츠','B','퍼블릭 도메인 후보'],['낭만주의','Bedřich Smetana','The Moldau','민족주의 관현악','A','퍼블릭 도메인 후보'],['후기 낭만주의','Paul Dukas','The Sorcerer’s Apprentice','관현악','A','퍼블릭 도메인 후보'],['후기 낭만주의','Pietro Mascagni','Cavalleria rusticana','오페라','A','퍼블릭 도메인 후보'],['후기 낭만주의','Ruggero Leoncavallo','Pagliacci','오페라','A','퍼블릭 도메인 후보'],['후기 낭만주의','Engelbert Humperdinck','Hänsel und Gretel','오페라','B','퍼블릭 도메인 후보'],['후기 낭만주의','Samuel Coleridge-Taylor','Hiawatha’s Wedding Feast','합창','B','퍼블릭 도메인 후보'],['20세기','Erik Satie','Gymnopédies','피아노','A','퍼블릭 도메인 후보'],['20세기','Gustav Holst','The Planets','관현악','A','관할별 검토'],['20세기','Carl Orff','Carmina Burana','합창·관현악','A','권리 검토'],['20세기','Florence Price','Symphony No. 1','교향곡·여성 작곡가','A','관할별 검토'],['20세기','William Grant Still','Afro-American Symphony','교향곡·흑인 작곡가','A','권리 검토'],['20세기','Silvestre Revueltas','Sensemayá','라틴아메리카','A','관할별 검토'],['20세기','Federico Mompou','Música callada','피아노','A','권리 검토'],['20세기','Joaquín Rodrigo','Concierto de Aranjuez','기타 협주곡','A','권리 검토'],['20세기','Aram Khachaturian','Sabre Dance','발레','A','권리 검토'],['20세기','Samuel Barber','Adagio for Strings','현악','A','권리 검토'],['20세기','Benjamin Britten','The Young Person’s Guide to the Orchestra','교육·관현악','A','권리 검토'],['전후 현대음악','Isang Yun','Réak','한국 현대음악','B','권리 검토'],['전후 현대음악','Tōru Takemitsu','November Steps','동아시아 현대음악','A','권리 검토'],['전후 현대음악','Tan Dun','Water Concerto','동아시아 현대음악','A','권리 검토'],['전후 현대음악','Chen Yi','Duo Ye','여성·동아시아','B','권리 검토']
];
const repSheet=workbook.worksheets.add('대표작 큐');title(repSheet,'A1:I1','대표작 중심 등록 큐');
repSheet.getRange('A2:I2').values=[['시대','작곡가','대표 작품','선정 이유','제안 우선순위','권리 1차 분류','출처 검증','XML 상태','메모']];header(repSheet.getRange('A2:I2'));
repSheet.getRange(`A3:I${representative.length+2}`).values=representative.map(r=>[...r,'필요','미확인','']);addTable(repSheet,`A2:I${representative.length+2}`,'RepresentativeWorksTable');
repSheet.getRange(`G3:G${representative.length+2}`).dataValidation={rule:{type:'list',values:['필요','검증 중','완료']}};repSheet.getRange(`H3:H${representative.length+2}`).dataValidation={rule:{type:'list',values:['미확인','보유','부분 보유','미보유','권리 검토']}};
finish(repSheet,`A1:I${representative.length+2}`,{A:16,B:29,C:48,D:26,E:14,F:20,G:13,H:14,I:28});

const education=[
 ['피아노 교육','초급','Johann Sebastian Bach / Christian Petzold','Minuet in G major, BWV Anh. 114','리듬·프레이즈·장식음','판본과 작곡자 귀속 확인'],['피아노 교육','초중급','Johann Sebastian Bach','Two-Part Inventions','대위법·동기','15곡 전곡'],['피아노 교육','중급 이상','Johann Sebastian Bach','The Well-Tempered Clavier','조성·대위법','48곡과 판본'],['피아노 교육','초중급','Muzio Clementi','Sonatinas, Op. 36','고전 형식·아티큘레이션','6곡'],['피아노 교육','중급','Wolfgang Amadeus Mozart','Piano Sonatas','고전 형식·프레이징','전곡 우선'],['피아노 교육','중급 이상','Ludwig van Beethoven','Piano Sonatas','형식·동기 발전','32곡'],['피아노 교육','초중급','Robert Schumann','Album for the Young, Op. 68','성격 소품','전곡'],['피아노 교육','초중급','Pyotr Ilyich Tchaikovsky','Album for the Young, Op. 39','성격 소품','전곡'],['피아노 교육','초중급','Friedrich Burgmüller','25 Études faciles et progressives, Op. 100','기초 테크닉','전곡'],['피아노 교육','중급','Carl Czerny','The School of Velocity, Op. 299','테크닉','교육적 가치와 검색 활용 분리'],['피아노 교육','중급 이상','Frédéric Chopin','Preludes, Op. 28','조성·성격','24곡'],['피아노 교육','고급','Frédéric Chopin','Études, Op. 10 and Op. 25','테크닉·동기','24곡'],['피아노 교육','초중급','Béla Bartók','Mikrokosmos','리듬·선법·현대어법','권리 확인'],['피아노 교육','중급','Claude Debussy','Children’s Corner','음색·리듬','전곡'],['피아노 교육','초중급','Dmitri Kabalevsky','24 Pieces for Children, Op. 39','리듬·현대 화성','권리 확인'],['현악 교육','초중급','Antonio Vivaldi','The Four Seasons','리토르넬로·협주곡','원전과 교육 편곡 분리'],['현악 교육','중급 이상','Johann Sebastian Bach','Sonatas and Partitas for Solo Violin','대위법·형식','전곡'],['실내악','중급 이상','Wolfgang Amadeus Mozart','Eine kleine Nachtmusik, K. 525','고전 형식','원전·파트'],['관현악 감상','입문','Ludwig van Beethoven','Symphony No. 5','동기 발전·형식','전악장'],['관현악 감상','입문','Antonín Dvořák','Symphony No. 9','민족주의·형식','전악장'],['음악사·분석','중급','Hector Berlioz','Symphonie fantastique','표제음악·순환 주제','전악장'],['음악사·분석','중급','Claude Debussy','Prélude à l’après-midi d’un faune','음색·형식','원전'],['음악사·분석','고급','Igor Stravinsky','The Rite of Spring','리듬·오스티나토','판본·권리 확인'],['음악사·분석','고급','Arnold Schoenberg','Pierrot lunaire','무조·동기','권리 확인'],['음악사·분석','고급','Béla Bartók','Music for Strings, Percussion and Celesta','대칭·형식','권리 확인']
];
const eduSheet=workbook.worksheets.add('교육·연주');title(eduSheet,'A1:J1','교육·연주 레퍼토리 수집 큐');
eduSheet.getRange('A2:J2').values=[['용도','난이도','작곡가','작품','교육 포인트','수집 범위','교육과정 출처','출처 확인일','XML 상태','메모']];header(eduSheet.getRange('A2:J2'));
eduSheet.getRange(`A3:J${education.length+2}`).values=education.map(r=>[...r,'ABRSM·RCM·대학 강의계획서 검증 필요',null,'미확인','']);addTable(eduSheet,`A2:J${education.length+2}`,'EducationRepertoireTable');
eduSheet.getRange(`H3:H${education.length+2}`).setNumberFormat('yyyy-mm-dd');eduSheet.getRange(`I3:I${education.length+2}`).dataValidation={rule:{type:'list',values:['미확인','보유','부분 보유','미보유','권리 검토']}};
finish(eduSheet,`A1:J${education.length+2}`,{A:17,B:13,C:31,D:50,E:26,F:30,G:37,H:14,I:14,J:28});

const balanceSheet=workbook.worksheets.add('균형 점검');title(balanceSheet,'A1:H1','작곡가·시대·지역 균형 점검');
balanceSheet.getRange('A3:H3').values=[['지표','현재 보완 큐','목표 방향','차이','판정','다음 조치','산출 기준','메모']];header(balanceSheet.getRange('A3:H3'));
balanceSheet.getRange('A4:H10').values=[
 ['보완 작곡가 수',supplements.length,30,0,'충족','검증 착수','보완 작곡가 행 수',''],['여성 작곡가 보완',supplements.filter(r=>r[6].includes('여성')).length,10,null,'','대표작·XML 확인','보완 목적에 여성 포함',''],['동아시아 보완',supplements.filter(r=>r[6].includes('동아시아')||r[5].includes('한국')||r[5].includes('일본')||r[5].includes('중국')).length,5,null,'','권리 검토 병행','지역·보완 목적 기준',''],['라틴아메리카·카리브 보완',supplements.filter(r=>r[6].includes('라틴')||r[6].includes('카리브')).length,3,null,'','후보 추가','지역·보완 목적 기준',''],['흑인 작곡가 보완',supplements.filter(r=>r[6].includes('흑인')).length,4,null,'','작품·판본 검증','보완 목적 기준',''],['고전 이전 보완',supplements.filter(r=>['중세','르네상스','바로크'].includes(r[1])).length,5,null,'','별도 후보 2차 추가','시대 기준','현재 0명'],['현대 권리 검토 대상',supplements.filter(r=>r[8].includes('권리')).length,null,null,'','XML 공개 전 권리 확인','권리 1차 분류 기준','목표치가 아니라 관리 대상']
];
for(let row=4;row<=9;row++){balanceSheet.getRange(`D${row}`).formulas=[[`=B${row}-C${row}`]];balanceSheet.getRange(`E${row}`).formulas=[[`=IF(D${row}>=0,"충족","보완 필요")`]];}
balanceSheet.getRange('A13:F13').values=[['시대','보완 큐 수','여성 작곡가','권리 검토','퍼블릭 도메인 후보','추가 목표']];header(balanceSheet.getRange('A13:F13'));
const eras=['중세','르네상스','바로크','고전주의','초기 낭만주의','낭만주의','후기 낭만주의','20세기','전후 현대음악','21세기'];
balanceSheet.getRange('A14:F23').values=eras.map(e=>[e,supplements.filter(r=>r[1]===e).length,supplements.filter(r=>r[1]===e&&r[6].includes('여성')).length,supplements.filter(r=>r[1]===e&&r[8].includes('권리')).length,supplements.filter(r=>r[1]===e&&r[8].includes('퍼블릭')).length,['중세','르네상스','바로크','21세기'].includes(e)?'보완 우선':'유지·검증']);
balanceSheet.getRange('E4:E10').conditionalFormats.add('containsText',{text:'보완 필요',format:{fill:lightRed,font:{bold:true,color:'#8A2F24'}}});balanceSheet.getRange('E4:E10').conditionalFormats.add('containsText',{text:'충족',format:{fill:green,font:{bold:true,color:'#2E5C3B'}}});
finish(balanceSheet,'A1:H23',{A:26,B:15,C:13,D:12,E:15,F:29,G:31,H:28},3);

const rightsRows=[...supplements.filter(r=>r[8].includes('권리')||r[8].includes('관할')).map(r=>[r[4],r[2],r[3],r[5],r[7],r[8],'가능','허가 또는 퍼블릭 도메인 확인 후','미확인','한국·서비스 대상국 별도',''])];
const rightsSheet=workbook.worksheets.add('현대 저작권');title(rightsSheet,'A1:K1','현대 작품 권리 검토 큐');
rightsSheet.getRange('A2:K2').values=[['작곡가','출생','사망','지역','대표 작품','1차 분류','메타데이터 등록','XML·악보 공개','권리 확인 상태','관할','메모']];header(rightsSheet.getRange('A2:K2'));
rightsSheet.getRange(`A3:K${rightsRows.length+2}`).values=rightsRows;
rightsSheet.tables.add(`A2:K${rightsRows.length+2}`,true,'ModernRightsTable').style='TableStyleMedium2';
rightsSheet.getRange(`I3:I${rightsRows.length+2}`).dataValidation={rule:{type:'list',values:['미확인','권리자 조사 중','허가 요청','허가 완료','퍼블릭 도메인 확인','공개 제외']}};
finish(rightsSheet,`A1:K${rightsRows.length+2}`,{A:28,B:9,C:9,D:18,E:48,F:20,G:17,H:34,I:18,J:25,K:30});

const guide=workbook.worksheets.getItem('기준 및 출처');
guide.getRange('A36:F36').values=[['확장 출처','용도','URL','접근일','제약','적용 탭']];header(guide.getRange('A36:F36'));
guide.getRange('A37:F44').values=[
 ['Bach Digital smart','J. S. Bach 작품 식별','https://smart.bach-digital.de/',new Date(),'원전·판본 조건 별도 확인','전작 카탈로그'],['Digital Mozart Edition','Mozart NMA·Köchel 연결','https://dme.mozarteum.at/DME/nma/start.php?l=2',new Date(),'대량·상업적 재사용 제한 확인','전작 카탈로그'],['Beethoven-Haus Bonn','Beethoven 작품 번호·날짜','https://www.beethoven.de/en/work/search',new Date(),'자료별 이용조건 확인','전작 카탈로그'],['Schubert Online','Schubert 자필·초판·D 번호','https://schubert-online.at/activpage/index.php?lang=E',new Date(),'이미지 재사용 조건 확인','전작 카탈로그'],['RISM Online','음악 자료·작품 식별 교차검증','https://rism.online/',new Date(),'자료 레코드와 작품 개념 구분','전작 카탈로그'],['IMSLP Collected Works','전집·판본 탐색','https://imslp.org/wiki/Category:Collected_Works',new Date(),'지역별 저작권·판본 권리 확인','대표작 큐'],['ABRSM','교육 레퍼토리 검증','https://www.abrsm.org/',new Date(),'현행 syllabus 버전 명시','교육·연주'],['국가법령정보센터 저작권법','한국 저작권 보호기간 검토','https://www.law.go.kr/법령/저작권법',new Date(),'법률 자문이 아님; 개별 작품·판본 확인','현대 저작권']
];guide.getRange('D37:D44').setNumberFormat('yyyy-mm-dd');finish(guide,'A1:F44',{A:25,B:42,C:57,D:14,E:44,F:22},3);

const summary=workbook.worksheets.getItem('우선 등록');
summary.getRange('J1:N1').merge();summary.getRange('J1').values=[['확장 수집 현황']];summary.getRange('J1:N1').format={fill:navy,font:{name:'Arial',size:13,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:30};
summary.getRange('J3:N3').values=[['확장 영역','후보 수','검증 완료','진행률','다음 단계']];header(summary.getRange('J3:N3'));
summary.getRange('J4:N9').values=[['보완 작곡가',supplements.length,0,null,'인명·대표작 검증'],['S등급 전작 카탈로그',catalogues.length,catalogues.filter(r=>r[7]==='확인').length,null,'권위 출처 확대'],['대표작 큐',representative.length,0,null,'기존 목록 중복 확인'],['교육·연주',education.length,0,null,'현행 syllabus 교차검증'],['균형 점검',7,1,null,'중세·르네상스 보완'],['현대 저작권',rightsRows.length,0,null,'권리자·관할 확인']];
for(let row=4;row<=9;row++)summary.getRange(`M${row}`).formulas=[[`=IFERROR(L${row}/K${row},0)`]];
summary.getRange('M4:M9').setNumberFormat('0%');summary.getRange('J:N').format.verticalAlignment='center';summary.getRange('J:N').format.wrapText=true;for(const [col,width] of Object.entries({J:27,K:12,L:13,M:12,N:31}))summary.getRange(`${col}:${col}`).format.columnWidth=width;

workbook.recalculate();
const checks={
 summary:await workbook.inspect({kind:'table',range:'우선 등록!J1:N9',include:'values,formulas',tableMaxRows:12,tableMaxCols:6}),
 supplements:await workbook.inspect({kind:'table',range:'보완 작곡가!A1:L12',include:'values,formulas',tableMaxRows:12,tableMaxCols:12}),
 catalogues:await workbook.inspect({kind:'table',range:'전작 카탈로그!A1:I12',include:'values,formulas',tableMaxRows:12,tableMaxCols:9}),
 errors:await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:300},summary:'final formula error scan'})
};
for(const [sheetName,range,file] of [
 ['우선 등록','J1:N10','summary-extension.png'],['보완 작곡가','A1:L18','supplement.png'],['전작 카탈로그','A1:I18','catalogues.png'],['대표작 큐','A1:I18','representative.png'],['교육·연주','A1:J18','education.png'],['균형 점검','A1:H23','balance.png'],['현대 저작권','A1:K18','rights.png'],['기준 및 출처','A27:F44','sources.png']
]){const blob=await workbook.render({sheetName,range,scale:1.25,format:'png'});await fs.writeFile(`${previewDir}/${file}`,new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(outputPath.replace(/[\\/][^\\/]+$/,''),{recursive:true});
const output=await SpreadsheetFile.exportXlsx(workbook);await output.save(outputPath);
console.log(JSON.stringify({outputPath,supplementCount:supplements.length,catalogueCount:catalogues.length,representativeCount:representative.length,educationCount:education.length,rightsCount:rightsRows.length,checks:Object.fromEntries(Object.entries(checks).map(([k,v])=>[k,v.ndjson]))},null,2));
