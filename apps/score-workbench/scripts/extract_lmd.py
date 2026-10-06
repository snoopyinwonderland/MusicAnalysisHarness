import tarfile
import os
import re
import time

tar_path = r"K:\MusicSearch\data\global-pop-midi\clean_midi.tar.gz"
dest_dir = r"K:\MusicSearch\data\global-pop-midi\clean_midi"
os.makedirs(dest_dir, exist_ok=True)

print(f"Extracting {tar_path}...")
t0 = time.time()
extracted = 0

with tarfile.open(tar_path, "r:gz") as tar:
    for member in tar.getmembers():
        if member.isdir():
            continue
        
        # Sanitize path for Windows
        rel_path = member.name
        # clean_midi usually starts with clean_midi/...
        parts = rel_path.split("/")
        sanitized_parts = []
        for p in parts:
            p = p.strip(". ")
            p = re.sub(r'[<>:"/\\|?*]', '_', p)
            if not p:
                p = "_"
            sanitized_parts.append(p)
        
        target = os.path.join(dest_dir, *sanitized_parts)
        if os.name == "nt" and not target.startswith("\\\\?\\"):
            abs_t = os.path.abspath(target)
            long_t = "\\\\?\\" + abs_t
        else:
            long_t = target
        
        os.makedirs(os.path.dirname(long_t), exist_ok=True)
        f_in = tar.extractfile(member)
        if f_in:
            with open(long_t, "wb") as f_out:
                f_out.write(f_in.read())
            extracted += 1
            if extracted % 2000 == 0:
                print(f"Extracted {extracted:,} files...")

print(f"Done in {time.time()-t0:.2f}s! Total files extracted: {extracted:,}")
