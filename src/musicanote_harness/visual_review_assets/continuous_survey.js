const $=id=>document.getElementById(id);
const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
let data,selectedPattern,serial=0,initial=new URLSearchParams(location.search).get('candidate');
const frac=q=>q.numerator+'/'+q.denominator;
function clear(){document.querySelectorAll('.context-mark,.ornament-mark').forEach(n=>n.classList.remove('context-mark','ornament-mark'));document.querySelectorAll('.range-box').forEach(n=>n.remove());}
function mark(pattern){
 selectedPattern=pattern;
 clear();if(!data)return;const ids=new Set(data.display_note_refs),c=data.conditions[+$('candidate').value];
 const sounds=Object.fromEntries((data.voices?.events||[]).map(s=>[s.sounding_event_id,s]));
 const middle=new Set(pattern?(sounds[pattern.middle_ref]?.source_note_ids||[]):[]);const groups=new Map();
 document.querySelectorAll('.scorepage .note').forEach(n=>{const id=n.dataset.id||n.id;if(!ids.has(id))return;n.classList.add(middle.has(id)?'ornament-mark':'context-mark');
  const system=n.closest('g.system')||n.closest('.scorepage');if(!groups.has(system))groups.set(system,[]);groups.get(system).push(n);
 });
 for(const notes of groups.values()){
  const page=notes[0].closest('.scorepage'),p=page.getBoundingClientRect(),rs=notes.map(n=>n.getBoundingClientRect());
  const left=Math.max(0,Math.min(...rs.map(r=>r.left))-p.left-5),top=Math.max(24,Math.min(...rs.map(r=>r.top))-p.top-5);
  const box=text('div','');box.className='range-box context';Object.assign(box.style,{left:left+'px',top:top+'px',width:Math.max(...rs.map(r=>r.right))-p.left-left+5+'px',height:Math.max(...rs.map(r=>r.bottom))-p.top-top+5+'px'});
  box.append(Object.assign(text('span',c?c.display_label+' ?':'관찰 범위'),{className:'candidate-label'}));page.append(box);
 }
}
function draw(){
 const box=$('details');box.replaceChildren();if(!data)return;const c=data.conditions[+$('candidate').value];
 box.append(text('p','검사 상태: '+data.status),text('p','같은 음표·시간을 모든 후보에 대조합니다. 관찰 범위 전체에 하나의 화음이 유지된다는 가정이며, 화음 교체는 아직 비교하지 않았습니다.'));
 if(!c){
  const reasons={sample_scope_abstention:'음표의 전체 길이가 고정 검사 범위를 벗어나거나 음가가 유효하지 않습니다.',context_abstention:'반복·박자·문맥 범위 안전 검사를 통과하지 못했습니다.',voice_enumeration_abstention:'성부 연결의 전체 조합이 계산 상한을 넘었습니다. 일부만 골라 판정하지 않습니다.',condition_budget_abstention_no_pruning:'후보와 성부 연결의 전체 비교량이 계산 상한을 넘었습니다. 후보를 임의로 버리지 않습니다.'};
  box.append(text('p',reasons[data.status]||'조건부 설명 없음/보류.'),text('p','후보나 화성이 없다는 뜻은 아닙니다.'));mark();return;}
 box.append(text('h3',c.display_label+' · 가설'),text('p','해당 기보 성부의 관찰 음가 '+frac(c.all_note_time)+' quarter · 구성음 '+frac(c.note_time_by_state.member)+' · 비구성음 '+frac(c.note_time_by_state.nonmember_not_confirmed_nct)));
 if(c.abstention_reasons.length)box.append(text('p','보류: '+c.abstention_reasons.join(', ')));
 if(!c.patterns.length)box.append(text('p','지원하는 연속 3음의 조건부 설명 없음. 정확한 화음이나 NCT 여부는 미확정입니다.'));
 for(const p of c.patterns){
  const names=Object.fromEntries(data.voices.events.map(s=>[s.sounding_event_id,s.pitch.spelling]));
  const role={passing_candidate:'경과음 형태',neighbor_candidate:'보조음 형태',chromatic_passing_candidate:'반음계 경과음 형태'}[p.conditional_role]||p.conditional_role;
  box.append(text('p',p.event_refs.map(id=>names[id]).join(' → ')+' · '+role+' · 일부 성부 연결에서만 가능'));
  const button=text('button','이 조건부 비화성음 보기');button.onclick=()=>mark(p);box.append(button);
 }
 box.append(text('p','전체 '+data.voices.assignments.length+'개 연결 조합에는 무연결도 포함합니다. 형태의 개수는 확률이 아니며 설명된 음도 비구성음 음가 합에 남습니다.'));
 mark();
}
async function load(){const request=++serial;data=null;clear();$('candidate').replaceChildren();$('details').textContent='불러오는 중…';
 try{const response=await fetch('samples/'+$('sample').value+'.json');if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(request!==serial)return;data=value;
  $('candidate').replaceChildren(...data.conditions.map((c,i)=>{const n=text('option',c.display_label+' · 형태 '+c.patterns.length+(c.abstention_reasons.length?' · 보류':''));n.value=i;return n;}));
  if([...$('candidate').options].some(o=>o.value===initial))$('candidate').value=initial;initial=null;draw();
 }catch(e){if(request===serial)$('details').textContent='읽기 실패: '+e.message;}}
$('sample').onchange=load;$('candidate').onchange=draw;window.addEventListener('resize',()=>mark(selectedPattern));
const sample=new URLSearchParams(location.search).get('sample');if([...$('sample').options].some(o=>o.value===sample))$('sample').value=sample;load();
