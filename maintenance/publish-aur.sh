#!/usr/bin/env bash
# Publish reviewed package metadata only. Call after trusted-main validation.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${AUR_SSH_PRIVATE_KEY:?Set a dedicated AUR account SSH private key}"
if [[ "${GITHUB_ACTIONS:-}" == true && "${GITHUB_REF:-}" != refs/heads/main ]]; then
  echo 'AUR publication is restricted to trusted main.' >&2
  exit 1
fi
# A docs-only main commit must not suppress a validated package publication.
# Fetch without changing the reviewed checkout, then compare every published blob.
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
  git fetch --no-tags origin refs/heads/main
  for package_file in PKGBUILD .SRCINFO LICENSE; do
    if [[ $(git rev-parse "HEAD:$package_file") != $(git rev-parse "FETCH_HEAD:$package_file") ]]; then
      echo 'Package metadata advanced during this run; the newer package workflow must publish it.' >&2
      exit 1
    fi
  done
fi
workspace=$PWD
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
umask 077
printf '%s\n' "$AUR_SSH_PRIVATE_KEY" > "$temporary/key"
unset AUR_SSH_PRIVATE_KEY
cat > "$temporary/known_hosts" <<'EOF'
aur.archlinux.org ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEuBKrPzbawxA/k2g6NcyV5jmqwJ2s+zpgZGZ7tpLIcN
EOF
# Fingerprint published at https://aur.archlinux.org/; never trust ssh-keyscan alone.
fingerprint=$(ssh-keygen -lf "$temporary/known_hosts" -E sha256 | awk '{print $2}')
[[ "$fingerprint" == SHA256:RFzBCUItH9LZS0cKB5UE6ceAYhBD5C8GeOBip8Z11+4 ]]
export GIT_SSH_COMMAND="ssh -i $temporary/key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$temporary/known_hosts -o BatchMode=yes"
git clone ssh://aur@aur.archlinux.org/fthr-clips-bin.git "$temporary/aur"
cd "$temporary/aur"
# AUR receives only its source package recipe and license, never binaries or CI files.
install -m644 "$workspace/PKGBUILD" "$workspace/.SRCINFO" "$workspace/LICENSE" .
git add PKGBUILD .SRCINFO LICENSE
if git diff --cached --quiet; then
  echo 'AUR already matches reviewed metadata.'
  exit 0
fi
git config user.name Vaspyyy
git config user.email lolbautz2@gmail.com
version=$(sed -n 's/^pkgver=//p' PKGBUILD)
release=$(sed -n 's/^pkgrel=//p' PKGBUILD)
git commit -m "Update fthr-clips-bin to $version-$release"
git push origin HEAD:master
