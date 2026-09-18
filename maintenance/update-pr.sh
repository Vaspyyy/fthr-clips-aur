#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Token is used for this repository only; never publish to AUR from this job.
python maintenance/update.py --allow-prerelease
if git diff --quiet -- PKGBUILD .SRCINFO; then
  exit 0
fi
version=$(sed -n 's/^pkgver=//p' PKGBUILD)
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-z]+[0-9]*)?$ ]]
branch="automation/upstream-$version"
# A previously proposed version stays under reviewer control, even if closed.
if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  echo "Update branch $branch already exists; leaving it unchanged."
  exit 0
fi
git switch -c "$branch"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add PKGBUILD .SRCINFO
git commit -m "Update fthr-clips-bin to $version"
gh auth setup-git
git push origin "HEAD:refs/heads/$branch"
body=$(mktemp)
trap 'rm -f "$body"' EXIT
cat > "$body" <<'EOF'
Update to the newest suitable upstream x86_64 Linux release, including prereleases by deliberate policy. Windows-only releases are ignored.

The updater verified the adjacent upstream SHA-256 file, the API digest when present, downloaded bytes, source verification, metadata consistency, and an unprivileged package build. Extraction/layout checks must pass. No AppImage or application was launched.

Review upstream changes and perform a native runtime smoke test before merging. This PR does not publish to AUR.
EOF
gh pr create --base main --head "$branch" --title "Update fthr-clips-bin to $version" --body-file "$body"
# PRs opened with GITHUB_TOKEN do not trigger ordinary pull_request workflows.
gh workflow run ci.yml --ref "$branch"
