import subprocess
import os
import re

git_exe = r"C:\Users\snoop\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"
ycacl_dir = r"K:\MusicSearch\data\classical-corpora\ycacl"

res = subprocess.run([git_exe, "ls-tree", "-r", "-z", "HEAD"], cwd=ycacl_dir, capture_output=True)
raw = res.stdout

entries = raw.split(b"\x00")
extracted = 0
already_present = 0

for entry in entries:
    if not entry:
        continue
    meta, filepath_bytes = entry.split(b"\t", 1)
    blob_hash = meta.split()[2].decode("ascii")
    filepath = filepath_bytes.decode("utf-8", errors="replace")
    
    # Normalize path check
    norm_path = os.path.join(ycacl_dir, filepath.replace("/", os.sep))
    if os.path.exists(norm_path):
        already_present += 1
        continue
    
    parts = filepath.split("/")
    sanitized_parts = []
    for part in parts:
        s = part.strip(". ")
        s = re.sub(r'[<>:"/\\|?*]', '_', s)
        s = s.replace("\u00a0", " ")
        if not s:
            s = "_"
        sanitized_parts.append(s)
    
    target_path = os.path.join(ycacl_dir, *sanitized_parts)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    blob_res = subprocess.run([git_exe, "cat-file", "-p", blob_hash], cwd=ycacl_dir, capture_output=True)
    with open(target_path, "wb") as f:
        f.write(blob_res.stdout)
    extracted += 1

print(f"Already present on Windows: {already_present}")
print(f"Extracted & sanitized: {extracted}")
print(f"Total pieces in YCACL now available: {already_present + extracted}")
