#!/usr/bin/env bash
# CI prerequisite only: python-keyboard is in AUR, not official Arch repositories.
# Root installs the result; the pinned recipe/source are built as the CI builder.
set -euo pipefail
install_keyboard_archive() {
  local listing archive name
  local -a candidates=()
  listing=$(runuser -u builder -- makepkg --packagelist)
  while IFS= read -r archive; do
    # makepkg may list a debug archive even when this pure-Python build did
    # not produce one. Select the real runtime package by its own metadata.
    [[ -s "$archive" ]] || continue
    name=$(pacman -Qpq -- "$archive")
    if [[ "$name" == python-keyboard ]]; then
      candidates+=("$archive")
    fi
  done <<< "$listing"
  if (( ${#candidates[@]} != 1 )); then
    echo 'Expected exactly one existing python-keyboard package archive.' >&2
    return 1
  fi
  pacman -U --noconfirm -- "${candidates[0]}"
}

# Permit offline tests to exercise selection without privileged build setup.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
  return
fi

if (( EUID != 0 )); then
  echo 'Run this CI bootstrap as root after creating the unprivileged builder.' >&2
  exit 1
fi
pin=2a0dc174a8bf63bd8c3d4659a6040123d3e9e236
# Reviewed 0.13.5-3: GitHub boppreh/keyboard v0.13.5 source with a fixed SHA512;
# python -m build --wheel --no-isolation, then python -m installer. No pip.
id builder >/dev/null
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
chown builder:builder "$temporary"
runuser -u builder -- git clone https://aur.archlinux.org/python-keyboard.git "$temporary/python-keyboard"
runuser -u builder -- git -C "$temporary/python-keyboard" checkout --detach "$pin"
[[ $(runuser -u builder -- git -C "$temporary/python-keyboard" rev-parse HEAD) == "$pin" ]]
cd "$temporary/python-keyboard"
runuser -u builder -- makepkg --verifysource --force --noconfirm
runuser -u builder -- makepkg --cleanbuild --force --noconfirm
install_keyboard_archive
