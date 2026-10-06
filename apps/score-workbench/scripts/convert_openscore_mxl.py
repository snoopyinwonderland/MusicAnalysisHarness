import os
import zipfile
import xml.etree.ElementTree as ET
import time
from concurrent.futures import ThreadPoolExecutor

def get_rootfile_from_container(container_xml_bytes):
    try:
        root = ET.fromstring(container_xml_bytes)
        for elem in root.iter():
            if elem.tag.endswith('rootfile'):
                full_path = elem.attrib.get('full-path')
                if full_path:
                    return full_path
    except Exception:
        pass
    return None

def convert_single_mxl(mxl_path):
    try:
        target_path = os.path.splitext(mxl_path)[0] + '.musicxml'
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            return (True, mxl_path, "Already exists")

        with zipfile.ZipFile(mxl_path, 'r') as z:
            namelist = z.namelist()
            rootfile_name = None
            if 'META-INF/container.xml' in namelist:
                container_data = z.read('META-INF/container.xml')
                rootfile_name = get_rootfile_from_container(container_data)

            if not rootfile_name or rootfile_name not in namelist:
                candidates = [n for n in namelist if n.endswith('.xml') and not n.startswith('META-INF')]
                if candidates:
                    rootfile_name = candidates[0]
                else:
                    return (False, mxl_path, "No xml found in zip")

            xml_data = z.read(rootfile_name)
            with open(target_path, 'wb') as out_f:
                out_f.write(xml_data)

        return (True, mxl_path, f"Extracted {len(xml_data)} bytes")
    except Exception as e:
        return (False, mxl_path, str(e))

def process_directory(base_dir):
    mxl_files = []
    for root, dirs, files in os.walk(base_dir):
        if '.git' in root:
            continue
        for f in files:
            if f.lower().endswith('.mxl'):
                mxl_files.append(os.path.join(root, f))
    return mxl_files

def main():
    dirs_to_scan = [
        r'K:\MusicSearch\data\classical-corpora\openscore-quartets',
        r'K:\MusicSearch\data\classical-corpora\openscore-lieder'
    ]

    all_mxl = []
    for d in dirs_to_scan:
        if os.path.exists(d):
            files = process_directory(d)
            print(f"Found {len(files)} .mxl files in {d}")
            all_mxl.extend(files)

    print(f"\nTotal .mxl files to convert/extract: {len(all_mxl)}")
    t0 = time.time()

    success_count = 0
    fail_count = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        for success, path, msg in executor.map(convert_single_mxl, all_mxl):
            if success:
                success_count += 1
            else:
                fail_count += 1
                print(f"[FAIL] {path}: {msg}")

    print(f"\nDone in {round(time.time() - t0, 2)}s.")
    print(f"Success: {success_count}, Failed: {fail_count}")

if __name__ == '__main__':
    main()
