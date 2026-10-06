import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='evaluation/case-assets/S-STRUCT-007';
if(existsSync(root))throw Error('Refusing to overwrite case');
const response=await fetch('http://127.0.0.1:5173/api/work/work-3817b61638e9efc0');
if(!response.ok)throw Error(`HTTP ${response.status}`);
const work=await response.json();
if(work.workId!=='work-3817b61638e9efc0'||!work.xml||work.notes[59]?.spelling!=='C4'||work.notes[60]?.spelling!=='Bb3'||work.notes[80]?.measure!==14)throw Error('Review mapping changed');
const hash=s=>createHash('sha256').update(s).digest('hex');
const snapshot={schema:'musicanote-structure-review/v1',capturedAt:new Date().toISOString(),xmlSha256:hash(work.xml),engineHash:hash(readFileSync('server/phrase-boundaries.mjs')),work};
const feedback={schema:'musicanote-user-structure-feedback/v1',caseId:'S-STRUCT-007',sourceHash:snapshot.xmlSha256,status:'review-preference-not-gold',
 userDescription:'Phrase1 전주와 Phrase2는 적절. Phrase3의 첫 beamed note는 다음 솔을 준비. Phrase3/4/5는 합치되 10마디 첫 라·도 2분음표까지. 뒤 시는 다음 도를 위한 비화성음이며 전타음 가능성, 다음 Phrase에 포함. Phrase6은14마디 첫 음까지.',
 proposedRanges:[{startEventId:work.notes[37].id,lastEventId:work.notes[59].id,endExclusiveEventId:work.notes[60].id,status:'mapped-from-explicit-measure-endpoint'},{startEventId:work.notes[60].id,lastEventId:work.notes[80].id,endExclusiveEventId:work.notes[81].id,status:'inferred-next-span-start-confirm-in-review'}],
 preservedBaselineStarts:[work.notes[0].id,work.notes[17].id,work.notes[37].id],
 harmonicHypotheses:[{targetEventId:work.notes[60].id,label:'non-chord-tone preparing following C',subtypeCandidate:'appoggiatura',status:'user-hypothesis-awaiting-harmony',confirmed:false}],
 sourceObservations:['m10 first notated chord Ab3+C4 half notes; selected melody C4 index59','m10 following note Bb3 quarter index60, not B natural','m14 first selected note F4 quarter index80','m10 boundary60 strength0.083333 without gap','m14 boundary81 rawStrength0.905726 suppressed to0.49 by minimum4attacks, local fragment start79'],
 limitations:['Current Phrase6 numbering and proposed second-span start are not equivalent; the proposed start is inferred from user next-phrase wording','No harmony or NCT label promoted to Core; no runtime rule change']};
mkdirSync(root);writeFileSync(root+'/context.musicxml',work.xml);writeFileSync(root+'/review-snapshot.json',JSON.stringify(snapshot,null,2));writeFileSync(root+'/feedback.json',JSON.stringify(feedback,null,2));
console.log(JSON.stringify({caseId:feedback.caseId,notes:work.notes.length,sourceHash:snapshot.xmlSha256,proposedRanges:feedback.proposedRanges}));
