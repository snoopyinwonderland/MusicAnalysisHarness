import type {Query, QueryEvent, Meter, QueryMode} from '../types';
import {pitchName} from './pitch';
const modes:QueryMode[]=['melody','melody_rhythm','rhythm','contour'];
const meters:Meter[]=['2/4','3/4','4/4','5/4','3/8','6/8','7/8','9/8','12/8','unknown'];
export function formatCompactQuery(query:Query):string {
 return query.events.map(e=>`${e.kind==='rest'?'쉼표':e.spelling||pitchName(e.pitchMidi!)}(${e.durationRatio})`).join('-');
}
function compactQuery(text:string, defaults:{mode?:QueryMode;meter?:Meter}):Query {
 const token=/\s*(쉼표|rest|R|[A-Ga-g](?:[#♯b♭])?-?\d+(?:[#♯b♭])?)\s*\(\s*(\d+(?:\.\d+)?|\.\d+)(?:\s*\/\s*(\d+(?:\.\d+)?))?\s*\)/iy;
 const events:QueryEvent[]=[];let offset=0;
 while(offset<text.length){token.lastIndex=offset;const m=token.exec(text);if(!m)throw Error('간단 표기는 C4(0.5)-D♭4(1)-쉼표(0.5)처럼 입력해 주세요.');
  const durationRatio=Number(m[2])/(m[3]===undefined?1:Number(m[3]));
  const rest=/^(쉼표|rest|r)$/i.test(m[1]);let pitchMidi:number|null=null,spelling:string|undefined;
  if(!rest){const p=/^([A-Ga-g])([#♯b♭]?)(-?\d+)([#♯b♭]?)$/.exec(m[1])!;if(p[2]&&p[4])throw Error('임시표는 음이름 앞이나 뒤 한 곳에만 입력해 주세요.');const accidental=p[2]||p[4];pitchMidi=12*(Number(p[3])+1)+({C:0,D:2,E:4,F:5,G:7,A:9,B:11}[p[1].toUpperCase()]!)+(/[♯#]/.test(accidental)?1:/[♭b]/.test(accidental)?-1:0);spelling=p[1].toUpperCase()+accidental+p[3];}
  events.push({id:`import-${events.length}`,kind:rest?'rest':'note',pitchMidi,durationRatio,...(spelling?{spelling}:{})});
  offset=token.lastIndex;const tail=text.slice(offset);if(!tail.trim())break;const separator=/^\s*[-–]\s*/.exec(tail);if(!separator)throw Error('각 음표 사이는 - 로 구분해 주세요.');offset+=separator[0].length;
 }
 return {version:1,mode:defaults.mode==='contour'?'melody_rhythm':defaults.mode??'melody_rhythm',meter:defaults.meter??'4/4',startsOnDownbeat:true,events};
}
export function parseQueryImport(text:string, defaults:{mode?:QueryMode;meter?:Meter}={}):Query {
 const cleaned=text.trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');
 let data;if(!cleaned.startsWith('{')&&!cleaned.startsWith('['))data=compactQuery(cleaned,defaults);else try{data=JSON.parse(cleaned)}catch{throw Error('올바른 Query JSON을 붙여넣어 주세요.');}
 if(!data||typeof data!=='object')throw Error('Query 객체가 필요합니다.');
 if(data.schema!==undefined&&data.schema!=='musicanote-query')throw Error('지원하지 않는 Query 형식입니다.');
 const q=data.schema==='musicanote-query'?data.query:data;
 if(!q||q.version!==1||!modes.includes(q.mode)||!meters.includes(q.meter)||q.startsOnDownbeat!==true)throw Error('지원하는 mode·meter·version·startsOnDownbeat 값인지 확인해 주세요.');
 if(!Array.isArray(q.events)||q.events.length===0||q.events.length>512)throw Error('이벤트 1~512개를 포함한 Query가 필요합니다.');
 const ids=new Set<string>();
 const events:QueryEvent[]=q.events.map((e:QueryEvent,i:number)=>{
  if(!e||!['note','rest'].includes(e.kind)||!Number.isFinite(e.durationRatio)||e.durationRatio<=0||e.durationRatio>256)throw Error(`${i+1}번째 음표/쉼표의 종류 또는 음가가 잘못되었습니다.`);
  if(e.kind==='note'&&(!Number.isInteger(e.pitchMidi)||e.pitchMidi!<0||e.pitchMidi!>127))throw Error(`${i+1}번째 음높이는 MIDI 0~127 정수여야 합니다.`);
  const id=typeof e.id==='string'&&e.id?e.id:`import-${i}`;if(ids.has(id))throw Error('음표 ID가 중복되어 있습니다.');ids.add(id);
  const out:QueryEvent={id,kind:e.kind,pitchMidi:e.kind==='rest'?null:e.pitchMidi,durationRatio:e.durationRatio};
  for(const k of ['spelling','tieGroup','tupletGroup'] as const)if(e[k]!==undefined){if(typeof e[k]!=='string')throw Error('음표 표기·그룹 값이 잘못되었습니다.');out[k]=e[k];}
  for(const k of ['writtenDuration','actualNotes','normalNotes','contourShapeConfidence'] as const)if(e[k]!==undefined){if(!Number.isFinite(e[k])||e[k]!<0)throw Error('음가/잇단음표 값이 잘못되었습니다.');out[k]=e[k];}
  if(out.tupletGroup&&(!out.writtenDuration||!Number.isInteger(out.actualNotes)||!Number.isInteger(out.normalNotes)||out.actualNotes!<1||out.normalNotes!<1))throw Error('잇단음표의 음가와 비율이 필요합니다.');
  return out;
 });
 const result:Query={version:1,mode:q.mode,meter:q.meter,startsOnDownbeat:true,events};
 for(const k of ['absoluteExactOnly','exactIntervalOnly','exactPitchOnly','exactRhythmOnly','includeRests','downbeatWeightBoost','allowContinuousStepwise','allowContinuousRepeated'] as const){if(q[k]!==undefined&&typeof q[k]!=='boolean')throw Error(`${k}는 true/false여야 합니다.`);if(q[k]!==undefined)result[k]=q[k];}
 // Do not silently enable the new broad-pattern permissions when old tests omit them.
 result.allowContinuousStepwise??=false;result.allowContinuousRepeated??=false;
 return result;
}
