const $=id=>document.getElementById(id);
const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
let data,serial=0,changed=new Set();
// Exact rational arithmetic for note-time; numbers below are SVG pixels only.
const gcd=(a,b)=>b?gcd(b,a%b):a;
const rational=(n,d=1n)=>{const g=gcd(n<0n?-n:n,d);return [n/g,d/g];};
const rq=q=>rational(BigInt(q.numerator),BigInt(q.denominator));
const add=(a,b)=>rational(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const sub=(a,b)=>add(a,[-b[0],b[1]]);
const le=(a,b)=>a[0]*b[1]<=b[0]*a[1];
const show=a=>a[1]===1n?String(a[0]):a.join('/');
function options(id,rows,label,selected=0){$(id).replaceChildren(...rows.map((r,i)=>{const n=text('option',label(r,i));n.value=i;return n;}));$(id).value=String(selected);}
function profile(cells,segments,aid){const totals={member:[0n,1n],conditional_nonmember:[0n,1n],unexplained_nonmember:[0n,1n],spelling_unresolved:[0n,1n]},items=[];
 for(const cell of cells){const r=segments.find(s=>le(rq(s.span.start),rq(cell.span.start))&&le(rq(cell.span.end),rq(s.span.end)));if(!r)throw Error('범위 계약 불일치');
  const c=r.condition,a=c.assignments.find(a=>a.assignment_ref===aid);if(!c.abstention_reasons.length&&!a)throw Error('성부 연결 누락');
  const explained=new Set(c.abstention_reasons.length?[]:a?.conditionally_explained_nonmember_refs||[]);
  for(const sid of cell.event_refs){const state=r.event_states[sid];if(!state)throw Error('음표 근거 누락');const bucket=state==='nonmember_not_confirmed_nct'?(explained.has(sid)?'conditional_nonmember':'unexplained_nonmember'):state;
   totals[bucket]=add(totals[bucket],sub(rq(cell.span.end),rq(cell.span.start)));items.push({sid,bucket,span:cell.span});}
 }return {totals,items};}
function clear(){document.querySelectorAll('.context-mark,.ornament-mark').forEach(n=>n.classList.remove('context-mark','ornament-mark'));document.querySelectorAll('.range-box').forEach(n=>n.remove());}
function drawOrnamentTimeline(box,b,h,l,r,aid,active){const shared=b.shared_context?.status==='ready',policy=shared?b.shared_context:b.ornament_timeline;if(!policy)return;
 const labels={member:'구성음만',conditional_nonmember:'장식 후보로 조건부 설명',withheld_nonmember:'설명 후보 있으나 보류',unexplained_nonmember:'미설명 비구성음 포함',spelling_unresolved:'음높이/철자 미정',silence:'쉼'};
 box.append(text('h3',shared?'동일 문맥·동일 규칙의 장식 설명 대조':'장식 설명을 연결한 시간순 대조'));
 const common=shared?policy.patterns.filter(p=>p.supporting_assignment_refs.includes(aid)):[],holdPatterns=common.filter(p=>p.hold_reading_indices.includes(+$('hold').value)),splitPatterns=common.filter(p=>p.left_reading_indices.includes(+$('left').value)&&p.right_reading_indices.includes(+$('right').value)),results=[];
 if(shared)box.append(text('p','양쪽 모두 ['+show(rq(policy.context_span.start))+', '+show(rq(policy.context_span.end))+')의 동일 음표·성부 연결을 참고합니다. 이전 local 설명을 그대로 더하지 않고 공통 음형 규칙으로 다시 계산합니다.'));
 for(const [name,segments,patterns] of [['유지',[h],shared?holdPatterns:[]],['분할',[l,r],shared?splitPatterns:l.condition.abstention_reasons.length||r.condition.abstention_reasons.length?[]:active]]){
  const p=profile(b.cells,segments,aid),totals={member:[0n,1n],conditional_nonmember:[0n,1n],withheld_nonmember:[0n,1n],unexplained_nonmember:[0n,1n],spelling_unresolved:[0n,1n]};
  for(const item of p.items){if(shared&&item.bucket==='conditional_nonmember')item.bucket='unexplained_nonmember';const refs=patterns.filter(v=>v.affected_event_ref===item.sid&&le(rq(v.nonmember_span.start),rq(item.span.start))&&le(rq(item.span.end),rq(v.nonmember_span.end)));if(item.bucket==='unexplained_nonmember'){if(refs.some(v=>!Object.hasOwn(policy.withheld_pattern_reasons,v.pattern_id)))item.bucket='conditional_nonmember';else if(refs.length)item.bucket='withheld_nonmember';}totals[item.bucket]=add(totals[item.bucket],sub(rq(item.span.end),rq(item.span.start)));}
  results.push({totals,items:p.items});
  box.append(text('p',name+' 음가 합: '+Object.entries(totals).map(([k,v])=>labels[k]+' '+show(v)).join(' / ')+' quarter. 보류 후보는 조건부 설명량과 분리합니다.'));
  for(const cell of b.cells){const items=p.items.filter(v=>show(rq(v.span.start))===show(rq(cell.span.start))&&show(rq(v.span.end))===show(rq(cell.span.end))),states=new Set(items.map(v=>v.bucket)),state=['spelling_unresolved','unexplained_nonmember','withheld_nonmember','conditional_nonmember'].find(v=>states.has(v))||(states.size?'member':'silence');box.append(text('p',name+' ['+show(rq(cell.span.start))+', '+show(rq(cell.span.end))+') '+labels[state]));}
 }
 if(shared){const spelling=x=>JSON.stringify([...x.members].sort()),same=spelling(h)===spelling(l)&&spelling(h)===spelling(r),unblocked=[h,l,r].every(x=>!x.condition.abstention_reasons.length);if(same&&unblocked){const equal=results[0].items.every((x,i)=>x.sid===results[1].items[i].sid&&x.bucket===results[1].items[i].bucket);if(!equal)throw Error('동일 화음 분할 불변식 실패');box.append(text('p','동일 화음 검사 통과: 경계를 나눠도 음표별 설명이 같습니다.'));}}
 box.append(text('p',shared?'문맥과 규칙의 비교 조건을 맞췄지만 조건부 설명은 확정 비화성음이나 정답 점수가 아닙니다. 앞의 기존 표는 이전 계산 기록이며 이 공통 문맥 결과와 구별합니다.':'조건부 설명은 확정 비화성음이나 정답 점수가 아닙니다. 유지/분할의 문맥 범위도 달라 자동 우열을 매기지 않습니다. 기존 표는 비교 기록으로 보존합니다.'));
}
function drawCoherence(box,b,names,aid){const t=b.temporal_coherence,e=b.temporal_observations;if(t?.status!=='ready')return;
 const labels={member_only:'구성음만',mixed:'구성음+비구성음',nonmember_only:'비구성음만',silence:'전 성부 쉼',unknown:'음높이 미정'};
 box.append(text('h3','시간 순서: 분산 출현인가, 다른 화음인가'));
 for(const [label,side,id] of [['유지','hold','hold'],['분할 앞','left','left'],['분할 뒤','right','right']]){const p=t.profiles[e.reading_profile_refs[side][+$(id).value]];
  box.append(text('p',label+' · '+Object.entries(p.cell_time_quarters).map(([k,v])=>labels[k]+' '+show(rq(v))).join(' / ')+' quarter (성부 수를 곱하지 않은 실제 시간)'));
  box.append(text('p',label+' 시간순: '+p.runs.map(v=>'['+show(rq(v.span.start))+', '+show(rq(v.span.end))+') '+labels[v.state]).join(' → ')));
  box.append(text('p',label+' 실제 최저음 흐름: '+p.lowest_pitch_runs.map(v=>'['+show(rq(v.span.start))+', '+show(rq(v.span.end))+') '+(v.midi_pitch===null?'미정/쉼':'MIDI '+v.midi_pitch)+' '+v.membership.map(s=>({member:'구성음',nonmember:'비구성음',silence:'쉼',unknown_pitch_present:'음높이 미정'}[s]||s)).join('/')).join(' → ')+'. 최저음 이동은 근음 이동이나 전위 변화의 확정이 아닙니다.'));
  if(p.first_complete_union_time)box.append(text('p',label+' · global '+show(rq(p.first_complete_union_time))+' quarter까지 모으면 구성음이 모두 있습니다.'+(p.complete_union_contains_nonmembers?' 그러나 관찰 구간에는 다른 음도 섞여 있어 같은 화음의 분산형으로 확정할 수 없습니다.':'')+(p.complete_union_crosses_silence?' 구성음이 모이기 전에 전 성부 쉼도 가로지릅니다.':'')+' 동시 출현이나 실제 화음 유지의 판정은 아닙니다.'));
  if(p.all_sounding_pitches_are_members)box.append(text('p',label+' · 울리는 음은 모두 이 후보의 구성음입니다. 분산형과 양립하지만 불완전한 음군·휴지·다른 화성 해석은 여전히 가능합니다.'));
 }
 const l=b.left.readings[+$('left').value],r=b.right.readings[+$('right').value],h=data.hold_readings[+$('hold').value],cut=rq(b.boundary),unknown=new Set(e.cells.flatMap(c=>c.unknown_pitch_refs)),sounds=Object.fromEntries(data.events.map(s=>[s.sounding_event_id,s]));
 const state=(sid,reading)=>{if(unknown.has(sid))return 'unknown';const p=sounds[sid].pitch,v=typeof p.alter==='number'?p.alter:p.alter.numerator/p.alter.denominator;return reading.members.some(([s,a])=>s===p.step&&a===v)?'member':'nonmember';};
 const exclusive=(own,other)=>data.events.filter(s=>!le(rq(s.span.end),rq(own.span.start))&&!le(rq(own.span.end),rq(s.span.start))&&state(s.sounding_event_id,own)==='member'&&state(s.sounding_event_id,other)==='nonmember').map(s=>s.sounding_event_id);
 const named=refs=>refs.map(id=>names[id]||id).join(', ')||'없음',left=exclusive(l,r),right=exclusive(r,l);
 box.append(text('p','양쪽을 구별하는 구성음 · 앞에서만 구성음: '+named(left)+' / 뒤에서만 구성음: '+named(right)+'. 두 해석을 구별하는 근거이며 반대 해석의 비화성음일 가능성을 배제하지 않습니다.'));
 const held=data.events.filter(s=>!le(cut,rq(s.span.start))&&!le(rq(s.span.end),cut));
 box.append(text('p','경계에서 실제 지속하는 음: '+(held.map(s=>names[s.sounding_event_id]+' '+state(s.sounding_event_id,l)+' → '+state(s.sounding_event_id,r)).join('; ')||'없음')+'. 공통음의 지속만으로 화음 유지가 확정되지는 않습니다.'));
 const assignment=data.assignments.find(a=>a.assignment_id===aid),links=assignment.links.filter(([x,y])=>!le(cut,rq(sounds[x].span.start))&&le(cut,rq(sounds[y].span.start)));
 box.append(text('p','선택한 성부 연결에서 경계를 넘는 진행: '+(links.map(([x,y])=>names[x]+' → '+names[y]+' (유지 '+state(x,h)+' → '+state(y,h)+' / 분할 '+state(x,l)+' → '+state(y,r)+(le(rq(sounds[x].span.end),cut)?'':'; 앞 음의 경계 이후 지속 부분은 '+state(x,r))+')').join('; ')||'연결 근거 없음')+'. 분석 대상 기보 성부의 가정이며 전 성부 연결을 확정한 것이 아닙니다.'));
 box.append(text('p','비구성음 시간은 확인된 비화성음 시간이 아닙니다. 이 대조는 후보 순위·확률·최종 경계를 변경하지 않습니다. 실제 최저음/박절은 아래 패널에서 함께 확인합니다.'));
}
function drawAssessment(box,b,active,names){const a=b.boundary_assessment,e=b.temporal_observations;if(a?.status!=='ready')return;
 const statuses={unknown_pitch_limits_support:'음높이 미정으로 지지 판단 제한',no_members_observed:'관찰 구간 전체에서 구성음 미관측',partial_members_observed:'구성음 일부만 관측',all_members_at_entry:'구간 시작에 전 구성음 관측',all_members_observed_with_delay:'구성음이 뒤늦게 모임 — 분산화음 가능, 미확정'};
 const pitch=([s,v])=>s+(v>0?'#'.repeat(v):'b'.repeat(-v));
 box.append(text('h3','화성 지지와 계류음 판단 보류'));
 for(const [label,side,id] of [['유지','hold','hold'],['분할 앞','left','left'],['분할 뒤','right','right']]){const p=a.support_assessments[e.reading_profile_refs[side][+$(id).value]];
  box.append(text('p',label+': '+statuses[p.status]+'. 뒤늦게 관측 '+(p.delayed_members.map(pitch).join(', ')||'없음')+' / 구간 끝까지 미관측 '+(p.unobserved_members.map(pitch).join(', ')||'없음')+(p.absence_certain?'':' (미정 음높이 때문에 부재 확정 불가)')+'.'));
 }
 const reasonNames={structural_bass_unconfirmed:'구조적 베이스',preparation_consonance_unconfirmed:'준비음의 협화성',boundary_dissonance_unconfirmed:'경계의 불협화성',resolution_consonance_unconfirmed:'해결음의 협화성',accent_and_style_unconfirmed:'박절 강세·양식',harmonic_change_unconfirmed:'실제 화성 교체',resolution_not_contiguous:'해결음까지 시간 간격 존재'};
 for(const p of active){const v=a.patterns.find(x=>x.pattern_ref===p.pattern_id);if(!v)continue;
  box.append(text('p','계류음 판정 보류: '+p.event_refs.map(id=>names[id]).join(' → ')+'. 미확인 조건: '+v.abstention_reasons.map(r=>reasonNames[r]||r).join(', ')+'.'));
  for(const [side,label,rows] of [['hold','유지',data.hold_readings],['right','분할 뒤',b.right.readings]]){const indices=v.competing_member_reading_indices[side],labels=[...new Set(indices.map(i=>rows[i].display_label))];
   box.append(text('p','경쟁 해석 ('+label+'): '+(labels.length?labels.slice(0,8).join(', ')+(labels.length>8?' 외 '+(labels.length-8)+'개':'')+'에서는 해당 지속음 자체가 구성음입니다.':'현재 후보에는 구성음으로 보는 대안이 없습니다.')+' 추천·투표 수가 아닙니다.'));
  }
 }
 box.append(text('p','위 표의 조건부 NCT는 이전의 음형 설명량이며 확정 비화성음 수가 아닙니다. 새 보류 판단은 그 수치를 바꾸지 않습니다. 미관측 구성음이나 지연만으로 화음을 기각하지 않습니다.'));
}
function drawTemporal(box,b,active,names){const e=b.temporal_observations;if(e?.status!=='ready')return;
 const pitch=([s,a])=>s+(a>0?'#'.repeat(a):'b'.repeat(-a));
 const namesOf=refs=>refs.map(id=>names[id]||id).join(', ')||'없음';
 box.append(text('h3','실제로 울리는 음과 최저음'));
 for(const [title,index] of [['경계 직전',e.before_cell_index],['경계 직후',e.after_cell_index]]){const c=e.cells[index];
  box.append(text('p',title+' ['+show(rq(c.span.start))+', '+show(rq(c.span.end))+') quarter · 최저음 '+(c.bass_status==='observed_lowest'?namesOf(c.lowest_event_refs):c.bass_status==='silence'?'쉼':'확인 불가')+' · 전체 '+namesOf(c.active_event_refs)));
 }
 const c=e.cells[e.after_cell_index],m=c.meter;
 box.append(text('p','최저 음높이 변화: '+(e.lowest_pitch_changed===null?'확인 불가':e.lowest_pitch_changed?'있음':'없음')+' · 경계의 새 attack: '+namesOf(c.attacked_event_refs)));
 if(m.onset_in_measure)box.append(text('p','경계 박절: '+m.printed_measure_number+'마디 +'+show(rq(m.onset_in_measure))+' quarter · 표기 '+(m.time_signature.beats||'?')+'/'+(m.time_signature.beat_type||'?')+' · 분모 음가 단위로 '+(m.denominator_unit_position_zero_based?show(rq(m.denominator_unit_position_zero_based)):'?')+' 경과. 강약·복합박 그룹은 미판정'+(m.pickup?' (못갖춘마디)':'')+'.'));
 for(const [label,side,index] of [['유지','hold',+$('hold').value],['분할 앞','left',+$('left').value],['분할 뒤','right',+$('right').value]]){const p=e.candidate_support_profiles[e.reading_profile_refs[side][index]];
  const cellIndex=side==='left'?e.before_cell_index:e.after_cell_index,point=p.cells.find(x=>x.cell_index===cellIndex);
  box.append(text('p',label+' · '+(side==='left'?'경계 직전':'경계 직후')+' 관측 구성음 '+(point.present_members.map(pitch).join(', ')||'없음')+' / 미관측 '+(point.not_observed_members.map(pitch).join(', ')||'없음')+(point.absence_certain_from_available_pitches?'':' (음높이 미정 포함)')));
  box.append(text('p',label+' · 구간별 구성음 지속 합집합: '+p.member_coverage.map(v=>pitch(v.spelling)+' '+show(rq(v.observed_duration_quarters))).join(' / ')+' quarter. 전 구성음 동시 출현 '+show(rq(p.all_members_simultaneous_duration_quarters))+' quarter. 분산화음은 동시 출현이 없어도 가능합니다.'));
 }
 for(const p of active){const po=e.pattern_observations.find(x=>x.pattern_ref===p.pattern_id);if(!po)continue;
  const checkpoints=[['경계 직후',e.after_cell_index,p.affected_event_ref],...po.event_onsets.map((x,i)=>['음형 '+(i+1)+' onset',x.cell_index,x.event_ref])];
  for(const [label,idx,event] of checkpoints){if(idx===null)continue;const cell=e.cells[idx],ints=cell.intervals_from_lowest.filter(x=>x.event_ref===event);
   box.append(text('p',label+' · '+(names[event]||event)+' 대 실제 최저음: '+(ints.map(x=>(names[x.bass_ref]||x.bass_ref)+' 기준 '+(x.generic_interval===null?'철자 역전':x.generic_interval+'도')+' / '+x.semitones+'반음').join('; ')||'해당 시점 음 없음 또는 음높이 미정')));
  }
 }
 box.append(text('p','최저음·수직 음정·박절 위치는 관찰 근거입니다. 구조적 베이스, 협화/불협화, 화성 기능이나 계류음의 정답 판정은 아닙니다.'));
}
function mark(){clear();if(!data)return;const ids=new Set(data.display_note_refs),middle=new Set((data.events||[]).filter(s=>changed.has(s.sounding_event_id)).flatMap(s=>s.source_note_ids)),groups=new Map();
 document.querySelectorAll('.scorepage .note').forEach(n=>{if(!ids.has(n.dataset.id||n.id))return;n.classList.add(middle.has(n.dataset.id||n.id)?'ornament-mark':'context-mark');const system=n.closest('g.system')||n.closest('.scorepage');if(!groups.has(system))groups.set(system,[]);groups.get(system).push(n);});
 const b=data.boundaries?.[+$('boundary').value],h=data.hold_readings?.[+$('hold').value],l=b?.left.readings[+$('left').value],r=b?.right.readings[+$('right').value];
 for(const notes of groups.values()){const page=notes[0].closest('.scorepage'),p=page.getBoundingClientRect(),rs=notes.map(n=>n.getBoundingClientRect());const left=Math.max(0,Math.min(...rs.map(r=>r.left))-p.left-5),top=Math.max(24,Math.min(...rs.map(r=>r.top))-p.top-5),box=text('div','');box.className='range-box context';Object.assign(box.style,{left:left+'px',top:top+'px',width:Math.max(...rs.map(r=>r.right))-p.left-left+5+'px',height:Math.max(...rs.map(r=>r.bottom))-p.top-top+5+'px'});
  box.append(Object.assign(text('span',h&&l&&r?'유지 '+h.display_label+' / 분할 '+l.display_label+' → '+r.display_label+' ?':'관찰 범위'),{className:'candidate-label'}));
  if(b){const onsets=new Set(data.events.filter(s=>show(rq(s.span.start))===show(rq(b.boundary))).flatMap(s=>s.source_note_ids)),anchors=notes.filter(n=>onsets.has(n.dataset.id||n.id));if(anchors.length){const line=text('span','');line.title='분할 가정 위치 (탐지 결과 아님)';Object.assign(line.style,{position:'absolute',left:(Math.min(...anchors.map(n=>n.getBoundingClientRect().left))-p.left-left-3)+'px',top:'0',height:'100%',borderLeft:'2px dashed #d57519'});box.append(line);}}
  page.append(box);}
}
function draw(){const box=$('details');box.replaceChildren();changed=new Set();if(!data)return;
 const b=data.boundaries[+$('boundary').value],h=data.hold_readings[+$('hold').value],l=b?.left.readings[+$('left').value],r=b?.right.readings[+$('right').value],aid=data.assignments?.[+$('assignment').value]?.assignment_id;
 if(!b||b.status!=='ready'||!h||!l||!r||!aid){const reason=data.no_boundary_reason||(b?.status==='no_spelled_comparison'?'일부 구간에서 철자를 지지하는 화음 대안을 만들지 못했습니다. 원 후보는 데이터에 보존합니다.':'계산 상한·문맥 제한 등입니다.');box.append(text('p','비교 보류: '+(b?.status||data.status||data.baseline_status)+'. '+reason+' 화음 부재의 판정이 아닙니다.'));mark();return;}
 try{const hp=profile(b.cells,[h],aid),cp=profile(b.cells,[l,r],aid),prior=cp.totals;
  const cross=b.boundary_figures,active=(cross?.patterns||[]).filter(p=>p.left_reading_indices.includes(+$('left').value)&&p.right_reading_indices.includes(+$('right').value)&&p.supporting_assignment_refs.includes(aid));
  if(cross){cp.totals=Object.fromEntries(Object.keys(prior).map(k=>[k,[0n,1n]]));for(const item of cp.items){if(item.bucket==='unexplained_nonmember'&&active.some(p=>p.affected_event_ref===item.sid&&le(rq(p.nonmember_span.start),rq(item.span.start))&&le(rq(item.span.end),rq(p.nonmember_span.end))))item.bucket='conditional_nonmember';cp.totals[item.bucket]=add(cp.totals[item.bucket],sub(rq(item.span.end),rq(item.span.start)));}}
  const sum=t=>Object.values(t).reduce(add,[0n,1n]);if(show(sum(hp.totals))!==show(sum(cp.totals))||show(sum(hp.totals))!==show(rq(data.total_note_time)))throw Error('음가 합 불일치');
  box.append(text('p','전 성부의 동일 음표·음가 '+show(sum(hp.totals))+' quarter를 비교합니다. 조건부 NCT는 표본의 기보 성부만 설명합니다.'));
  const table=document.createElement('table');table.style.width='100%';const header=document.createElement('tr');(cross?['분류','유지','분할(이전)','분할+문맥']:['분류','유지','분할']).forEach(s=>header.append(text('th',s)));table.append(header);
  for(const [key,name] of Object.entries({member:'구성음',conditional_nonmember:'조건부 NCT',unexplained_nonmember:'미설명 비구성음',spelling_unresolved:'철자 미정'})){const row=document.createElement('tr');(cross?[name,show(hp.totals[key]),show(prior[key]),show(cp.totals[key])]:[name,show(hp.totals[key]),show(cp.totals[key])]).forEach(s=>row.append(text('td',s)));table.append(row);}box.append(table);
  hp.items.forEach((item,i)=>{if(item.sid!==cp.items[i].sid)throw Error('음표 불일치');if(item.bucket!==cp.items[i].bucket)changed.add(item.sid);});
  box.append(text('p','보라색: 설명이 달라진 '+changed.size+'개 sounding event. 구간을 가로지르는 음은 일부 음가에서만 달라질 수 있습니다. 주황 점선은 분할 가정 위치입니다.'));
  const names=Object.fromEntries(data.events.map(s=>[s.sounding_event_id,s.pitch.spelling])),buckets={member:'구성음',conditional_nonmember:'조건부 NCT',unexplained_nonmember:'미설명 비구성음',spelling_unresolved:'철자 미정'},seen=new Set();
  hp.items.forEach((item,i)=>{const key=JSON.stringify([item.sid,item.bucket,cp.items[i].bucket]);if(item.bucket!==cp.items[i].bucket&&!seen.has(key)){seen.add(key);box.append(text('p',names[item.sid]+': '+buckets[item.bucket]+' → '+buckets[cp.items[i].bucket]+' (유지 → 분할)'));}});
  const warnings=[...new Set([h,l,r].flatMap(s=>s.condition.abstention_reasons))];if(warnings.length)box.append(text('p','조건부 설명 보류: '+warnings.join(', ')));
  drawOrnamentTimeline(box,b,h,l,r,aid,active);
  drawCoherence(box,b,names,aid);
  drawAssessment(box,b,active,names);
  drawTemporal(box,b,active,names);
  for(const [name,reading] of [['유지',h],['분할 앞',l],['분할 뒤',r]]){if(reading.missing_spellings?.length)box.append(text('p',name+' '+reading.display_label+' · 구간에서 관측되지 않은 구성음: '+reading.missing_spellings.map(([s,a])=>s+(a>0?'#'.repeat(a):'b'.repeat(-a))).join(', ')+'. 불완전한 후보이며 NCT 확정 근거가 아닙니다.'));}
  if(JSON.stringify([...l.members].sort())===JSON.stringify([...r.members].sort()))box.append(text('p','앞뒤 구성음 철자가 같습니다. 이 분할은 화음 변화의 증거가 아닙니다.'));
  if(cross){const labels={cross_boundary_passing_candidate:'경계를 넘는 경과음 형태',cross_boundary_chromatic_passing_candidate:'경계를 넘는 반음계 경과음 형태',cross_boundary_neighbor_candidate:'경계를 넘는 보조음 형태',anticipation_held_candidate:'지속된 선행음 후보',anticipation_reattack_candidate:'재타격 선행음 후보',prepared_suspension_candidate:'지속 후 하행 해결한 계류음 후보'};
   for(const p of active)box.append(text('p',(labels[p.kind]||p.kind)+': '+p.event_refs.map(id=>names[id]).join(' → ')+' · 적용 ['+show(rq(p.nonmember_span.start))+', '+show(rq(p.nonmember_span.end))+') quarter'));
   box.append(text('p','경계 문맥은 실제 지속·철자·같은 성부 연결 가정만 사용합니다. 박절·수직 불협화·양식 적합성은 미검증이며 NCT 확정이 아닙니다.'));
  }else box.append(text('p','경계를 가로지르는 NCT는 이 버전에서 아직 설명하지 않습니다.'));
  box.append(text('p','설명량 차이를 정답 점수로 쓰지 않습니다. 조성·기능·화성 리듬·최종 선택은 미확정입니다.'));
  box.append(text('p','기본 선택은 비교를 보여 주기 위한 사례이며 추천이나 최적 성부 연결이 아닙니다.'));
 }catch(e){box.append(text('p','비교 오류: '+e.message));}mark();}
function sides(initial){const b=data.boundaries[+$('boundary').value];options('left',b?.left.readings||[],r=>r.display_label,initial?.left||0);options('right',b?.right.readings||[],r=>r.display_label,initial?.right||0);draw();}
async function load(){const seq=++serial;data=null;clear();['boundary','hold','left','right','assignment'].forEach(id=>$(id).replaceChildren());$('details').textContent='불러오는 중…';
 try{const response=await fetch('samples/'+$('sample').value+'.json');if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(seq!==serial)return;data=value;const p=data.preview_selection;
 options('boundary',data.boundaries,b=>b.display_boundary+' (분할 가정)',p?.boundary||0);
 options('hold',data.hold_readings,r=>r.display_label,p?.hold||0);
 const ai=data.assignments?.findIndex(a=>a.assignment_id===p?.assignment)||0;
 options('assignment',data.assignments||[],(a,i)=>'조합 '+(i+1)+' · 연결 '+a.links.length+'개'+(!a.links.length?' (무연결)':''),Math.max(0,ai));sides(p);
 }catch(e){if(seq===serial)$('details').textContent='읽기 실패: '+e.message;}}
$('sample').onchange=load;$('boundary').onchange=()=>sides();['hold','left','right','assignment'].forEach(id=>$(id).onchange=draw);window.addEventListener('resize',mark);
const sample=new URLSearchParams(location.search).get('sample');if([...$('sample').options].some(o=>o.value===sample))$('sample').value=sample;load();
