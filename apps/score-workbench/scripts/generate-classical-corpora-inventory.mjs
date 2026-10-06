import fs from 'node:fs';
import path from 'node:path';

const baseDir = 'K:\\MusicSearch\\data\\classical-corpora';

function scanDir(dir) {
  const stats = {
    mscz: 0,
    mscx: 0,
    mxl: 0,
    xml: 0,
    krn: 0,
    ly: 0,
    tsv: 0,
    rntxt: 0,
    pdf: 0,
    totalMusicFiles: 0,
    totalFiles: 0
  };

  function walk(current) {
    let list;
    try {
      list = fs.readdirSync(current, { withFileTypes: true });
    } catch (e) {
      return;
    }
    for (const item of list) {
      if (item.name === '.git') continue;
      const fullPath = path.join(current, item.name);
      if (item.isDirectory()) {
        walk(fullPath);
      } else if (item.isFile()) {
        stats.totalFiles++;
        const ext = path.extname(item.name).toLowerCase();
        if (ext === '.mscz') stats.mscz++;
        else if (ext === '.mscx') stats.mscx++;
        else if (ext === '.mxl') stats.mxl++;
        else if (ext === '.xml' || ext === '.musicxml') stats.xml++;
        else if (ext === '.krn') stats.krn++;
        else if (ext === '.ly') stats.ly++;
        else if (ext === '.tsv') stats.tsv++;
        else if (ext === '.rntxt') stats.rntxt++;
        else if (ext === '.pdf') stats.pdf++;
      }
    }
  }

  walk(dir);
  // Total usable score files (either MusicXML/compressed mxl, MuseScore mscz/mscx, Humdrum krn, or LilyPond ly)
  stats.totalMusicFiles = stats.mscz + stats.mscx + stats.mxl + stats.xml + stats.krn + stats.ly;
  return stats;
}

const corpora = [
  {
    group: '1. OpenScore (Peer-Reviewed Open MusicXML)',
    corpora: [
      { id: 'openscore-quartets', name: 'OpenScore String Quartets (Full Scores & Parts)', dir: path.join(baseDir, 'openscore-quartets') },
      { id: 'openscore-lieder', name: 'OpenScore Lieder Corpus (19th-Century Art Songs)', dir: path.join(baseDir, 'openscore-lieder') }
    ]
  },
  {
    group: '2. DCMLab (EPFL Lausanne - Annotated Classical Corpora)',
    corpora: [
      { id: 'dcmlab-beethoven-quartets', name: 'Beethoven String Quartets (ABC Corpus + Harmonies)', dir: path.join(baseDir, 'dcmlab', 'beethoven-quartets') },
      { id: 'dcmlab-beethoven-sonatas', name: 'Beethoven Piano Sonatas (with Roman Numeral TSV)', dir: path.join(baseDir, 'dcmlab', 'beethoven-sonatas') },
      { id: 'dcmlab-mozart-sonatas', name: 'Mozart Piano Sonatas (Harmonically Annotated)', dir: path.join(baseDir, 'dcmlab', 'mozart-sonatas') },
      { id: 'dcmlab-chopin-mazurkas', name: 'Chopin Mazurkas (Harmonically Annotated)', dir: path.join(baseDir, 'dcmlab', 'chopin-mazurkas') },
      { id: 'dcmlab-corelli', name: 'Corelli Trio Sonatas (Op. 1 - Op. 6)', dir: path.join(baseDir, 'dcmlab', 'corelli') }
    ]
  },
  {
    group: '3. KernScores (Stanford CCARH Humdrum Scores)',
    corpora: [
      { id: 'kern-bach-chorales', name: 'J.S. Bach 371 Four-Part Chorales (Complete)', dir: path.join(baseDir, 'kernscores', 'bach-chorales') },
      { id: 'kern-beethoven-sonatas', name: 'Beethoven 32 Piano Sonatas', dir: path.join(baseDir, 'kernscores', 'beethoven-sonatas') },
      { id: 'kern-mozart-sonatas', name: 'Mozart Piano Sonatas (Complete)', dir: path.join(baseDir, 'kernscores', 'mozart-sonatas') },
      { id: 'kern-haydn-sonatas', name: 'Haydn Piano Sonatas', dir: path.join(baseDir, 'kernscores', 'haydn-sonatas') },
      { id: 'kern-humdrum-meta', name: 'Humdrum Data Meta-Repository (Craig Sapp)', dir: path.join(baseDir, 'kernscores', 'humdrum-data') }
    ]
  },
  {
    group: '4. MuseData (Stanford CCARH Orchestral Scores)',
    corpora: [
      { id: 'musedata-haydn-symphonies', name: 'Haydn Symphonies (Full Scores & Parts)', dir: path.join(baseDir, 'musedata', 'haydn-symphonies') },
      { id: 'musedata-haydn-quartets', name: 'Haydn String Quartets', dir: path.join(baseDir, 'musedata', 'haydn-quartets') },
      { id: 'musedata-bach-brandenburg', name: 'J.S. Bach Brandenburg Concertos', dir: path.join(baseDir, 'musedata', 'bach-brandenburg') }
    ]
  },
  {
    group: '5. Mutopia Project (Community Public Domain Classical Archive)',
    corpora: [
      { id: 'mutopia-archive', name: 'Mutopia Classical Archive (Bach, Beethoven, Chopin, Brahms, etc.)', dir: path.join(baseDir, 'mutopia-project') }
    ]
  }
];

let globalTotalMusicScores = 0;
let globalAnnotations = 0;
const results = [];

for (const cat of corpora) {
  const catRes = { category: cat.group, items: [] };
  for (const item of cat.corpora) {
    const stats = scanDir(item.dir);
    catRes.items.push({
      id: item.id,
      name: item.name,
      path: item.dir,
      exists: fs.existsSync(item.dir),
      stats
    });
    globalTotalMusicScores += (stats.mscz + stats.mxl + stats.krn + stats.ly);
    globalAnnotations += (stats.tsv + stats.rntxt);
  }
  results.push(catRes);
}

const summaryOutput = {
  timestamp: new Date().toISOString(),
  totalScoresAcquired: globalTotalMusicScores,
  totalHarmonicAnnotationFiles: globalAnnotations,
  categories: results
};

fs.writeFileSync(
  path.join(baseDir, 'classical-corpora-inventory.json'),
  JSON.stringify(summaryOutput, null, 2),
  'utf8'
);

console.log('Successfully written inventory:');
console.log('Total Musical Scores / Movements Acquired:', globalTotalMusicScores);
console.log('Total Ground-Truth Harmonic Annotation Files:', globalAnnotations);
