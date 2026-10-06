import {readdirSync,readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
export function structurePreviewApiPlugin(){return {name:'structure-preview-readonly',configureServer(server){server.middlewares.use('/api/structure-preview',(req,res)=>{
 res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');
 if(req.method!=='GET'){res.statusCode=405;res.end('{}');return;}
 const id=new URL(req.url,'http://localhost').searchParams.get('workId');
 if(!/^work-[a-f0-9]+(?:-[a-f0-9]+)*$/.test(id??'')){res.statusCode=400;res.end('{}');return;}
 try{
  const root=resolve('evaluation/case-assets');
  for(const entry of readdirSync(root,{withFileTypes:true})){
   if(!entry.isDirectory()||!/^S-STRUCT-\d+$/.test(entry.name))continue;
   const path=resolve(root,entry.name),fp=resolve(path,'feedback-revision-02.json'),sp=resolve(path,'review-snapshot.json');
   if(!existsSync(fp)||!existsSync(sp))continue;
   const feedback=JSON.parse(readFileSync(fp)),snapshot=JSON.parse(readFileSync(sp)),w=snapshot.work;
   if(w.workId!==id||!Array.isArray(feedback.ranges))continue;
   res.end(JSON.stringify({schema:'structure-preview/v1',workId:id,streamId:w.streamId,sourceHash:snapshot.xmlSha256,caseId:entry.name,origin:'user-preferred-interpretation-not-algorithm-selection',noteIdentity:w.notes.map(n=>[n.id,n.pitchMidi,n.onset,n.durationRatio,n.measure,n.beat]),ranges:feedback.ranges}));return;
  }
  res.statusCode=404;res.end(JSON.stringify({message:'저장된 검토 범위 없음'}));
 }catch{res.statusCode=500;res.end(JSON.stringify({message:'검토 범위를 읽지 못했습니다.'}));}
 });}};}
