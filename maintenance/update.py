#!/usr/bin/env python3
"""Review-gated upstream updater. Never execute downloaded AppImages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

REPO = 'FTHR-Community/FTHR-Clips'
API = f'https://api.github.com/repos/{REPO}/releases'
ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(alpha|beta|rc)(?:\.(0|[1-9][0-9]*))?)?\Z')


def version(value):
    if not isinstance(value, str) or not (m := VERSION.fullmatch(value)):
        raise ValueError(f'Unsupported release version: {value!r}; manual review required')
    major, minor, patch, stage, number = m.groups()
    normalized = f'{major}.{minor}.{patch}' + (stage + (number or '') if stage else '')
    key = (int(major), int(minor), int(patch), {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[stage], int(number) if number is not None else -1)
    return normalized, key


def select_release(releases, allow_prerelease):
    if not isinstance(releases, list):
        raise ValueError('Release API must return a list')
    candidates = []
    for release in releases:
        if not isinstance(release, dict) or not isinstance(release.get('assets'), list):
            raise ValueError('Malformed release metadata')
        if release.get('draft'):
            continue
        assets = release['assets']
        if any(not isinstance(a, dict) or not isinstance(a.get('name'), str) for a in assets):
            raise ValueError('Malformed asset metadata')
        images = [a for a in assets if a['name'].lower().endswith('.appimage') and 'x86_64' in a['name']]
        if not images:
            continue  # Windows-only and other-architecture releases do not advance this package.
        tag = release.get('tag_name')
        normalized, key = version(tag)
        if key[3] != 3 and not allow_prerelease:
            continue
        if release.get('prerelease') and not allow_prerelease:
            continue
        upstream = tag.removeprefix('v')
        name = f'FTHRClips-{upstream}-x86_64.AppImage'
        if len(images) != 1 or images[0]['name'] != name:
            raise ValueError(f'Ambiguous or renamed Linux artifact in {tag}')
        candidates.append((key, normalized, upstream, release, images[0]))
    if not candidates:
        raise ValueError('No suitable Linux release found')
    candidates.sort(key=lambda c: c[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ValueError('Ambiguous release versions')
    return candidates[0]


def asset_url(asset, tag):
    name = asset['name']
    if '/' in name or '\\' in name or name in ('.', '..'):
        raise ValueError('Unsafe asset name')
    expected = f'https://github.com/{REPO}/releases/download/{tag}/{name}'
    if asset.get('browser_download_url') != expected or asset.get('state') != 'uploaded':
        raise ValueError('Unexpected asset origin or incomplete upload')
    return expected


def digest_matches(asset, actual):
    digest = asset.get('digest')
    if digest is not None and digest != 'sha256:' + actual:
        raise ValueError('GitHub API digest mismatch or unsupported digest')


def checksum(text, name):
    match = re.fullmatch(r'([0-9a-fA-F]{64}) [ *]([^\r\n]+)\n?', text)
    if not match or match[2] != name:
        raise ValueError('Malformed checksum or unexpected checksum filename')
    return match[1].lower()


def fetch(url, destination=None):
    headers = {'User-Agent': 'fthr-clips-bin-maintenance', 'Accept': 'application/vnd.github+json'}
    if url.startswith('https://api.github.com/') and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
        if destination is None:
            data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError('Metadata exceeds size limit')
            return data
        hasher = hashlib.sha256()
        with destination.open('wb') as out:
            while block := response.read(1024 * 1024):
                hasher.update(block)
                out.write(block)
        return hasher.hexdigest()


def replace_field(text, field, value):
    result, count = re.subn(r'^' + re.escape(field) + r'=.*$', lambda _: field + '=' + value, text, flags=re.M)
    if count != 1:
        raise ValueError(f'Expected one literal {field} assignment')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Report candidate without downloading AppImage or changing files')
    parser.add_argument('--allow-prerelease', action='store_true', help='Explicitly track alpha/beta/rc releases')
    args = parser.parse_args()
    releases = []
    for page in range(1, 101):
        batch = json.loads(fetch(f'{API}?per_page=100&page={page}'))
        if not isinstance(batch, list):
            raise ValueError('Malformed release list')
        releases.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError('Release pagination limit reached')
    _, pkgver, upstream, release, artifact = select_release(releases, args.allow_prerelease)
    tag = release['tag_name']
    # PKGBUILD deliberately uses v-prefixed upstream tags.
    if tag != 'v' + upstream:
        raise ValueError('Changed upstream tag convention requires manual review')
    sums = [a for a in release['assets'] if a['name'] == artifact['name'] + '.sha256']
    if len(sums) != 1:
        raise ValueError('Newest suitable release must provide exactly one adjacent .sha256 asset')
    url = asset_url(artifact, tag)
    sum_data = fetch(asset_url(sums[0], tag))
    digest_matches(sums[0], hashlib.sha256(sum_data).hexdigest())
    expected = checksum(sum_data.decode('ascii'), artifact['name'])
    digest_matches(artifact, expected)
    path = ROOT / 'PKGBUILD'
    original = path.read_text()
    current = re.findall(r'^pkgver=([0-9a-z.]+)$', original, re.M)
    if len(current) != 1:
        raise ValueError('Expected one literal pkgver')
    comparison = int(subprocess.check_output(['vercmp', pkgver, current[0]], text=True).strip())
    print(f'Latest suitable release: {tag}; Arch version: {pkgver}; SHA-256: {expected}')
    if comparison <= 0:
        if comparison == 0 and f"sha256sums=('{expected}')" not in original:
            raise ValueError('Published artifact checksum changed without version bump; manual review required')
        print('No newer Arch version; no files changed.')
        return
    if args.check:
        print('Update available; rerun without --check to download, verify, build, and update metadata.')
        return
    if os.geteuid() == 0:
        raise ValueError('Run updater as an unprivileged user (makepkg refuses root)')
    srcinfo = ROOT / '.SRCINFO'
    old_info = srcinfo.read_bytes() if srcinfo.exists() else None
    with tempfile.TemporaryDirectory(prefix='fthr-update-') as temporary:
        source = Path(temporary) / artifact['name']
        if fetch(url, source) != expected:
            raise ValueError('Downloaded AppImage checksum mismatch')
        changed = original
        for field, value in [('pkgver', pkgver), ('pkgrel', '1'), ('_upstream_version', upstream), ('sha256sums', f"('{expected}')")]:
            changed = replace_field(changed, field, value)
        try:
            path.write_text(changed)
            info = subprocess.check_output(['makepkg', '--printsrcinfo'], cwd=ROOT)
            srcinfo.write_bytes(info)
            env = dict(os.environ, SRCDEST=temporary)
            subprocess.run(['bash', 'maintenance/validate.sh'], cwd=ROOT, env=env, check=True)
        except BaseException:
            path.write_text(original)
            if old_info is None:
                srcinfo.unlink(missing_ok=True)
            else:
                srcinfo.write_bytes(old_info)
            raise
    print(f'Updated PKGBUILD and .SRCINFO to {pkgver}-1; source and package checks passed. Review and runtime smoke-test before merging.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Update failed: {error}')
