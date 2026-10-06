import os
import sys
import json
import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DATA = r"K:\MusicSearch\data"

CATEGORY_DIRS = {
    "Classical Corpora": os.path.join(BASE_DATA, "classical-corpora"),
    "Pop & Global Analysis Corpora": os.path.join(BASE_DATA, "pop-and-analysis-corpora"),
    "Jazz Corpora": os.path.join(BASE_DATA, "jazz-corpora"),
    "Global Pop, Karaoke & MIDI Corpora": os.path.join(BASE_DATA, "global-pop-midi")
}

EXTENSIONS = [
    'mscz', 'mscx', 'mxl', 'musicxml', 'krn', 'ly',
    'tsv', 'rntxt', 'csv', 'json', 'jams', 'ttl',
    'mid', 'midi', 'kar', 'txt', 'db', 'sqlite', 'pdf'
]

master_inventory = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "categories": {},
    "grandTotals": {}
}

total_corpora = 0
total_files = 0
total_mxl = 0
total_musicxml = 0
total_humdrum_krn = 0
total_lilypond_ly = 0
total_midi = 0
total_structural_and_harmonic_annotations = 0
total_bytes = 0

for cat_name, cat_path in CATEGORY_DIRS.items():
    if not os.path.exists(cat_path):
        continue
    
    cat_entry = {"corpora": {}, "totals": {}}
    cat_files = 0
    cat_bytes = 0
    cat_ext_counts = {ext: 0 for ext in EXTENSIONS}
    
    for sub in sorted(os.listdir(cat_path)):
        sub_path = os.path.join(cat_path, sub)
        if not os.path.isdir(sub_path):
            continue
        
        # Exclude git internal folder if direct child (usually inside repo)
        corp_counts = {ext: 0 for ext in EXTENSIONS}
        corp_files = 0
        corp_bytes = 0
        
        for root, dirs, files in os.walk(sub_path):
            if '.git' in dirs:
                dirs.remove('.git')
            for f in files:
                corp_files += 1
                try:
                    f_size = os.path.getsize(os.path.join(root, f))
                    corp_bytes += f_size
                except Exception:
                    pass
                
                parts = f.lower().split('.')
                ext = parts[-1] if len(parts) > 1 else ''
                if ext in corp_counts:
                    corp_counts[ext] += 1
        
        corp_entry = {}
        for ext in EXTENSIONS:
            corp_entry[ext] = corp_counts[ext]
        corp_entry["totalFiles"] = corp_files
        corp_entry["sizeMB"] = round(corp_bytes / (1024 * 1024), 2)
        
        cat_entry["corpora"][sub] = corp_entry
        total_corpora += 1
        cat_files += corp_files
        cat_bytes += corp_bytes
        for ext in EXTENSIONS:
            cat_ext_counts[ext] += corp_counts[ext]
    
    cat_entry["totals"] = {
        "corporaCount": len(cat_entry["corpora"]),
        "totalFiles": cat_files,
        "sizeMB": round(cat_bytes / (1024 * 1024), 2),
        "sizeGB": round(cat_bytes / (1024 * 1024 * 1024), 2),
        **cat_ext_counts
    }
    
    master_inventory["categories"][cat_name] = cat_entry
    total_files += cat_files
    total_bytes += cat_bytes
    total_mxl += cat_ext_counts['mxl']
    total_musicxml += cat_ext_counts['musicxml']
    total_humdrum_krn += cat_ext_counts['krn']
    total_lilypond_ly += cat_ext_counts['ly']
    total_midi += cat_ext_counts['mid'] + cat_ext_counts['midi'] + cat_ext_counts['kar']
    total_structural_and_harmonic_annotations += (
        cat_ext_counts['tsv'] + cat_ext_counts['rntxt'] + cat_ext_counts['csv'] +
        cat_ext_counts['jams'] + cat_ext_counts['ttl']
    )

master_inventory["grandTotals"] = {
    "total_corpora": total_corpora,
    "total_files": total_files,
    "total_mxl": total_mxl,
    "total_musicxml": total_musicxml,
    "total_humdrum_krn": total_humdrum_krn,
    "total_lilypond_ly": total_lilypond_ly,
    "total_midi_and_kar": total_midi,
    "total_structural_and_harmonic_annotations": total_structural_and_harmonic_annotations,
    "total_size_gb": round(total_bytes / (1024 * 1024 * 1024), 2)
}

# Add local Korean Karaoke reference
master_inventory["korean_karaoke_reference"] = {
    "archive_path": "K:\\KYSing_MusicXML.zip",
    "total_songs": 50875,
    "archive_size_mb": 1464.3,
    "metadata_path": "K:\\MusicSearch\\data\\kysing-metadata\\kumyoung-2026-09-03-all.json"
}

output_path = os.path.join(BASE_DATA, "music-corpora-master-inventory.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(master_inventory, f, indent=2, ensure_ascii=False)

print(f"Master inventory successfully updated at: {output_path}")
print(f"Grand Totals: {master_inventory['grandTotals']}")
