import os
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor

CONTAINER_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<container>\n'
    b'  <rootfiles>\n'
    b'    <rootfile full-path="score.xml"/>\n'
    b'  </rootfiles>\n'
    b'</container>'
)

def convert_musicxml_to_mxl(xml_path):
    mxl_path = os.path.splitext(xml_path)[0] + '.mxl'
    try:
        if os.path.exists(mxl_path) and os.path.getsize(mxl_path) > 0:
            return (True, xml_path, mxl_path, "Already exists", 0, 0)

        with open(xml_path, 'rb') as f:
            xml_bytes = f.read()

        with zipfile.ZipFile(mxl_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr('META-INF/container.xml', CONTAINER_XML)
            z.writestr('score.xml', xml_bytes)

        orig_size = len(xml_bytes)
        mxl_size = os.path.getsize(mxl_path)
        return (True, xml_path, mxl_path, "OK", orig_size, mxl_size)
    except Exception as e:
        return (False, xml_path, mxl_path, str(e), 0, 0)

def find_xml_files(dirs):
    files_to_convert = []
    for d in dirs:
        if not os.path.exists(d):
            continue
        for root, dirs_list, files in os.walk(d):
            if '.git' in root:
                continue
            for f in files:
                if f.lower().endswith('.musicxml'):
                    files_to_convert.append(os.path.join(root, f))
    return sorted(files_to_convert)

def main():
    targets = [
        r'K:\MusicSearch\data\classical-corpora\dcmlab',
        r'K:\MusicSearch\data\classical-corpora\kernscores',
        r'K:\MusicSearch\data\classical-corpora\musedata'
    ]

    all_files = find_xml_files(targets)
    print(f"Found {len(all_files)} .musicxml files to convert to .mxl.")

    t0 = time.time()
    success = 0
    failed = 0
    total_orig = 0
    total_mxl = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(convert_musicxml_to_mxl, all_files)
        for ok, xml_p, mxl_p, msg, orig_s, mxl_s in results:
            if ok:
                success += 1
                total_orig += orig_s
                total_mxl += mxl_s
            else:
                failed += 1
                print(f"[FAIL] {os.path.basename(xml_p)}: {msg}")

    elapsed = time.time() - t0
    orig_mb = total_orig / (1024 * 1024)
    mxl_mb = total_mxl / (1024 * 1024)
    ratio = (total_mxl / total_orig * 100) if total_orig > 0 else 0

    print("\n==========================================")
    print(f"MusicXML to MXL conversion complete in {round(elapsed, 2)}s!")
    print(f"Total files: {len(all_files)}")
    print(f"Success: {success}, Failed: {failed}")
    print(f"Original size: {round(orig_mb, 2)} MB")
    print(f"Compressed .mxl size: {round(mxl_mb, 2)} MB")
    print(f"Compression ratio: {round(ratio, 1)}% (Space saved: {round(100 - ratio, 1)}%)")

if __name__ == '__main__':
    main()
