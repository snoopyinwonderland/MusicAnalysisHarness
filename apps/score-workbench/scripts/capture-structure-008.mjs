import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {alignStructureTemplate} from '../src/music/structureTemplateAlignment.ts';
const root='evaluation/case-assets/S-STRUCT-008';if(existsSync(root))throw Error('Refusing overwrite');
const response=await fetch('http://127.0.0.1:5173/api/work/work-15fa42f2e80b3722');if(!response.ok)throw Error(`HTTP ${response.status}`);
const work=await response.json(),n=work.notes,hash=s=>createHash('sha256').update(s).digest('hex');
const starts=work.phraseAnalysis.boundaries.filter(b=>b.supported).slice(0,3).map(b=>b.index);
if(JSON.stringify(starts)!=='[30,35,60]'||work.workId!=='work-15fa42f2e80b3722')throw Error('Review mapping changed');
const sourceHash=hash(work.xml),comparison=alignStructureTemplate(n.slice(0,30),n.slice(30,60));
const feedback={caseId:'S-STRUCT-008',sourceHash,status:'user-preference-not-gold',userDescription:'Phrase2는 Phrase1 앞부분의 반복인데 분리되었다. Phrase2와3을 합쳐야 한다.',
 reference:{startEventId:n[0].id,lastEventId:n[29].id},proposed:{startEventId:n[30].id,lastEventId:n[59].id,endExclusiveEventId:n[60].id},removeBoundaryBefore:n[35].id,
 observations:{originalArrival:{eventId:n[4].id,pitch:n[4].spelling,duration:n[4].durationRatio,gap:n[5].onset-n[4].onset-n[4].durationRatio},repeatedArrival:{eventId:n[34].id,pitch:n[34].spelling,duration:n[34].durationRatio,gap:n[35].onset-n[34].onset-n[34].durationRatio}},
 analysis:comparison,limitations:['Similarity is uncalibrated, not merge probability','No production rule or harmonic interpretation changed']};
mkdirSync(root);writeFileSync(root+'/context.musicxml',work.xml);writeFileSync(root+'/review-snapshot.json',JSON.stringify({schema:'musicanote-structure-review/v1',capturedAt:new Date().toISOString(),xmlSha256:sourceHash,engineHash:hash(readFileSync('server/phrase-boundaries.mjs')),work},null,2));writeFileSync(root+'/feedback.json',JSON.stringify(feedback,null,2));
console.log(JSON.stringify({sourceHash,similarity:comparison.similarity,coverage:comparison.coverage,terminal:comparison.terminal,observations:feedback.observations}));
