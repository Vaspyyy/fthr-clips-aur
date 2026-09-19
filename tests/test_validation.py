"""Exercise the moving-version build boundary without building upstream code."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUB = '''#!/usr/bin/python3
import os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
if name=='python':
 if args[0]=='-':
  sys.argv=['-']+args[1:]
  exec(sys.stdin.read())
elif name=='makepkg':
 if '--printsrcinfo' in args: print(Path('.SRCINFO').read_text(),end='')
 elif '--cleanbuild' in args:
  Path('PKGBUILD').write_text('pkgver=2.r99.gabcdef0\\n')
  Path('fixture.pkg.tar.zst').write_bytes(b'fixture')
  Path(os.environ['BUILD_LOG']).write_text(str(Path.cwd()))
 elif '--packagelist' in args: print(Path('fixture.pkg.tar.zst').resolve())
'''


class ValidationTests(unittest.TestCase):
    @unittest.skipIf(os.geteuid() == 0, 'makepkg validation deliberately rejects root')
    def test_vcs_build_does_not_rewrite_reviewed_recipe_or_srcinfo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            maintenance = root / 'maintenance'
            maintenance.mkdir()
            shutil.copyfile(ROOT / 'maintenance/validate.sh', maintenance / 'validate.sh')
            recipe = root / 'packages/fthr-clips-git'
            recipe.mkdir(parents=True)
            original = 'pkgver=1.r1.g1234567\n'
            (recipe / 'PKGBUILD').write_text(original)
            (recipe / '.SRCINFO').write_text('pkgver = 1.r1.g1234567\n')
            bindir = root / 'bin'
            bindir.mkdir()
            for name in ('python', 'makepkg', 'namcap', 'bsdtar', 'desktop-file-validate'):
                tool = bindir / name
                tool.write_text(STUB)
                tool.chmod(0o755)
            log = root / 'build-log'
            env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'], BUILD_LOG=str(log))
            result = subprocess.run(['bash', str(maintenance / 'validate.sh'), 'fthr-clips-git'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((recipe / 'PKGBUILD').read_text(), original)
            self.assertEqual((recipe / '.SRCINFO').read_text(), 'pkgver = 1.r1.g1234567\n')
            self.assertNotEqual(Path(log.read_text()), recipe)
            self.assertFalse(Path(log.read_text()).exists(), 'Disposable VCS build should be cleaned up')
