#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root=$PWD
package=${1:-fthr-clips-bin}
case "$package" in
  fthr-clips-bin|fthr-clips-git) ;;
  *) echo 'Expected fthr-clips-bin or fthr-clips-git.' >&2; exit 2 ;;
esac
if (( EUID == 0 )); then
  echo 'Run validation as an unprivileged user.' >&2
  exit 1
fi
python -m unittest discover -s tests -v
recipe="$root/packages/$package"
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
cd "$recipe"
# Check committed metadata before makepkg can update a VCS pkgver.
makepkg --printsrcinfo > "$temporary/srcinfo"
diff -u .SRCINFO "$temporary/srcinfo"
python "$root/maintenance/check-sources.py" .SRCINFO
if [[ "$package" == fthr-clips-git ]]; then
  # A moving Git branch changes pkgver during a build. Validate a disposable
  # source recipe so scheduled builds never rewrite the reviewed metadata.
  python - "$recipe" "$temporary/build" <<'PY'
from pathlib import Path
import shutil, sys
source, target = map(Path, sys.argv[1:])
shutil.copytree(source, target, ignore=shutil.ignore_patterns(
    'src', 'pkg', '.git', 'FTHR-Clips', '*.pkg.tar.*', '*.src.tar.*', '*.log'))
PY
  cd "$temporary/build"
fi
makepkg --verifysource --force --noconfirm
makepkg --cleanbuild --force --noconfirm
if [[ "$package" == fthr-clips-bin ]]; then
  python "$root/maintenance/audit-elf.py" pkg/fthr-clips-bin/usr/lib/fthr-clips
else
  python "$root/maintenance/audit-native.py" pkg/fthr-clips-git
fi
desktop-file-validate "pkg/$package/usr/share/applications/fthr-clips.desktop"
# Packaging checks live in PKGBUILD prepare()/package(); no application is launched.
namcap PKGBUILD
package_list=$(makepkg --packagelist)
[[ -n "$package_list" ]]
mapfile -t packages <<< "$package_list"
for archive in "${packages[@]}"; do
  test -s "$archive"
  bsdtar -tf "$archive" >/dev/null
  if command -v namcap >/dev/null; then
    echo 'namcap advisory: bundled libraries can cause dependency and RPATH reports; independent layout checks are the gates.'
    namcap "$archive" || echo 'namcap reported advisory findings.'
  fi
done
