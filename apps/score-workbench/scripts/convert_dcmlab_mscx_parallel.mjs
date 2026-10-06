import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const mscoreExe = 'K:\\MusicSearch\\tools\\musescore3\\MuseScore 3\\bin\\MuseScore3.exe';
const dcmlabDir = 'K:\\MusicSearch\\data\\classical-corpora\\dcmlab';
const jobsDir = 'K:\\MusicSearch\\tools\\dcmlab_parallel_jobs';

if (!fs.existsSync(jobsDir)) {
  fs.mkdirSync(jobsDir, { recursive: true });
}

function findMscxFiles(d) {
  let list = [];
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    if (ent.name === '.git') continue;
    const full = path.join(d, ent.name);
    if (ent.isDirectory()) {
      list = list.concat(findMscxFiles(full));
    } else if (ent.isFile() && ent.name.toLowerCase().endsWith('.mscx')) {
      list.push(full);
    }
  }
  return list;
}

const allMscx = findMscxFiles(dcmlabDir);
console.log(`Found ${allMscx.length} .mscx files in DCMLab.`);

const toConvert = [];
let alreadyExists = 0;

for (const mscx of allMscx) {
  const outXml = mscx.slice(0, -path.extname(mscx).length) + '.musicxml';
  if (fs.existsSync(outXml) && fs.statSync(outXml).size > 0) {
    alreadyExists++;
  } else {
    toConvert.push({ in: mscx, out: outXml });
  }
}

console.log(`Already converted: ${alreadyExists}, Remaining to convert: ${toConvert.length}`);

if (toConvert.length === 0) {
  console.log('All DCMLab files are already converted to MusicXML!');
  process.exit(0);
}

// Split into smaller chunks for fast parallel processing
const CHUNK_SIZE = 20;
const chunks = [];
for (let i = 0; i < toConvert.length; i += CHUNK_SIZE) {
  chunks.push(toConvert.slice(i, i + CHUNK_SIZE));
}

console.log(`Split into ${chunks.length} chunks of up to ${CHUNK_SIZE} files each.`);

const NUM_WORKERS = 4;
let chunkIndex = 0;
let completedFiles = alreadyExists;
let failedFiles = 0;
const startTime = Date.now();

async function runWorker(workerId) {
  while (true) {
    const currentIndex = chunkIndex++;
    if (currentIndex >= chunks.length) {
      break;
    }
    const currentChunk = chunks[currentIndex];
    const jobPath = path.join(jobsDir, `job_w${workerId}_c${currentIndex}.json`);
    fs.writeFileSync(jobPath, JSON.stringify(currentChunk, null, 2), 'utf8');

    const t0 = Date.now();
    try {
      await execFileAsync(mscoreExe, ['-j', jobPath], { windowsHide: true });
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
      
      let chunkOk = 0;
      for (const item of currentChunk) {
        if (fs.existsSync(item.out) && fs.statSync(item.out).size > 0) {
          chunkOk++;
        } else {
          failedFiles++;
        }
      }
      completedFiles += chunkOk;
      const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[Worker ${workerId}] Chunk ${currentIndex + 1}/${chunks.length} done in ${elapsed}s | Total progress: ${completedFiles}/${allMscx.length} (${totalElapsed}s)`);
    } catch (err) {
      console.error(`[Worker ${workerId}] Error in chunk ${currentIndex}: ${err.message}`);
      failedFiles += currentChunk.length;
    } finally {
      try { fs.unlinkSync(jobPath); } catch (e) {}
    }
  }
}

console.log(`Starting ${NUM_WORKERS} parallel MuseScore workers...`);
const workers = [];
for (let w = 1; w <= NUM_WORKERS; w++) {
  workers.push(runWorker(w));
}

await Promise.all(workers);

const totalDuration = ((Date.now() - startTime) / 1000).toFixed(1);
console.log('\n========================================');
console.log(`DCMLab Parallel Conversion Complete in ${totalDuration}s!`);
console.log(`Total Success / Converted: ${completedFiles}/${allMscx.length}`);
console.log(`Failed: ${failedFiles}`);
