"""Monorepo metadata, source integrity, and workflow contract checks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('fthr-clips-bin', 'fthr-clips-git')
spec = importlib.util.spec_from_file_location('check_sources', ROOT / 'maintenance/check-sources.py')
source_policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_policy)


def fields(text):
    result = {}
    for line in text.splitlines():
        if ' = ' in line:
            key, value = line.strip().split(' = ', 1)
            result.setdefault(key, []).append(value)
    return result


class PackageTests(unittest.TestCase):
    def test_package_metadata_and_syntax(self):
        for package in PACKAGES:
            with self.subTest(package=package):
                recipe = ROOT / 'packages' / package
                subprocess.run(['bash', '-n', str(recipe / 'PKGBUILD')], check=True)
                info = (recipe / '.SRCINFO').read_text()
                data = fields(info)
                self.assertEqual(data['pkgbase'], [package])
                self.assertEqual(data['pkgname'], [package])
                self.assertEqual(data['provides'], ['fthr-clips=' + data['pkgver'][0]])
                self.assertIn('fthr-clips', data['conflicts'])
                self.assertNotIn('replaces', data)
                source_policy.check(info)
                if shutil.which('makepkg'):
                    generated = subprocess.check_output(['makepkg', '--printsrcinfo'], cwd=recipe, text=True)
                    self.assertEqual(info, generated)

    def test_git_tracks_only_linux_and_local_sources_are_hashed(self):
        recipe = ROOT / 'packages/fthr-clips-git'
        data = fields((recipe / '.SRCINFO').read_text())
        vcs = []
        local = []
        for key, sources in data.items():
            if key != 'source' and not key.startswith('source_'):
                continue
            hashes = data['sha256sums' + key.removeprefix('source')]
            for source, checksum in zip(sources, hashes):
                origin = source.split('::', 1)[-1]
                if origin.startswith('git+'):
                    vcs.append(origin)
                elif '://' not in origin:
                    local.append(origin)
                    self.assertEqual(hashlib.sha256((recipe / origin).read_bytes()).hexdigest(), checksum)
        self.assertEqual(vcs, ['git+https://github.com/FTHR-Community/FTHR-Clips.git#branch=linux'])
        self.assertTrue(local, 'The Git package must ship a reviewed launcher')
        self.assertFalse(any('AppImage' in value for key, values in data.items() if key == 'source' or key.startswith('source_') for value in values))

    def test_changed_upstream_ffmpeg_pin_fails_before_replacing_existing_files(self):
        helper = ROOT / 'packages/fthr-clips-git/prepare-ffmpeg.py'
        for mismatch in ('asset', 'sha256'):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'tools').mkdir()
                archive = root / 'ffmpeg.tar.xz'
                archive.write_bytes(b'checksum fixture; extraction must never happen')
                source = {'asset': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
                source[mismatch] = 'changed-upstream-pin'
                (root / 'tools/ffmpeg_manifest_linux.json').write_text(json.dumps({'source': source}))
                destination = root / 'FTHRcapture_linux/third_party/ffmpeg'
                destination.mkdir(parents=True)
                sentinel = destination / 'existing-library'
                sentinel.write_text('preserve')
                result = subprocess.run(['python', str(helper), str(root), str(archive)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Upstream FFmpeg pin changed', result.stderr)
                self.assertEqual(sentinel.read_text(), 'preserve')

    def test_skip_policy_rejects_unchecked_assets_and_other_branches(self):
        prefix = 'pkgbase = fthr-clips-git\nsource = '
        allowed = 'git+https://github.com/FTHR-Community/FTHR-Clips.git#branch=linux'
        source_policy.check(prefix + allowed + '\nsha256sums = SKIP\n')
        for source in ['fthr-clips', 'https://example.com/archive.tar.gz', allowed.replace('linux', 'main'), allowed.replace('linux', 'master')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                source_policy.check(prefix + source + '\nsha256sums = SKIP\n')
        with self.assertRaises(ValueError):
            source_policy.check('pkgbase = fthr-clips-bin\nsource = '+allowed+'\nsha256sums = SKIP\n')
        with self.assertRaises(ValueError):
            source_policy.check(prefix + allowed + '\n')

    def test_workflows_keep_actions_pinned_and_deploy_main_only(self):
        workflows = ROOT / '.github/workflows'
        for path in workflows.glob('*.yml'):
            text = path.read_text()
            for action in re.findall(r'^\s*- uses: (.+)$', text, re.M):
                if not action.startswith('./.github/workflows/'):
                    self.assertRegex(action, r'^[\w/-]+@[0-9a-f]{40}(?:\s+#.*)?$')
        ci = (workflows / 'ci.yml').read_text()
        publish = (workflows / 'publish-aur.yml').read_text()
        for package in PACKAGES:
            self.assertIn('package: ' + package, ci)
            self.assertIn('package: ' + package, publish)
        self.assertIn("paths: ['packages/**']", publish)
        self.assertIn('uses: ./.github/workflows/publish-package.yml', publish)
        reusable = (workflows / 'publish-package.yml').read_text()
        self.assertEqual(reusable.count("if: github.ref == 'refs/heads/main'"), 2)
        self.assertIn('needs: validate', reusable)
        self.assertIn('secrets.AUR_SSH_PRIVATE_KEY', publish)
        self.assertNotIn('secrets.AUR_SSH_PRIVATE_KEY', ci)
        daily = (workflows / 'git-build.yml').read_text()
        self.assertIn("vars.ENABLE_DAILY_GIT_BUILD == 'true'", daily)
        self.assertIn('contents: read', daily)
        for forbidden in ('git commit', 'git push', 'publish-aur', 'contents: write', 'AUR_SSH_PRIVATE_KEY'):
            self.assertNotIn(forbidden, daily)

    def test_native_ci_installs_declared_official_dependencies(self):
        data = fields((ROOT / 'packages/fthr-clips-git/.SRCINFO').read_text())
        required = set(data.get('depends', []) + data.get('makedepends', []) + data.get('checkdepends', []))
        required.discard('python-keyboard')  # Built from pinned AUR recipe by bootstrap helper.
        for name in ('ci.yml', 'publish-aur.yml', 'git-build.yml'):
            text = (ROOT / '.github/workflows' / name).read_text()
            if name == 'git-build.yml':
                tool_lines = re.findall(r'run: pacman -Syu --noconfirm --needed (.+)', text)
            else:
                tool_lines = re.findall(r'package: fthr-clips-git\n\s+tools: (.+)', text)
            self.assertEqual(len(tool_lines), 1, name)
            installed = set(tool_lines[0].split())
            self.assertFalse(required - installed, f'{name}: missing {required - installed}')

    def test_updater_only_targets_binary_recipe(self):
        spec = importlib.util.spec_from_file_location('package_update', ROOT / 'maintenance/update.py')
        updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(updater)
        self.assertEqual(updater.PACKAGE, ROOT / 'packages/fthr-clips-bin')
        proposal = (ROOT / 'maintenance/update-pr.sh').read_text()
        self.assertIn('packages/fthr-clips-bin/PKGBUILD packages/fthr-clips-bin/.SRCINFO', proposal)
        self.assertNotIn('packages/fthr-clips-git', proposal)

    def test_ci_aur_bootstrap_is_pinned_and_unprivileged(self):
        helper = (ROOT / 'maintenance/bootstrap-git-deps.sh').read_text()
        self.assertRegex(helper, r'(?m)^pin=[0-9a-f]{40}$')
        self.assertIn('checkout --detach "$pin"', helper)
        self.assertIn('runuser -u builder -- makepkg --verifysource', helper)
        self.assertIn('runuser -u builder -- makepkg --cleanbuild', helper)
        self.assertNotIn('makepkg --skipchecksums', helper)
