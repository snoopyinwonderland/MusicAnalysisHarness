import type {CorpusNote} from '../types';
export const reviewNoteIdentity=(notes:CorpusNote[])=>notes.map(n=>[n.id,n.pitchMidi,n.onset,n.durationRatio,n.measure,n.beat]);
export function validateRepeatReview(data:any,work:{workId:string;streamId:string;notes:CorpusNote[]}){
  if(data?.schema!=='repeat-review-ui/v1'||data.workId!==work.workId||data.streamId!==work.streamId||JSON.stringify(data.noteIdentity)!==JSON.stringify(reviewNoteIdentity(work.notes)))throw Error('보고서와 현재 악보/성부/음표 정보가 다릅니다. 보고서를 다시 생성해 주세요.');
  if(!Array.isArray(data.rows)||data.rows.length>10000)throw Error('잘못된 후보 목록');
  for(const row of data.rows)for(const side of ['left','right']){
    const r=row[side];
    if(!r||!Number.isInteger(r.startIndex)||!Number.isInteger(r.endIndexExclusive)||r.startIndex<0||r.endIndexExclusive<=r.startIndex||r.endIndexExclusive>work.notes.length||work.notes[r.startIndex].id!==r.startEventId||work.notes[r.endIndexExclusive-1].id!==r.lastEventId)throw Error('후보 음표 참조가 유효하지 않습니다.');
  }
  return data;
}
