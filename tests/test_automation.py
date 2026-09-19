"""Offline shell workflow regression tests; no credentials or network calls."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUB = '''#!/usr/bin/python3
import io,os,sys,tarfile
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
with open(os.environ['CALL_LOG'],'a') as f:
 f.write(name+' '+' '.join(args)+'\\n')
if name=='git':
 if args[:1]==['ls-remote']: print('abc123\\trefs/heads/automation/upstream-2.0.0')
 elif args[:1]==['rev-parse']:
  print(os.environ.get('PACKAGE_BLOB','old') if args[1].startswith('FETCH_HEAD:packages/') else 'old')
 elif args[:1]==['archive']:
  recipe=Path(args[1].split(':',1)[1])
  with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as archive:
   for file in recipe.iterdir(): archive.add(file,arcname=file.name)
 elif args[:1]==['clone']:
  target=Path(args[-1]); target.mkdir(); (target/'stale.patch').write_text('obsolete')
  (target/'.git').mkdir()
 elif args[:1]==['ls-files']: sys.stdout.write('stale.patch\\0')
 elif args[:1]==['add']:
  with open(os.environ['CALL_LOG'],'a') as f:
   f.write('staged-files '+','.join(sorted(p.name for p in Path('.').iterdir()))+'\\n')
 elif args[:1]==['diff']: sys.exit(int(os.environ.get('AUR_CHANGED','0')) if '--cached' in args else 1)
elif name=='gh':
 if args[:2]==['pr','list']: print(os.environ.get('PR_STATE',''))
 elif args[:2]==['run','list']: print(os.environ.get('RUN_ID',''))
elif name=='ssh-keygen': print('256 SHA256:RFzBCUItH9LZS0cKB5UE6ceAYhBD5C8GeOBip8Z11+4 fake')
'''


class AutomationTests(unittest.TestCase):
    def run_script(self, script, package=None, **extra):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'maintenance').mkdir()
            shutil.copyfile(ROOT / 'maintenance' / script, root / 'maintenance' / script)
            for name in ('fthr-clips-bin', 'fthr-clips-git'):
                recipe = root / 'packages' / name
                recipe.mkdir(parents=True)
                (recipe / 'PKGBUILD').write_text('pkgver=2.0.0\npkgrel=1\n')
                (recipe / '.SRCINFO').write_text('metadata\n')
                (recipe / 'LICENSE').write_text('license\n')
                if name.endswith('-git'):
                    (recipe / 'fthr-clips').write_text('launcher\n')
            bindir = root / 'bin'
            bindir.mkdir()
            for name in ('git', 'gh', 'python', 'ssh-keygen'):
                target = bindir / name
                target.write_text(STUB)
                target.chmod(0o755)
            log = root / 'calls'
            env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'], CALL_LOG=str(log),
                       GITHUB_ACTIONS='true', GITHUB_REF='refs/heads/main', AUR_SSH_PRIVATE_KEY='offline-fixture')
            env.update(extra)
            command = ['bash', str(root / 'maintenance' / script)]
            if package is not None:
                command.append(package)
            result = subprocess.run(command, env=env, text=True, capture_output=True)
            return result, log.read_text() if log.exists() else ''

    def test_existing_branch_without_pr_resumes(self):
        result, calls = self.run_script('update-pr.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('gh pr create ', calls)
        self.assertIn('gh workflow run ci.yml ', calls)
        self.assertIn('packages/fthr-clips-bin/PKGBUILD packages/fthr-clips-bin/.SRCINFO', calls)
        self.assertNotIn('git push ', calls)

    def test_open_pr_without_ci_resumes(self):
        result, calls = self.run_script('update-pr.sh', PR_STATE='OPEN')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('gh pr create ', calls)
        self.assertIn('gh workflow run ci.yml ', calls)

    def test_existing_ci_and_closed_pr_are_preserved(self):
        for state, run in [('OPEN', '123'), ('CLOSED', ''), ('MERGED', '')]:
            result, calls = self.run_script('update-pr.sh', PR_STATE=state, RUN_ID=run)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('gh pr create ', calls)
            self.assertNotIn('gh workflow run ', calls)
            self.assertNotIn('git push ', calls)

    def test_docs_only_commit_allows_publish_but_unchanged_aur_has_no_push(self):
        for package in ('fthr-clips-bin', 'fthr-clips-git'):
            result, calls = self.run_script('publish-aur.sh', package)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f'git clone ssh://aur@aur.archlinux.org/{package}.git', calls)
            self.assertIn(f'git archive HEAD:packages/{package}', calls)
            self.assertNotIn('git push ', calls)

    def test_changed_recipe_syncs_assets_removes_stale_files_and_pushes_master(self):
        result, calls = self.run_script('publish-aur.sh', 'fthr-clips-git', AUR_CHANGED='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('staged-files .SRCINFO,.git,LICENSE,PKGBUILD,fthr-clips', calls)
        self.assertIn('git push origin HEAD:master', calls)
        self.assertNotIn('force', calls)

    def test_newer_package_blocks_stale_publish(self):
        for package in ('fthr-clips-bin', 'fthr-clips-git'):
            result, calls = self.run_script('publish-aur.sh', package, PACKAGE_BLOB='new')
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('git clone ', calls)
            self.assertIn('metadata advanced', result.stderr)

    def test_untrusted_branch_and_invalid_package_rejected(self):
        for package, ref in [('fthr-clips-git', 'refs/heads/untrusted'), ('../escape', 'refs/heads/main')]:
            result, calls = self.run_script('publish-aur.sh', package, GITHUB_REF=ref)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('git clone ', calls)
