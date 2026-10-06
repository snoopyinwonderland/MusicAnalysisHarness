import {DatabaseSync} from 'node:sqlite';
import {existsSync,statSync} from 'node:fs';
import {contourString,CONTOUR_SEED_VERSION} from '../server/contour-seeds.mjs';
const [source,out]=process.argv.slice(2);if(!out||existsSync(out))throw Error('Source DB and NEW sidecar required');
const st=statSync(source),db=new DatabaseSync(source,{readOnly:true}),target=new DatabaseSync(out);
target.exec('CREATE TABLE metadata(value TEXT); CREATE TABLE streams(id TEXT PRIMARY KEY,contour TEXT,pitches TEXT); PRAGMA journal_mode=DELETE');
const meta={version:CONTOUR_SEED_VERSION,sourceSize:st.size,sourceMtime:st.mtimeMs,complete:false};target.prepare('INSERT INTO metadata VALUES(?)').run(JSON.stringify(meta));
const add=target.prepare('INSERT INTO streams VALUES(?,?,?)');let count=0,notes=0;target.exec('BEGIN');
try{for(const row of db.prepare('SELECT id,notes FROM works').iterate()){
 const p=JSON.parse(row.notes).map(n=>n.p);if(p.some(n=>!Number.isInteger(n)||n<0||n>127))throw Error('Invalid pitch '+row.id);
 add.run(row.id,contourString(p),Buffer.from(p).toString('base64'));count++;notes+=p.length;
 if(count%10000===0){target.exec('COMMIT');if(statSync(out).size>1024**3)throw Error('Contour sidecar exceeds 1 GiB budget');target.exec('BEGIN');console.log(JSON.stringify({count,notes,bytes:statSync(out).size}));}
}target.exec('COMMIT');const end=statSync(source);if(end.size!==st.size||end.mtimeMs!==st.mtimeMs)throw Error('Source changed during build');target.prepare('UPDATE metadata SET value=?').run(JSON.stringify({...meta,complete:true,count,notes}));console.log(JSON.stringify({count,notes,bytes:statSync(out).size,complete:true}));}finally{db.close();target.close()}
