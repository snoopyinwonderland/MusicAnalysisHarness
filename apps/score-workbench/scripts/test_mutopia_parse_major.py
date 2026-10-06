import os
import re
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

ftp_dir = r'K:\MusicSearch\data\classical-corpora\mutopia-project\ftp'

test_composers = ['BachJS', 'BeethovenLv', 'ChopinF', 'MozartWA']

for comp in test_composers:
    comp_path = os.path.join(ftp_dir, comp)
    ly_files = glob.glob(os.path.join(comp_path, '**', '*.ly'), recursive=True)[:5]
    for f in ly_files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            txt = fp.read()

        def get_field(k):
            m = re.search(r'^\s*' + k + r'\s*=\s*["\']([^"\']+)["\']', txt, re.MULTILINE | re.IGNORECASE)
            if m:
                return m.group(1).strip()
            m2 = re.search(r'^\s*' + k + r'\s*=\s*([^\n\r%]+)', txt, re.MULTILINE | re.IGNORECASE)
            if m2:
                val = m2.group(1).strip().strip('"\'')
                if not val.startswith(r'\markup'):
                    return val
            return ''

        title = get_field('title') or get_field('mutopiatitle') or os.path.basename(f)
        opus = get_field('opus')
        inst = get_field('mutopiainstrument') or get_field('instrument')

        # Measures
        bar_comments = re.findall(r'%\s*(\d+)\s*$', txt, re.MULTILINE)
        max_bar = 0
        if bar_comments:
            nums = [int(n) for n in bar_comments if n.isdigit() and int(n) < 10000]
            if nums:
                max_bar = max(nums)

        pipes = len(re.findall(r'\|', txt))
        staves = len(re.findall(r'\\new Staff', txt, re.IGNORECASE)) or len(re.findall(r'\\context Staff', txt, re.IGNORECASE)) or len(re.findall(r'\\relative', txt, re.IGNORECASE)) or 1
        
        calc_bars = max_bar if max_bar > 0 else (round(pipes / max(1, staves)) if pipes > 0 else 0)

        # Pages
        pc_m = re.search(r'page-count\s*=\s*#?(\d+)', txt, re.IGNORECASE)
        page_breaks = len(re.findall(r'\\pageBreak', txt))
        
        if pc_m:
            page_str = f"{pc_m.group(1)} (명시)"
        elif page_breaks > 0:
            page_str = f"{page_breaks + 1} (PageBreak)"
        else:
            # Estimate
            rate = 16 if 'piano' in inst.lower() or 'harpsichord' in inst.lower() else (8 if 'quartet' in inst.lower() or 'orchestra' in inst.lower() else 14)
            est = max(1, round(calc_bars / rate)) if calc_bars > 0 else 1
            page_str = f"{est} (추정)"

        size_kb = round(os.path.getsize(f) / 1024, 1)

        print(f"[{comp:11s}] {title[:25]:25s} | Opus: {opus[:12]:12s} | 마디: {calc_bars:3d} | 쪽: {page_str:15s} | {size_kb:5.1f} KB")
