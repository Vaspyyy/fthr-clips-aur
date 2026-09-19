"""Exercise archive selection with pacman metadata and phantom debug outputs."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUB = '''#!/usr/bin/python3
import os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
if name=='runuser':
 print(os.environ['PACKAGE_LIST'])
elif name=='pacman':
 if args[0]=='-Qpq': print(Path(args[-1]).read_text())
 elif args[0]=='-U': Path(os.environ['INSTALL_LOG']).write_text(args[-1])
 else: raise SystemExit('Unexpected pacman call')
'''


class BootstrapTests(unittest.TestCase):
    def select(self, fixture_names, expected=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bindir = root / 'bin'
            bindir.mkdir()
            for name in ('pacman', 'runuser'):
                tool = bindir / name
                tool.write_text(STUB)
                tool.chmod(0o755)
            archives = []
            for filename, package_name in fixture_names:
                archive = root / filename
                archives.append(str(archive))
                if package_name is not None:
                    archive.write_text(package_name)
            log = root / 'installed'
            env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'],
                       PACKAGE_LIST='\n'.join(archives), INSTALL_LOG=str(log))
            result = subprocess.run(['bash', '-c', 'source "$1"; install_keyboard_archive',
                                     'test-bootstrap', str(ROOT / 'maintenance/bootstrap-git-deps.sh')],
                                    env=env, capture_output=True, text=True)
            if expected is None:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('exactly one existing python-keyboard', result.stderr)
                self.assertFalse(log.exists())
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(log.read_text(), str(root / expected))

    def test_missing_debug_archive_does_not_block_runtime_package(self):
        self.select([('runtime.pkg.tar.zst', 'python-keyboard'), ('debug.pkg.tar.zst', None)],
                    'runtime.pkg.tar.zst')

    def test_existing_debug_package_is_not_installed(self):
        self.select([('debug.pkg.tar.zst', 'python-keyboard-debug'), ('runtime.pkg.tar.zst', 'python-keyboard')],
                    'runtime.pkg.tar.zst')

    def test_no_matching_package_is_rejected(self):
        self.select([('python-keyboard.pkg.tar.zst', 'unexpected-package'), ('debug.pkg.tar.zst', None)])

    def test_multiple_matching_packages_are_rejected(self):
        self.select([('one.pkg.tar.zst', 'python-keyboard'), ('two.pkg.tar.zst', 'python-keyboard')])
