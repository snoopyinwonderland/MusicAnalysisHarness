import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const gitPath = 'C:\\Users\\snoop\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\\cmd\\git.exe';
const baseDir = 'K:\\MusicSearch\\data\\classical-corpora';

if (!fs.existsSync(baseDir)) {
  fs.mkdirSync(baseDir, { recursive: true });
}

const tasks = [
  {
    id: 'openscore-quartets',
    name: 'OpenScore String Quartets',
    url: 'https://github.com/OpenScore/StringQuartets.git',
    targetDir: path.join(baseDir, 'openscore-quartets')
  },
  {
    id: 'openscore-lieder',
    name: 'OpenScore Lieder Corpus (1,300+ songs)',
    url: 'https://github.com/OpenScore/Lieder.git',
    targetDir: path.join(baseDir, 'openscore-lieder')
  },
  {
    id: 'dcmlab-beethoven-quartets',
    name: 'DCMLab Annotated Beethoven Corpus (ABC - String Quartets)',
    url: 'https://github.com/DCMLab/abc.git',
    targetDir: path.join(baseDir, 'dcmlab', 'beethoven-quartets')
  },
  {
    id: 'dcmlab-beethoven-sonatas',
    name: 'DCMLab Beethoven Piano Sonatas (with Roman Numeral Analysis)',
    url: 'https://github.com/DCMLab/beethoven_piano_sonatas.git',
    targetDir: path.join(baseDir, 'dcmlab', 'beethoven-sonatas')
  },
  {
    id: 'dcmlab-mozart-sonatas',
    name: 'DCMLab Mozart Piano Sonatas',
    url: 'https://github.com/DCMLab/mozart_piano_sonatas.git',
    targetDir: path.join(baseDir, 'dcmlab', 'mozart-sonatas')
  },
  {
    id: 'dcmlab-chopin-mazurkas',
    name: 'DCMLab Chopin Mazurkas',
    url: 'https://github.com/DCMLab/chopin_mazurkas.git',
    targetDir: path.join(baseDir, 'dcmlab', 'chopin-mazurkas')
  },
  {
    id: 'dcmlab-corelli',
    name: 'DCMLab Corelli Trio Sonatas',
    url: 'https://github.com/DCMLab/corelli.git',
    targetDir: path.join(baseDir, 'dcmlab', 'corelli')
  },
  {
    id: 'mutopia-project',
    name: 'Mutopia Project (2,000+ Classical Works)',
    url: 'https://github.com/MutopiaProject/MutopiaProject.git',
    targetDir: path.join(baseDir, 'mutopia-project')
  },
  {
    id: 'kernscores-bach-chorales',
    name: 'KernScores / CCARH Bach 371 Four-part Chorales',
    url: 'https://github.com/craigsapp/bach-370-chorales.git',
    targetDir: path.join(baseDir, 'kernscores', 'bach-chorales')
  },
  {
    id: 'kernscores-haydn-quartets',
    name: 'KernScores / CCARH Haydn String Quartets',
    url: 'https://github.com/craigsapp/haydn-string-quartets.git',
    targetDir: path.join(baseDir, 'kernscores', 'haydn-quartets')
  },
  {
    id: 'kernscores-beethoven-sonatas',
    name: 'KernScores / CCARH Beethoven Piano Sonatas',
    url: 'https://github.com/craigsapp/beethoven-piano-sonatas.git',
    targetDir: path.join(baseDir, 'kernscores', 'beethoven-sonatas')
  },
  {
    id: 'kernscores-mozart-sonatas',
    name: 'KernScores / CCARH Mozart Piano Sonatas',
    url: 'https://github.com/craigsapp/mozart-piano-sonatas.git',
    targetDir: path.join(baseDir, 'kernscores', 'mozart-sonatas')
  }
];

console.log(`Starting download of ${tasks.length} classical corpora tasks into ${baseDir}...`);

for (const t of tasks) {
  console.log(`\n========================================`);
  console.log(`[Task: ${t.id}] ${t.name}`);
  console.log(`Source: ${t.url}`);
  console.log(`Destination: ${t.targetDir}`);
  
  if (fs.existsSync(t.targetDir) && fs.existsSync(path.join(t.targetDir, '.git'))) {
    console.log(`Already downloaded. Running git pull...`);
    try {
      execFileSync(gitPath, ['pull'], { cwd: t.targetDir, stdio: 'inherit' });
    } catch (e) {
      console.warn(`Pull skipped or failed: ${e.message}`);
    }
    continue;
  }

  // Ensure parent dir
  const parent = path.dirname(t.targetDir);
  if (!fs.existsSync(parent)) fs.mkdirSync(parent, { recursive: true });

  const t0 = Date.now();
  try {
    execFileSync(gitPath, ['clone', '--depth', '1', t.url, t.targetDir], { stdio: 'inherit' });
    console.log(`Successfully downloaded ${t.id} in ${((Date.now() - t0) / 1000).toFixed(1)}s.`);
  } catch (err) {
    console.error(`Failed to clone ${t.id}: ${err.message}`);
  }
}

console.log(`\n========================================`);
console.log(`All download tasks finished. Generating summary inventory...`);

// Inventory scan
function countFiles(dir, exts) {
  let count = 0;
  if (!fs.existsSync(dir)) return 0;
  function walk(curr) {
    const entries = fs.readdirSync(curr, { withFileTypes: true });
    for (const e of entries) {
      if (e.name === '.git') continue;
      const full = path.join(curr, e.name);
      if (e.isDirectory()) {
        walk(full);
      } else if (e.isFile()) {
        const ext = path.extname(e.name).toLowerCase();
        if (exts.includes(ext)) count++;
      }
    }
  }
  walk(dir);
  return count;
}

const summary = [];
for (const t of tasks) {
  const mscz = countFiles(t.targetDir, ['.mscz', '.mscx']);
  const xml = countFiles(t.targetDir, ['.xml', '.musicxml']);
  const krn = countFiles(t.targetDir, ['.krn']);
  const ly = countFiles(t.targetDir, ['.ly']);
  const tsv = countFiles(t.targetDir, ['.tsv', '.csv']);
  summary.push({
    id: t.id,
    name: t.name,
    targetDir: t.targetDir,
    scoreCounts: { mscz, xml, krn, ly, tsv, totalScores: mscz + xml + krn + ly }
  });
}

console.log(JSON.stringify(summary, null, 2));

fs.writeFileSync(
  path.join(baseDir, 'classical-corpora-inventory.json'),
  JSON.stringify({ generatedAt: new Date().toISOString(), summary }, null, 2),
  'utf8'
);
console.log(`Saved inventory to ${path.join(baseDir, 'classical-corpora-inventory.json')}`);
