#!/usr/bin/env python3
"""Check native package layout and ELF metadata without launching the application."""
from pathlib import Path
import re
import stat
import subprocess
import sys

ALLOWED = {
    'ld-linux-x86-64.so.2': 'glibc', 'libc.so.6': 'glibc',
    'libdl.so.2': 'glibc', 'libm.so.6': 'glibc', 'libmvec.so.1': 'glibc',
    'libpthread.so.0': 'glibc', 'libresolv.so.2': 'glibc', 'librt.so.1': 'glibc',
    'libgcc_s.so.1': 'gcc-libs', 'libstdc++.so.6': 'gcc-libs',
    'libpulse.so.0': 'libpulse', 'libpulse-simple.so.0': 'libpulse',
    'libwayland-client.so.0': 'wayland', 'libwayland-cursor.so.0': 'wayland',
    'libwayland-egl.so.1': 'wayland',
}


def audit(package):
    package = package.resolve()
    root = package / 'usr/lib/fthr-clips'
    native = root / 'FTHRcapture_linux/build'
    for relative in (
        'usr/bin/fthr-clips', 'usr/lib/fthr-clips/FTHR_UI/main.py',
        'usr/lib/fthr-clips/FTHRcapture_linux/build/FTHRclips',
        'usr/lib/fthr-clips/FTHRcapture_linux/build/libFTHRPlaybackMixer.so',
        'usr/lib/fthr-clips/FTHRcapture_linux/third_party/ffmpeg/bin/ffmpeg',
        'usr/lib/fthr-clips/FTHRcapture_linux/third_party/ffmpeg/bin/ffprobe',
        'usr/lib/fthr-clips/plugin-packages/FTHR-Uploader-linux.fthrplugin',
        'usr/share/applications/fthr-clips.desktop',
        'usr/share/icons/hicolor/512x512/apps/fthr-clips.png',
        'usr/share/licenses/fthr-clips-git/LICENSE',
        'usr/share/doc/fthr-clips-git/ffmpeg_manifest_linux.json',
    ):
        if not (package / relative).is_file():
            raise ValueError(f'Missing package file: {relative}')
    for path in package.rglob('*'):
        mode = path.lstat().st_mode
        if mode & 0o6000 or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            raise ValueError(f'Unsafe package file or permissions: {path}')
        if path.is_symlink() and (not path.exists() or not path.resolve().is_relative_to(package)):
            raise ValueError(f'Broken or escaping package symlink: {path}')
    if not (package / 'usr/bin/fthr-clips').stat().st_mode & stat.S_IXUSR:
        raise ValueError('Launcher is not executable')
    provided = {p.name for p in root.rglob('*') if p.is_file()}
    external = set()
    count = 0
    for path in root.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        count += 1
        dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
        external.update(name for name in re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic) if name not in provided)
        paths = re.findall(r'\((?:RPATH|RUNPATH)\).*?\[(.*?)\]', dynamic)
        for entry in (entry for value in paths for entry in value.split(':')):
            expanded = entry.replace('${ORIGIN}', str(path.parent)).replace('$ORIGIN', str(path.parent))
            if not entry.startswith(('$ORIGIN', '${ORIGIN}')) or not Path(expanded).resolve().is_relative_to(root):
                raise ValueError(f'Unexpected ELF search path in {path.name}: {entry}')
        if path.parent == native:
            rpath = re.findall(r'\(RPATH\).*?\[(.*?)\]', dynamic)
            if not any('$ORIGIN/../third_party/ffmpeg/lib' in value.split(':') for value in rpath):
                raise ValueError(f'{path.name} lacks inherited private FFmpeg RPATH')
    if count < 4:
        raise ValueError('Expected the native engine, mixer, FFmpeg and FFprobe ELF binaries')
    unknown = external - ALLOWED.keys()
    if unknown:
        raise ValueError('New external libraries require review: ' + ', '.join(sorted(unknown)))
    print(f'Audited {count} native ELF files; unbundled libraries:')
    for name in sorted(external):
        print(f'  {name}: {ALLOWED[name]}')
    print('Static layout/ELF checks passed; graphical runtime remains a separate smoke test.')


if __name__ == '__main__':
    try:
        audit(Path(sys.argv[1]))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
