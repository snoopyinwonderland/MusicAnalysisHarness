const $ = id => document.getElementById(id);
let data, serial = 0;
let initialEdge = new URLSearchParams(location.search).get('edge');
const roman = {V:'V',V7:'V7',vii:'viio',vii7:'viio7',vii_half7:'viiø7'};
const statuses = {resolution_supported_hypothesis:'직접 성부 진행과 도착 근거 있음 · 가설',shape_relation_only:'화음 형태 관계만 확인',blocked_context:'문맥 판정 보류'};
function text(tag, value) { const n = document.createElement(tag); n.textContent = value; return n; }
function clear() {
  document.querySelectorAll('.source-mark,.target-mark,.shared-mark,.context-mark').forEach(n=>n.classList.remove('source-mark','target-mark','shared-mark','context-mark'));
  document.querySelectorAll('.range-box').forEach(n=>n.remove());
}
function draw() {
  clear(); const e = data?.edges[+$('edge').value]; const box = $('details'); box.replaceChildren();
  $('show').disabled = !e;
  if (!e) { box.append(text('p','연결 가능한 Secondary 계열 가설이 없습니다. 다른 화음 후보가 없다는 뜻은 아닙니다.')); return; }
  box.append(text('h3',statuses[e.status]),text('p',e.source_display_label+' → '+e.target_display_label));
  const terminal=e.source_time.terminal_support_span;
  const frac=q=>q.numerator+'/'+q.denominator;
  box.append(text('p',terminal?'출발 화음의 핵심음 동시 지지: quarter '+frac(terminal.start)+' ~ '+frac(terminal.end):'출발 핵심음이 끝까지 함께 울리는 구간은 확인하지 못했습니다. 분산·지연 해결은 추가 검토가 필요합니다.'));
  box.append(text('p','도착 시점 근음·3음: '+(e.target_identity_at_boundary?'관측됨':'불충분')));
  if(e.target_arrival){
    const a=e.target_arrival;
    box.append(text('p','목표 근음·3음 누적 관측 시점: '+(a.cumulative_identity_time?frac(a.cumulative_identity_time):'창 안에서 미완성')+' / 실제 동시 관측 시작: '+(a.first_simultaneous_identity_time?frac(a.first_simultaneous_identity_time):'없음')+' (quarter 좌표)'));
    for(const d of e.delayed_endpoint_hypotheses)box.append(text('p','지연 연결 가설: '+d.source_pitch+' → '+d.target_pitch+' · 지연 '+frac(d.delay_quarters)+' quarter · 직접 해결 아님'+(d.audit.review_reasons.length?' · 경고: '+d.audit.review_reasons.join(', '):'')));
  }
  for(const s of e.direct_voice_support) box.append(text('p',s.source_pitch+' → '+s.target_pitch+' · '+s.relations.map(r=>r==='leading_tone_to_target_root'?'이끎음 상행':'7음 순차 하행').join(', ')+(s.dependency_group?' · 옥타브 중복':'') ));
  for(const pid of e.arrival_path_refs||[]){
    const p=data.arrival_path_assessment.paths[pid],o=p.observation;
    box.append(text('h4',(data.bounded_path_context?'기존 고정창 검사 · ':'중간 경로 · ')+'음표 생략 없음'));
    const pitches=Object.fromEntries(o.events.map(n=>[n.event_ref,n.pitch.spelling]));
    box.append(text('p',o.attack_groups.map(g=>g.event_refs.map(id=>pitches[id]).join(' + ')).join(' → ')+' (동시음은 +로 묶음 · 선율 연결 확정 아님)'));
    const reasons={full_path_outside_frozen_context:'경로 전체가 이번 검사 범위에 들어오지 않음',arrival_polyphony_or_sustained_overlap:'같은 기보 성부의 동시음/지속음이 겹침',grace_timing_unresolved:'장식음 시간 미확정',meter_unavailable_or_changed:'박자 미확정 또는 변경',repeat_or_ending_barrier:'반복/엔딩 경계'};
    if(o.abstention_reasons.length)box.append(text('p','경로 보류: '+o.abstention_reasons.map(r=>reasons[r]||r).join(', ')));
    for(const c of p.conditions.filter(c=>c.edge_refs.includes(e.edge_id))){
      const kind=c.hypothesis==='source_hold_counterfactual'?'출발 화음 유지 가정':'도착 화음 가정';
      const terms={chord_member_unfolding_compatible:'구성음 펼침과 양립',local_ornament_geometry_compatible:'조건부 장식음 형태와 양립'};
      box.append(text('p',kind+(c.outside_extension_assumption?' · 원래 후보 범위 밖 연장 가정':c.outside_candidate_span?' · 후보 범위 밖 음 포함으로 보류':'')+': '+(c.compatible_patterns.map(t=>terms[t]||t).join(', ')||'설명 미확정')));
    }
    box.append(text('p','다른 화음 가능성 검토용 세부 시간 구간 '+p.alternative_cell_catalog_refs.length+'개 · 후보 존재만으로 화음 교체를 확정하지 않습니다.'));
    const expanded=data.bounded_path_context?.paths[pid];
    if(expanded){
      const policy=expanded.context_policy;
      box.append(text('h4','추가 관찰 · 기존 판정과 별도'));
      box.append(text('p','quarter '+frac(policy.original_span.start)+'–'+frac(policy.original_span.end)+' → '+frac(policy.proposed_span.start)+'–'+frac(policy.proposed_span.end)+' · '+(policy.accepted?'관찰 범위 허용':'확장 보류: '+policy.abstention_reasons.join(', '))));
      if(policy.accepted){
        box.append(text('p','새로 포함된 sounding event '+policy.added_sound_refs.length+'개 · 화음 지속 범위를 늘린 것은 아닙니다. 기존 범위 밖 지속음도 원래 음가를 보존합니다.'));
        const show=text('button','확장 관찰 음표 보기 (화음 범위 아님)');
        show.onclick=()=>{clear();const ids=new Set(policy.source_note_refs);let first;
          document.querySelectorAll('.scorepage .note').forEach(n=>{if(ids.has(n.dataset.id||n.id)){n.classList.add('context-mark');first=first||n;}});
          if(first)first.scrollIntoView({block:'center',behavior:'smooth'});
        };box.append(show);
        box.append(text('p','남은 경로 보류: '+(expanded.observation.abstention_reasons.map(r=>reasons[r]||r).join(', ')||'없음 (성부 연결 확정 아님)')));
        for(const g of expanded.polyphonic_observation.groups){
          const details=document.createElement('details');details.append(text('summary','quarter '+frac(g.time)+' · '+g.assignments.length+'개 부분 대응 (무연결 포함, 확률 아님)'));
          for(const a of g.assignments){
            const links=a.edge_indices.map(i=>g.edges[i].source_pitch.spelling+' → '+g.edges[i].target_pitch.spelling);
            details.append(text('p',(links.join(' / ')||'모두 연결하지 않음')+' · 미연결 출발 '+a.unmatched_source_refs.length+'음, 도착 '+a.unmatched_target_refs.length+'음 · 교차 '+a.crossing_count+'개'));
          }box.append(details);
        }
        for(const a of expanded.polyphonic_observation.abstentions)box.append(text('p','성부 대응 보류: '+a.reason));
        box.append(text('p','세부 화음 후보 구간 '+expanded.alternative_cell_catalog_refs.length+'개 · 전체 선율 경로/화음 교체는 아직 선택하지 않았습니다.'));
      }
    }
    const tracks=data.continuous_voice_paths?.paths[pid];
    if(tracks){
      box.append(text('h4','연속 경로 후보 · 음표 중복/누락 검사'));
      if(!tracks.enumeration_complete)box.append(text('p','전체 조합 보류: '+(tracks.abstention_reasons||[tracks.status]).join(', ')));
      else{
        box.append(text('p',tracks.assignments.length+'개 조합 모두 음표 1회 사용·음가 보존. 출발/도착 끝점이 같은 연속 경로에 속한 조합 '+tracks.endpoint_same_track_assignments+'개. 연결 수는 확률이나 정확도가 아닙니다.'));
        const names=Object.fromEntries(tracks.events.map(s=>[s.sounding_event_id,s.pitch.spelling]));
        const select=document.createElement('select');select.setAttribute('aria-label','연속 성부 경로 조합');
        for(const [i,a] of tracks.assignments.entries()){
          const option=text('option','조합 '+(i+1)+' · '+a.links.length+'연결 / '+a.tracks.length+'경로'+(!a.links.length?' · 모두 무연결':''));option.value=i;select.append(option);
        }
        const preview=document.createElement('div');
        const render=()=>{preview.replaceChildren();const a=tracks.assignments[+select.value];
          for(const [i,chain] of a.tracks.entries())preview.append(text('p','경로 '+(i+1)+': '+chain.map(id=>names[id]).join(' → ')+(chain.length===1?' (독립 음)':'')));
        };
        select.onchange=render;box.append(select,preview);render();
        box.append(text('p','기본 표시는 무연결 대안이며 추천이 아닙니다. 쉼을 건너는 연속 성부는 만들지 않았습니다. 화음은 아직 선택하지 않았습니다.'));
      }
    }
    const ornaments=data.path_conditioned_ornaments?.paths[pid];
    if(ornaments){
      box.append(text('h4','성부 경로별 비화성음 설명 · 조건부'));
      for(const c of ornaments.conditions.filter(c=>c.edge_refs.includes(e.edge_id))){
        box.append(text('p',(c.mode==='source_hold_counterfactual'?'출발 화음 유지 가정':'도착 후보 원래 범위')+(c.outside_extension_assumption?' · 명시적 연장 가정':'')+': '+(c.abstention_reasons.length?'보류 ('+c.abstention_reasons.join(', ')+')':c.patterns.length+'개 조건부 음형')));
        box.append(text('p','관찰 음가 합 '+frac(c.all_note_time)+' quarter · 비구성음 '+frac(c.note_time_by_state.nonmember_not_confirmed_nct)+' quarter 유지 (해당 기보 성부만)'));
        for(const p of c.patterns){
          const role={passing_candidate:'경과음 형태',neighbor_candidate:'보조음 형태',chromatic_passing_candidate:'반음계 경과음 형태'}[p.conditional_role]||p.conditional_role;
          box.append(text('p',role+' · '+(p.common_to_all_assignments?'모든 연결 가정에서 공통':'일부 연결 가정에만 존재')+' · 확정 NCT 아님'));
        }
        if(!c.abstention_reasons.length&&!c.patterns.length)box.append(text('p','지원하는 연속 3음 설명 없음. 비화성음이 없다는 뜻은 아닙니다.'));
      }
      box.append(text('p','무연결 대안도 포함합니다. 설명 횟수는 확률이 아니며 음표를 삭제하거나 화음 점수를 올리지 않습니다.'));
    }
  }
  if(e.abstention_reasons.length)box.append(text('p','보류 근거: '+e.abstention_reasons.join(', ')));
  const spells=ps=>ps.map(([s,a])=>s+(a>0?'#'.repeat(a):'b'.repeat(-a))).join(', ')||'없음';
  box.append(text('p','미관측 구성음: 출발 '+spells(e.source_missing_spellings)+' / 도착 '+spells(e.target_missing_spellings)));
  box.append(text('p','기능 확정·국소 조성·전위·종지·추천 순위는 아직 판단하지 않았습니다.'));
  mark(false);
}
function mark(scroll = true) {
  clear();const e=data?.edges[+$('edge').value];if(!e)return;
  const sets={source:new Set(data.display_notes.source),target:new Set(data.display_notes.target)};let first;
  const groups=new Map();
  document.querySelectorAll('.scorepage .note').forEach(n=>{
    const id=n.dataset.id||n.id;const a=sets.source.has(id),b=sets.target.has(id);if(!a&&!b)return;
    n.classList.add(a&&b?'shared-mark':a?'source-mark':'target-mark');first=first||n;
    const page=n.closest('.scorepage');if(!groups.has(page))groups.set(page,{source:[],target:[]});
    if(a)groups.get(page).source.push(n);if(b)groups.get(page).target.push(n);
  });
  for(const [page,sides] of groups)for(const [side,notes] of Object.entries(sides)){
    if(!notes.length)continue;const p=page.getBoundingClientRect(),rs=notes.map(n=>n.getBoundingClientRect());
    const left=Math.max(0,Math.min(...rs.map(r=>r.left))-p.left-5),top=Math.max(24,Math.min(...rs.map(r=>r.top))-p.top-5);
    const box=text('div','');box.className='range-box '+side;Object.assign(box.style,{left:left+'px',top:top+'px',width:Math.max(...rs.map(r=>r.right))-p.left-left+5+'px',height:Math.max(...rs.map(r=>r.bottom))-p.top-top+5+'px'});
    const label=text('span',side==='source'?roman[e.family]+' ?':(e.target_quality==='M'?'I':'i')+' ?');label.className='roman';label.title='도착 화음의 3화음 핵심 기준 기능 가설 · 전위/추가음 미표기';box.append(label);page.append(box);
  }
  if(first && scroll)first.scrollIntoView({block:'center',behavior:'smooth'});
}
async function load(){const request=++serial;clear();data=null;$('edge').replaceChildren();$('edge').disabled=true;$('show').disabled=true;$('details').textContent='불러오는 중…';
  try{const response=await fetch('pairs/'+$('range').value+'.json');if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(request!==serial)return;data=value;
    $('edge').replaceChildren(...data.edges.map((e,i)=>{const n=text('option',e.source_display_label+' → '+e.target_display_label+' · '+statuses[e.status]);n.value=i;return n;}));
    if([...$('edge').options].some(o=>o.value===initialEdge))$('edge').value=initialEdge;
    initialEdge=null;$('edge').disabled=false;draw();
  }catch(e){if(request===serial)$('details').textContent='읽기 실패: '+e.message;}}
$('range').onchange=load;$('edge').onchange=draw;$('show').onclick=()=>mark(true);
window.addEventListener('resize',()=>{if(!document.querySelector('.context-mark'))mark(false);});
const requestedPair=new URLSearchParams(location.search).get('pair');
if([...$('range').options].some(o=>o.value===requestedPair))$('range').value=requestedPair;
load();
