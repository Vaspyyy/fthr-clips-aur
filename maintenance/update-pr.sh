#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Token is used for this repository only; never publish to AUR from this job.
python maintenance/update.py --allow-prerelease
if git diff --quiet -- packages/fthr-clips-bin/PKGBUILD packages/fthr-clips-bin/.SRCINFO; then
  exit 0
fi
version=$(sed -n 's/^pkgver=//p' packages/fthr-clips-bin/PKGBUILD)
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-z]+[0-9]*)?$ ]]
branch="automation/upstream-$version"
# Resume interrupted proposals without overwriting an existing automation branch.
if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  echo "Update branch $branch already exists; preserving its contents."
else
  git switch -c "$branch"
  git config user.name 'github-actions[bot]'
  git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
  git add packages/fthr-clips-bin/PKGBUILD packages/fthr-clips-bin/.SRCINFO
  git commit -m "Update fthr-clips-bin to $version"
  gh auth setup-git
  git push origin "HEAD:refs/heads/$branch"
fi
pr_state=$(gh pr list --base main --head "$branch" --state all --json state --jq '.[0].state // ""')
if [[ "$pr_state" == CLOSED || "$pr_state" == MERGED ]]; then
  echo "Proposal for $version was already closed or merged; leaving the decision unchanged."
  exit 0
fi
body=$(mktemp)
trap 'rm -f "$body"' EXIT
cat > "$body" <<'EOF'
Update to the newest suitable upstream x86_64 Linux release, including prereleases by deliberate policy. Windows-only releases are ignored.

The updater verified the adjacent upstream SHA-256 file, the API digest when present, downloaded bytes, source verification, metadata consistency, and an unprivileged package build. Extraction/layout checks must pass. No AppImage or application was launched.

Review upstream changes and perform a native runtime smoke test before merging. This PR does not publish to AUR.
EOF
if [[ -z "$pr_state" ]]; then
  gh pr create --base main --head "$branch" --title "Update fthr-clips-bin to $version" --body-file "$body"
fi
# PRs opened with GITHUB_TOKEN do not trigger ordinary pull_request workflows.
branch_sha=$(git ls-remote --exit-code --heads origin "$branch" | cut -f1)
existing_run=$(gh run list --workflow ci.yml --branch "$branch" --commit "$branch_sha" --limit 1 --json databaseId --jq '.[0].databaseId // ""')
if [[ -z "$existing_run" ]]; then
  gh workflow run ci.yml --ref "$branch"
else
  echo "Package checks already exist for this branch revision; inspect their result before merging."
fi
