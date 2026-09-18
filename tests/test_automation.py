"""Offline shell workflow regression tests; no credentials or network calls."""
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
with open(os.environ['CALL_LOG'],'a') as f:
 f.write(name+' '+' '.join(args)+'\\n')
if name=='git':
 if args[:1]==['ls-remote']: print('abc123\\trefs/heads/automation/upstream-2.0.0')
 elif args[:2]==['rev-parse','HEAD:PKGBUILD']: print('old')
 elif args[:2]==['rev-parse','FETCH_HEAD:PKGBUILD']: print(os.environ.get('PACKAGE_BLOB','old'))
 elif args[:1]==['rev-parse']: print('identical')
 elif args[:1]==['clone']: Path(args[-1]).mkdir()
 elif args[:1]==['diff']: sys.exit(0 if '--cached' in args else 1)
elif name=='gh':
 if args[:2]==['pr','list']: print(os.environ.get('PR_STATE',''))
 elif args[:2]==['run','list']: print(os.environ.get('RUN_ID',''))
elif name=='ssh-keygen': print('256 SHA256:RFzBCUItH9LZS0cKB5UE6ceAYhBD5C8GeOBip8Z11+4 fake')
'''


class AutomationTests(unittest.TestCase):
    def run_script(self, script, **extra):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'maintenance').mkdir()
            shutil.copyfile(ROOT / 'maintenance' / script, root / 'maintenance' / script)
            (root / 'PKGBUILD').write_text('pkgver=2.0.0\npkgrel=1\n')
            (root / '.SRCINFO').write_text('metadata\n')
            (root / 'LICENSE').write_text('license\n')
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
            result = subprocess.run(['bash', str(root / 'maintenance' / script)], env=env, text=True, capture_output=True)
            return result, log.read_text()

    def test_existing_branch_without_pr_resumes(self):
        result, calls = self.run_script('update-pr.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('gh pr create ', calls)
        self.assertIn('gh workflow run ci.yml ', calls)
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

    def test_docs_only_commit_allows_publish(self):
        result, calls = self.run_script('publish-aur.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('git clone ssh://aur@aur.archlinux.org/', calls)

    def test_newer_package_blocks_stale_publish(self):
        result, calls = self.run_script('publish-aur.sh', PACKAGE_BLOB='new')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('git clone ', calls)
        self.assertIn('metadata advanced', result.stderr)
