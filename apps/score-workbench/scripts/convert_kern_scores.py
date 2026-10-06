import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

def init_worker():
    import music21.metadata
    orig_add = music21.metadata.Metadata.add
    def safe_add(self, name, value):
        try:
            orig_add(self, name, value)
        except KeyError:
            try:
                self.addCustom(name, value)
            except Exception:
                pass
        except Exception:
            pass
    music21.metadata.Metadata.add = safe_add

def convert_single_krn(krn_path):
    target_path = os.path.splitext(krn_path)[0] + '.musicxml'
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return (True, krn_path, target_path, "Already exists", 0.0)

    import music21
    t0 = time.time()
    try:
        s = music21.converter.parse(krn_path)
        s.write('musicxml', fp=target_path)
        elapsed = time.time() - t0
        return (True, krn_path, target_path, "OK", elapsed)
    except Exception as e:
        elapsed = time.time() - t0
        return (False, krn_path, target_path, str(e), elapsed)

def find_all_krn_files(base_dirs):
    krn_files = []
    for b in base_dirs:
        if not os.path.exists(b):
            continue
        for root, dirs, files in os.walk(b):
            if '.git' in root or '.lists' in root:
                continue
            for f in files:
                if f.lower().endswith('.krn'):
                    krn_files.append(os.path.join(root, f))
    return sorted(krn_files)

def main():
    targets = [
        r'K:\MusicSearch\data\classical-corpora\kernscores\bach-chorales',
        r'K:\MusicSearch\data\classical-corpora\kernscores\beethoven-sonatas',
        r'K:\MusicSearch\data\classical-corpora\kernscores\mozart-sonatas',
        r'K:\MusicSearch\data\classical-corpora\kernscores\haydn-sonatas',
        r'K:\MusicSearch\data\classical-corpora\musedata\haydn-symphonies',
        r'K:\MusicSearch\data\classical-corpora\musedata\haydn-quartets',
        r'K:\MusicSearch\data\classical-corpora\musedata\bach-brandenburg'
    ]

    all_files = find_all_krn_files(targets)
    print(f"Total Humdrum .krn scores identified: {len(all_files)}")

    t_start = time.time()
    success_count = 0
    fail_count = 0
    failures = []

    # Using 8 parallel processes for 12 CPU cores
    with ProcessPoolExecutor(max_workers=8, initializer=init_worker) as executor:
        future_to_file = {executor.submit(convert_single_krn, f): f for f in all_files}
        completed = 0
        total = len(all_files)
        for future in as_completed(future_to_file):
            completed += 1
            success, krn, target, msg, elapsed = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1
                failures.append((krn, msg))
                print(f"[FAIL] {os.path.basename(krn)}: {msg}")

            if completed % 50 == 0 or completed == total:
                print(f"Progress: {completed}/{total} ({success_count} succeeded, {fail_count} failed) [{round(time.time() - t_start, 1)}s]")

    print(f"\n==========================================")
    print(f"Humdrum to MusicXML conversion complete!")
    print(f"Total processed: {len(all_files)}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total elapsed time: {round(time.time() - t_start, 1)}s")

    if failures:
        print(f"\nFailure details ({len(failures)}):")
        for f, err in failures[:10]:
            print(f" - {os.path.basename(f)}: {err}")

if __name__ == '__main__':
    main()
