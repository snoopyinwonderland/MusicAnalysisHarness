/** Explicit opt-out only: older Harness/API queries retain their original policy. */
export function simpleQueryPattern(notes) {
 if(notes.length<6)return null;
 // A rest breaks continuity. Tied attacks have already been collapsed by the caller.
 if(notes.slice(1).some((n,i)=>Math.abs(n.onset-notes[i].onset-notes[i].durationRatio)>1e-6))return null;
 const intervals=notes.slice(1).map((n,i)=>n.pitchMidi-notes[i].pitchMidi);
 const repeated=intervals.every(i=>i===0);
 const stepwise=intervals.every(i=>[1,2].includes(Math.abs(i)))&&intervals.every(i=>Math.sign(i)===Math.sign(intervals[0]));
 return stepwise?'stepwise':repeated?'repeated':null;
}
export function queryPatternNotice(query,notes) {
 if(!['melody','melody_rhythm'].includes(query.mode))return null;
 const pattern=simpleQueryPattern(notes);
 if(pattern==='stepwise'&&query.allowContinuousStepwise===false)return '6음 이상이 모두 같은 방향의 순차진행입니다. 상세 검색에서 “연속 순차 진행 검색 허용”을 체크하거나 특징적인 음을 더 입력해 주세요.';
 if(pattern==='repeated'&&query.allowContinuousRepeated===false)return '6음 이상이 모두 같은 음의 반복입니다. 상세 검색에서 “연속 같은 음 검색 허용”을 체크하거나 특징적인 음을 더 입력해 주세요.';
 return null;
}
