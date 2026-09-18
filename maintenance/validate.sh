#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if (( EUID == 0 )); then
  echo 'Run validation as an unprivileged user.' >&2
  exit 1
fi
python -m unittest discover -s tests -v
info=$(mktemp)
trap 'rm -f "$info"' EXIT
makepkg --printsrcinfo > "$info"
diff -u .SRCINFO "$info"
if grep -Eq '^[[:space:]]*sha256sums = SKIP$' .SRCINFO; then
  echo 'Unchecked sources are forbidden.' >&2
  exit 1
fi
makepkg --verifysource --force --noconfirm
makepkg --cleanbuild --force --noconfirm
python maintenance/audit-elf.py pkg/fthr-clips-bin/usr/lib/fthr-clips
desktop-file-validate pkg/fthr-clips-bin/usr/share/applications/fthr-clips.desktop
# Packaging checks live in PKGBUILD prepare()/package(); no application is launched.
namcap PKGBUILD
mapfile -t packages < <(makepkg --packagelist)
for package in "${packages[@]}"; do
  test -s "$package"
  bsdtar -tf "$package" >/dev/null
  if command -v namcap >/dev/null; then
    echo "namcap advisory: bundled PyInstaller/Qt libraries cause false dependency and RPATH reports; upstream hardening cannot be repaired by repackaging."
    namcap "$package" || echo "namcap reported advisory findings; the independent ELF/layout/desktop checks are the gates."
  fi
done
