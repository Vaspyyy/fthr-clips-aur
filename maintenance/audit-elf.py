#!/usr/bin/env python3
"""Review new unbundled ELF dependencies without executing release binaries."""
from pathlib import Path
import re
import subprocess
import sys

ALLOWED = {
    'ld-linux-x86-64.so.2': 'glibc', 'libc.so.6': 'glibc',
    'libdl.so.2': 'glibc', 'libm.so.6': 'glibc', 'libmvec.so.1': 'glibc',
    'libpthread.so.0': 'glibc', 'libresolv.so.2': 'glibc', 'librt.so.1': 'glibc',
    'libGL.so.1': 'libglvnd', 'libEGL.so.1': 'libglvnd',
    'libdrm.so.2': 'libdrm', 'libxcb.so.1': 'libxcb',
    'libwayland-client.so.0': 'wayland', 'libwayland-cursor.so.0': 'wayland',
    'libwayland-egl.so.1': 'wayland', 'libz.so.1': 'zlib',
}
root = Path(sys.argv[1]).resolve()
if not (root / 'FTHRClips').is_file():
    raise SystemExit('Missing packaged executable')
provided = {p.name for p in root.rglob('*') if p.is_file()}
external = set()
count = 0
for p in root.rglob('*'):
    if not p.is_file() or p.is_symlink():
        continue
    with p.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            continue
    count += 1
    result = subprocess.run(['readelf', '-d', str(p)], check=True, text=True, capture_output=True)
    for needed in re.findall(r'\(NEEDED\).*?\[(.*?)\]', result.stdout):
        # The PyInstaller bootloader does not add _internal until it loads Python.
        if needed not in provided or p == root / 'FTHRClips':
            external.add(needed)
unknown = external - ALLOWED.keys()
if unknown:
    raise SystemExit('New external libraries require review: ' + ', '.join(sorted(unknown)))
print(f'Audited {count} ELF files; unbundled libraries:')
for name in sorted(external):
    print(f'  {name}: {ALLOWED[name]}')
print('This static closure check does not replace graphical runtime testing.')
