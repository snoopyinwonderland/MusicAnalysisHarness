import subprocess
import os
import re

git_exe = r"C:\Users\snoop\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"
choco_dir = r"K:\MusicSearch\data\classical-corpora\choco"

res = subprocess.run([git_exe, "ls-tree", "-r", "-z", "HEAD"], cwd=choco_dir, capture_output=True)
raw = res.stdout

entries = raw.split(b"\x00")
extracted = 0
already_present = 0

for entry in entries:
    if not entry:
        continue
    parts = entry.split(b"\t", 1)
    if len(parts) < 2:
        continue
    meta, filepath_bytes = parts
    blob_hash = meta.split()[2].decode("ascii")
    filepath = filepath_bytes.decode("utf-8", errors="replace")
    
    norm_path = os.path.join(choco_dir, filepath.replace("/", os.sep))
    if os.path.exists(norm_path):
        already_present += 1
        continue
    
    subparts = filepath.split("/")
    sanitized_parts = []
    for part in subparts:
        s = part.strip(". ")
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        s = s.replace("\u00a0", " ")
        if not s:
            s = "_"
        sanitized_parts.append(s)
    
    target_path = os.path.join(choco_dir, *sanitized_parts)
    if os.name == 'nt' and not target_path.startswith('\\\\?\\'):
        abs_target = os.path.abspath(target_path)
        long_target = '\\\\?\\' + abs_target
    else:
        long_target = target_path

    os.makedirs(os.path.dirname(long_target), exist_ok=True)
    
    blob_res = subprocess.run([git_exe, "cat-file", "-p", blob_hash], cwd=choco_dir, capture_output=True)
    with open(long_target, "wb") as f:
        f.write(blob_res.stdout)
    extracted += 1

print(f"Already present on Windows: {already_present}")
print(f"Extracted & sanitized: {extracted}")
print(f"Total files in ChoCo now available: {already_present + extracted}")
