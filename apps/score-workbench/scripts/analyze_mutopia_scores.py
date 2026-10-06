import os
import re

ftp_dir = r'K:\MusicSearch\data\classical-corpora\mutopia-project\ftp'

footers = set()
ly_count = 0
header_count = 0

for root, dirs, files in os.walk(ftp_dir):
    for f in files:
        if f.endswith('.ly'):
            ly_count += 1
            full_path = os.path.join(root, f)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                m = re.search(r'footer\s*=\s*["\'](Mutopia-[^"\']+)["\']', content, re.IGNORECASE)
                if m:
                    footers.add(m.group(1))
                if r'\header' in content:
                    header_count += 1
            except Exception:
                pass

print(f"Total .ly files: {ly_count}")
print(f"Files with \\header: {header_count}")
print(f"Unique Mutopia footer IDs: {len(footers)}")
