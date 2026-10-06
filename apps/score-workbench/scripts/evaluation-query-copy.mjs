/** Adds clipboard controls without changing saved queries, scores or search responses. */
export function withQueryCopy(html,suite){
 if(html.includes('id="evaluation-query-copy"'))return html;
 const data=suite.cases.map(c=>({id:c.caseId,query:c.query,original:suite.bases.find(b=>b.baseId===c.baseId)?.query}));
 const install=function(data){
  const names=['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
  function compact(q){return q.events.map(e=>(e.kind==='rest'?'쉼표':e.spelling||names[e.pitchMidi%12]+(Math.floor(e.pitchMidi/12)-1))+'('+e.durationRatio+')').join('-');}
  for(const item of data){const section=document.getElementById(item.id);if(!section)continue;
   const articles=section.querySelectorAll('.grid article');
   for(const [i,q] of [item.original,item.query].entries()){if(!q||!articles[i])continue;
    const bar=document.createElement('div'),status=document.createElement('span');status.setAttribute('role','status');
    for(const [label,value] of [['Query JSON 복사',JSON.stringify({schema:'musicanote-query',query:q},null,2)],['간단 표기 복사',compact(q)]]){
     const button=document.createElement('button');button.textContent=label;button.type='button';
     button.onclick=async()=>{try{await navigator.clipboard.writeText(value);status.textContent=' 복사됨';}catch{let box=bar.querySelector('textarea');if(!box){box=document.createElement('textarea');box.rows=5;box.style.width='100%';box.setAttribute('aria-label','수동 복사용 Query');bar.append(box);}box.value=value;box.focus();box.select();status.textContent=' 선택된 내용을 Ctrl+C로 복사해 주세요.';}};bar.append(button);
    }bar.append(status);articles[i].querySelector('h3')?.after(bar);
   }
  }
 };
 const script='<script id="evaluation-query-copy">('+install.toString()+')('+JSON.stringify(data).replaceAll('<','\\u003c')+');</script>';
 new Function(script.slice(script.indexOf('>')+1,script.lastIndexOf('</script>')));
 return html.replace('</html>',script+'</html>');
}
