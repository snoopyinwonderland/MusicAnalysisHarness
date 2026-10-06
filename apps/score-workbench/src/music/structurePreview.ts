import {reviewNoteIdentity} from './repeatReviewImport';
export function validateStructurePreview(data:any,work:any){
 if(data?.schema!=='structure-preview/v1'||data.workId!==work.workId||data.streamId!==work.streamId||JSON.stringify(data.noteIdentity)!==JSON.stringify(reviewNoteIdentity(work.notes)))throw Error('저장 사례와 현재 악보가 다릅니다.');
 if(!Array.isArray(data.ranges)||!data.ranges.length||data.ranges.length>100)throw Error('잘못된 범위 목록');
 let previous=0;
 for(const r of data.ranges){
  if(!Number.isInteger(r.startIndex)||!Number.isInteger(r.endIndexExclusive)||r.startIndex<previous||r.endIndexExclusive<=r.startIndex||r.endIndexExclusive>work.notes.length||work.notes[r.startIndex]?.id!==r.startEventId||work.notes[r.endIndexExclusive-1]?.id!==r.lastEventId)throw Error('음표 범위 불일치');
  previous=r.endIndexExclusive;
 }
 return data;
}
