import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest
import tempfile
from unittest.mock import patch
import json

spec = importlib.util.spec_from_file_location('update', Path(__file__).resolve().parents[1] / 'maintenance/update.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def release(tag='v1.1.0-alpha', names=None):
    if names is None:
        names = [f'FTHRClips-{tag[1:]}-x86_64.AppImage']
    return dict(tag_name=tag, draft=False, prerelease='-' in tag,
                assets=[dict(name=n, state='uploaded', browser_download_url=f'https://github.com/{u.REPO}/releases/download/{tag}/{n}') for n in names])


class UpdaterTests(unittest.TestCase):
    def test_versions(self):
        tags = ['v1.1.0-alpha', 'v1.1.0-alpha.0', 'v1.1.0-alpha.2', 'v1.1.0-alpha.10', 'v1.1.0-beta', 'v1.1.0-rc.1', 'v1.1.0', 'v1.2.0']
        self.assertEqual(tags, sorted(reversed(tags), key=lambda t: u.version(t)[1]))
        self.assertEqual(u.version(tags[0])[0], '1.1.0alpha')
        if shutil.which('vercmp'):
            for a, b in zip(tags, tags[1:]):
                self.assertLess(int(subprocess.check_output(['vercmp', u.version(a)[0], u.version(b)[0]])), 0)

    def test_invalid_versions(self):
        for tag in ['v01.2.3', 'v1.0.0-alpha.01', 'v1.0.0-unknown', 'v1.0.0+build', '../../a', 'v1.0.0\n', None]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                u.version(tag)

    def test_windows_newer_ignored_and_order_by_version(self):
        data = [release('v9.0.0', ['setup.exe']), release('v1.1.0-alpha'), release('v1.0.0')]
        self.assertEqual(u.select_release(data, True)[2], '1.1.0-alpha')
        self.assertEqual(u.select_release(data, False)[2], '1.0.0')

    def test_ambiguity(self):
        for data in [[release(), release()], [release(names=['one-x86_64.AppImage', 'two-x86_64.AppImage'])], [release(names=['renamed-x86_64.AppImage'])], {}, [{'assets': None}]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                u.select_release(data, True)

    def test_checksum(self):
        sha = 'a' * 64
        self.assertEqual(u.checksum(sha + '  file.AppImage\n', 'file.AppImage'), sha)
        for text in [sha + '  ../file.AppImage', sha + '  file.AppImage\nextra', 'SKIP  file.AppImage', sha + '  /file.AppImage']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                u.checksum(text, 'file.AppImage')

    def test_origin_and_path(self):
        asset = release()['assets'][0]
        self.assertTrue(u.asset_url(asset, 'v1.1.0-alpha').startswith('https://github.com/'))
        for override in [{'name': '../evil'}, {'name': 'x\\evil'}, {'browser_download_url': 'https://evil.test/file'}, {'state': 'new'}]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                u.asset_url(dict(asset, **override), 'v1.1.0-alpha')

    def test_digest(self):
        u.digest_matches({}, 'a' * 64)
        u.digest_matches({'digest': 'sha256:' + 'a' * 64}, 'a' * 64)
        with self.assertRaises(ValueError):
            u.digest_matches({'digest': 'sha256:' + 'b' * 64}, 'a' * 64)

    def test_failed_validation_rolls_back_metadata(self):
        data = release('v2.0.0')
        artifact = data['assets'][0]
        sum_asset = dict(artifact, name=artifact['name'] + '.sha256',
                         browser_download_url=artifact['browser_download_url'] + '.sha256')
        data['assets'].append(sum_asset)
        digest = 'a' * 64
        def fake_fetch(url, destination=None):
            if destination is not None:
                destination.write_bytes(b'unexecuted fixture')
                return digest
            if '/releases?' in url:
                return json.dumps([data]).encode()
            return (digest + '  ' + artifact['name'] + '\n').encode()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = "pkgver=1.0.0\npkgrel=2\n_upstream_version=1.0.0\nsha256sums=('old')\n"
            (root / 'PKGBUILD').write_text(original)
            (root / '.SRCINFO').write_bytes(b'original srcinfo')
            with patch.object(u, 'ROOT', root), patch.object(u, 'fetch', side_effect=fake_fetch), patch.object(u.os, 'geteuid', return_value=1000), patch('sys.argv', ['update.py']), patch.object(u.subprocess, 'check_output', side_effect=['1', b'new srcinfo']), patch.object(u.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'validate')):
                with self.assertRaises(subprocess.CalledProcessError):
                    u.main()
            self.assertEqual((root / 'PKGBUILD').read_text(), original)
            self.assertEqual((root / '.SRCINFO').read_bytes(), b'original srcinfo')

    def test_exact_replacement(self):
        self.assertEqual(u.replace_field('pkgver=1\npkgrel=1\n', 'pkgver', '2'), 'pkgver=2\npkgrel=1\n')
        for text in ['', 'pkgver=1\npkgver=2']:
            with self.assertRaises(ValueError):
                u.replace_field(text, 'pkgver', '3')


if __name__ == '__main__':
    unittest.main()
