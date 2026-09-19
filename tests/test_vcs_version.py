"""Exercise the real pkgver() against evolving tagged Git history and pacman."""
from pathlib import Path
import subprocess
import tempfile
import unittest

RECIPE = Path(__file__).resolve().parents[1] / 'packages/fthr-clips-git/PKGBUILD'


class VcsVersionTests(unittest.TestCase):
    def test_tag_revision_and_prerelease_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / 'FTHR-Clips'
            checkout.mkdir()

            def git(*args):
                return subprocess.check_output(['git', *args], cwd=checkout,
                                               text=True, stderr=subprocess.PIPE).strip()

            def commit():
                git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    'commit', '--allow-empty', '-m', 'fixture')

            def version():
                return subprocess.check_output(
                    ['bash', '-c', 'source "$1"; pkgver', 'version-test', str(RECIPE)],
                    cwd=root, text=True).strip()

            def compare(left, right):
                return int(subprocess.check_output(['vercmp', left, right], text=True))

            git('init', '-b', 'linux')
            commit()
            git('tag', 'v1.1.0-alpha')
            first = version()
            self.assertEqual(first, '1.1.0alpha.r0.g' + git('rev-parse', '--short=7', 'HEAD'))
            commit()
            second = version()
            self.assertEqual(second, '1.1.0alpha.r1.g' + git('rev-parse', '--short=7', 'HEAD'))
            self.assertLess(compare(first, second), 0)
            self.assertGreater(compare(second, '1.1.0alpha-2'), 0)

            previous = second
            for tag, prefix in [('v1.1.0-alpha.2', '1.1.0alpha.2'),
                                ('v1.1.0-beta', '1.1.0beta'),
                                ('v1.1.0-rc1', '1.1.0rc1'),
                                ('v1.1.0', '1.1.0'),
                                ('v1.2.0-alpha', '1.2.0alpha')]:
                commit()
                git('tag', tag)
                current = version()
                self.assertTrue(current.startswith(prefix + '.r0.g'), current)
                self.assertLess(compare(previous, current), 0)
                previous = current
            for release in ('1.1.0alpha2', '1.1.0beta', '1.1.0rc1', '1.1.0'):
                self.assertLess(compare(second, release), 0)

    def test_unknown_tag_fails_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / 'FTHR-Clips'
            checkout.mkdir()
            for args in [('init', '-b', 'linux'),
                         ('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                          'commit', '--allow-empty', '-m', 'fixture'),
                         ('tag', 'v1.1.0-preview')]:
                subprocess.run(['git', *args], cwd=checkout, check=True, capture_output=True)
            result = subprocess.run(['bash', '-c', 'source "$1"; pkgver', 'version-test', str(RECIPE)],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unrecognized upstream release tag', result.stderr)
