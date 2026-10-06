// Written score order, not part IDs or the search index's melody-role score.
// Keep one whole voice across the piece; rests do not trigger voice switching.
export function selectUpperStructureStream(rows,xml){
 const partOrder=[...xml.matchAll(/<score-part\b[^>]*\bid="([^"]+)"/g)].map(m=>m[1]);
 const candidates=rows.filter(r=>!r.stream_id.endsWith(':structural')).map(row=>{
  const [part,staff,voice]=row.stream_id.split(':'),notes=JSON.parse(row.notes).filter(n=>Number.isFinite(n.p));
  const pitches=notes.map(n=>n.p).sort((a,b)=>a-b);
  return {row,part,staff,voice,order:partOrder.indexOf(part),median:pitches[Math.floor(pitches.length/2)]??-Infinity};
 }).filter(c=>c.order>=0&&c.median!==-Infinity);
 candidates.sort((a,b)=>a.order-b.order||Number(a.staff)-Number(b.staff)||b.median-a.median||a.voice.localeCompare(b.voice,undefined,{numeric:true}));
 const chosen=candidates[0];
 return chosen?{row:chosen.row,policy:'written-upper-staff-whole-voice/v1',reason:'악보 파트 배치 → 위쪽 오선 → 성부의 중앙 음높이',alternatives:candidates.filter(c=>c.part===chosen.part&&c.staff===chosen.staff).map(c=>c.row.stream_id)}:null;
}
