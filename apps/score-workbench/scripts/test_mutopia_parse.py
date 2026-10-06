import os
import re
import glob

ftp_dir = r'K:\MusicSearch\data\classical-corpora\mutopia-project\ftp'
sample_files = glob.glob(os.path.join(ftp_dir, '**', '*.ly'), recursive=True)

print(f"Total .ly files found in ftp: {len(sample_files)}")

for f in sample_files[:15]:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            txt = fp.read()
    except Exception:
        continue

    def get_field(k):
        # Match k = "..." or k = \markup ...
        m = re.search(r'^\s*' + k + r'\s*=\s*["\']([^"\']+)["\']', txt, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m2 = re.search(r'^\s*' + k + r'\s*=\s*([^\n\r%]+)', txt, re.MULTILINE | re.IGNORECASE)
        if m2:
            val = m2.group(1).strip().strip('"\'')
            if not val.startswith(r'\markup'):
                return val
        return ''

    title = get_field('title') or get_field('mutopiatitle')
    composer = get_field('composer') or get_field('mutopiacomposer')
    opus = get_field('opus')
    instrument = get_field('mutopiainstrument')
    footer = get_field('footer')
    date = get_field('date')
    style = get_field('style')

    # Page count detection
    pc_m = re.search(r'page-count\s*=\s*#?(\d+)', txt, re.IGNORECASE)
    explicit_pages = int(pc_m.group(1)) if pc_m else None
    page_breaks = len(re.findall(r'\\pageBreak', txt))

    # Measure detection
    bar_comments = re.findall(r'%\s*(\d+)\s*$', txt, re.MULTILINE)
    max_bar_comment = 0
    if bar_comments:
        nums = [int(n) for n in bar_comments if n.isdigit() and int(n) < 10000]
        if nums:
            max_bar_comment = max(nums)

    pipes = len(re.findall(r'\|', txt))
    file_kb = round(os.path.getsize(f) / 1024, 1)

    print(f"File: {os.path.basename(f):20s} | Comp: {composer[:15]:15s} | Title: {title[:20]:20s} | Bars: {max_bar_comment:3d} (pipes: {pipes:3d}) | Pgs: {explicit_pages or (page_breaks + 1 if page_breaks else 'auto')} | {file_kb} KB")
