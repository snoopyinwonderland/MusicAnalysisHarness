import subprocess
import os
import re

git_exe = r"C:\Users\snoop\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"
repo_dir = r"K:\MusicSearch\data\jazz-corpora\charlie-parker-50-solos"

res = subprocess.run([git_exe, "ls-tree", "-r", "-z", "HEAD"], cwd=repo_dir, capture_output=True)
entries = res.stdout.split(b"\x00")
extracted = 0
already = 0

for entry in entries:
    if not entry:
        continue
    parts = entry.split(b"\t", 1)
    if len(parts) < 2:
        continue
    meta, filepath_bytes = parts
    blob_hash = meta.split()[2].decode("ascii")
    filepath = filepath_bytes.decode("utf-8", errors="replace")
    
    norm = os.path.join(repo_dir, filepath.replace("/", os.sep))
    if os.path.exists(norm):
        already += 1
        continue
    
    subparts = filepath.split("/")
    sanitized = []
    for s in subparts:
        s = s.strip(". ")
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        s = s.replace("\u00a0", " ")
        if not s:
            s = "_"
        sanitized.append(s)
    
    target = os.path.join(repo_dir, *sanitized)
    if os.name == "nt" and not target.startswith("\\\\?\\"):
        abs_t = os.path.abspath(target)
        long_t = "\\\\?\\" + abs_t
    else:
        long_t = target
    
    os.makedirs(os.path.dirname(long_t), exist_ok=True)
    blob_res = subprocess.run([git_exe, "cat-file", "-p", blob_hash], cwd=repo_dir, capture_output=True)
    with open(long_t, "wb") as f:
        f.write(blob_res.stdout)
    extracted += 1

print(f"Already: {already}, Extracted: {extracted}, Total: {already + extracted}")
