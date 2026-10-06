import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const mscoreExe = 'K:\\MusicSearch\\tools\\musescore3\\MuseScore 3\\bin\\MuseScore3.exe';
const dcmlabDir = 'K:\\MusicSearch\\data\\classical-corpora\\dcmlab';
const jobsDir = 'K:\\MusicSearch\\tools\\dcmlab_jobs';

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

console.log(`Already converted: ${alreadyExists}, Need conversion: ${toConvert.length}`);

if (toConvert.length === 0) {
  console.log('All DCMLab files are already converted!');
  process.exit(0);
}

// Split into batches of 40 files
const batchSize = 40;
const batches = [];
for (let i = 0; i < toConvert.length; i += batchSize) {
  batches.push(toConvert.slice(i, i + batchSize));
}

console.log(`Split ${toConvert.length} items into ${batches.length} batch jobs.`);

let successCount = alreadyExists;
let failCount = 0;

for (let bIdx = 0; bIdx < batches.length; bIdx++) {
  const batch = batches[bIdx];
  const jobFile = path.join(jobsDir, `job_${bIdx}.json`);
  fs.writeFileSync(jobFile, JSON.stringify(batch, null, 2), 'utf8');

  console.log(`Executing batch ${bIdx + 1}/${batches.length} (${batch.length} files)...`);
  const t0 = Date.now();
  try {
    execFileSync(mscoreExe, ['-j', jobFile], { stdio: 'ignore' });
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    
    // Verify results
    let batchSuccess = 0;
    for (const item of batch) {
      if (fs.existsSync(item.out) && fs.statSync(item.out).size > 0) {
        batchSuccess++;
      } else {
        console.warn(`[WARN] Failed to create: ${item.out}`);
        failCount++;
      }
    }
    successCount += batchSuccess;
    console.log(`Batch ${bIdx + 1} finished in ${elapsed}s (${batchSuccess}/${batch.length} ok).`);
  } catch (err) {
    console.error(`Error in batch ${bIdx + 1}: ${err.message}`);
    failCount += batch.length;
  }
}

console.log('\n========================================');
console.log('DCMLab conversion finished!');
console.log(`Total converted / available: ${successCount}`);
console.log(`Failed: ${failCount}`);
