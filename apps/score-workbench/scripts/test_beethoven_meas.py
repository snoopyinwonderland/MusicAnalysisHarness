import re
from fractions import Fraction

def parse_lilypond_measures(content):
    # 1. Check for explicit bar comment numbers (e.g. % 120 or % 1)
    bar_comments = re.findall(r'%\s*(\d+)\s*$', content, re.MULTILINE)
    if bar_comments:
        nums = [int(n) for n in bar_comments if n.isdigit() and int(n) < 5000]
        if nums and max(nums) > 5:
            return max(nums), "bar_comment"

    # 2. Check for pipe bar checks if frequent
    pipes = len(re.findall(r'\|', content))
    
    # 3. Detect time signature
    time_m = re.search(r'\\time\s+(\d+)\/(\d+)', content)
    if time_m:
        num = int(time_m.group(1))
        den = int(time_m.group(2))
        bar_len = Fraction(num, den)
    else:
        bar_len = Fraction(4, 4)

    # Let's count durations in the first main music section
    # Find note/rest duration tokens: e.g. 4, 8, 16, 2., 4.., etc.
    # Exclude version, staff-size, paper numbers
    music_part = content
    header_end = content.find(r'\score')
    if header_end != -1:
        music_part = content[header_end:]

    # Match tokens with duration: ([a-gA-GRs]|>)\s*('|,)*\s*(\d+)(\.*)
    # Also multi-measure rests: R2.*3, R1*4, etc.
    total_dur = Fraction(0, 1)
    curr_dur = Fraction(1, 4) # default duration in LilyPond if omitted

    # Tokenizer for LilyPond notes & rests
    # Matches: note/chord/rest with duration, or just duration
    # e.g., c4., <c e g>2, r8, R2.*4, s4
    tokens = re.finditer(r'(?:<[^>]+>|[a-grsR]|\\bar|\\times|\\tuplet)\s*(?:[\',!])*([0-9]+)(\.*)(?:\*([0-9]+(?:\/[0-9]+)?))?', music_part)
    
    # Or measure multi-measure rests:
    mm_rests = re.finditer(r'R(?:([0-9]+)(\.*))(?:\*([0-9]+))?', music_part)
    
    # Let's also check pipe checks
    staves = len(re.findall(r'\\context Staff|\\new Staff', content)) or 2
    if pipes > 10:
        est_by_pipes = round(pipes / staves)
        if est_by_pipes > 10:
            return est_by_pipes, "pipes"

    # Fallback to duration scan
    notes = re.findall(r'(?:[a-g]|>|r|s|R)(?:\'|,)*(\d+)(\.*)', music_part)
    if notes:
        tot = Fraction(0, 1)
        for d, dots in notes:
            val = Fraction(1, int(d))
            dot_val = val
            for _ in range(len(dots)):
                dot_val /= 2
                val += dot_val
            tot += val
        meas = round(float(tot / bar_len) / staves)
        if meas > 0:
            return meas, "duration"

    return 0, "unknown"

f = r'K:\MusicSearch\data\classical-corpora\mutopia-project\ftp\BeethovenLv\O10\LVB_Sonate_10no1_1\LVB_Sonate_10no1_1.ly'
with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
    c = fp.read()

m_count, method = parse_lilypond_measures(c)
print(f"Beethoven Op.10 No.1 1st mvt: measures = {m_count} (method: {method})")
