#!/usr/bin/env bash
# Publish reviewed source recipes only. Call after trusted-main validation.
set -euo pipefail
cd "$(dirname "$0")/.."
package=${1:-fthr-clips-bin}
case "$package" in
  fthr-clips-bin|fthr-clips-git) ;;
  *) echo 'Expected fthr-clips-bin or fthr-clips-git.' >&2; exit 2 ;;
esac
recipe="packages/$package"
: "${AUR_SSH_PRIVATE_KEY:?Set a dedicated AUR account SSH private key}"
if [[ "${GITHUB_ACTIONS:-}" == true && "${GITHUB_REF:-}" != refs/heads/main ]]; then
  echo 'AUR publication is restricted to trusted main.' >&2
  exit 1
fi
# Compare the entire package tree, including patches/launchers. A docs-only main
# commit must not suppress publication; newer recipe contents must block it.
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
  git fetch --no-tags origin refs/heads/main
  if [[ $(git rev-parse "HEAD:$recipe") != $(git rev-parse "FETCH_HEAD:$recipe") ]]; then
    echo 'Package metadata advanced during this run; the newer package workflow must publish it.' >&2
    exit 1
  fi
fi
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
# Export committed recipe contents only, excluding local build products and any
# dynamic pkgver change made by a VCS build. GitHub is the authoritative source.
mkdir "$temporary/recipe"
git archive "HEAD:$recipe" | tar -x -C "$temporary/recipe"
umask 077
printf '%s\n' "$AUR_SSH_PRIVATE_KEY" > "$temporary/key"
unset AUR_SSH_PRIVATE_KEY
cat > "$temporary/known_hosts" <<'HOSTS'
aur.archlinux.org ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEuBKrPzbawxA/k2g6NcyV5jmqwJ2s+zpgZGZ7tpLIcN
HOSTS
# Fingerprint published at https://aur.archlinux.org/; never trust ssh-keyscan alone.
fingerprint=$(ssh-keygen -lf "$temporary/known_hosts" -E sha256 | awk '{print $2}')
[[ "$fingerprint" == SHA256:RFzBCUItH9LZS0cKB5UE6ceAYhBD5C8GeOBip8Z11+4 ]]
export GIT_SSH_COMMAND="ssh -i $temporary/key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$temporary/known_hosts -o BatchMode=yes"
git clone "ssh://aur@aur.archlinux.org/$package.git" "$temporary/aur"
cd "$temporary/aur"
# Remove obsolete tracked recipe files too; preserve the separate AUR history.
git ls-files -z | xargs -0 -r rm -f --
cp -a "$temporary/recipe/." .
git add -A
if git diff --cached --quiet; then
  echo "AUR $package already matches reviewed metadata."
  exit 0
fi
git config user.name Vaspyyy
git config user.email lolbautz2@gmail.com
version=$(sed -n 's/^pkgver=//p' PKGBUILD)
release=$(sed -n 's/^pkgrel=//p' PKGBUILD)
git commit -m "Update $package recipe ($version-$release)"
git push origin HEAD:master
