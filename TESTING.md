# Validation notes

Initial release: upstream `v1.1.0-alpha`, Arch `1.1.0alpha-1`, 2026-09-18.
Official artifact SHA-256:
`47634819ac68e797ca42e76c9d1fe9f465d817f937a177d75733f4a591086b1a`.
Matched the adjacent release checksum and GitHub API digest.

- `makepkg --verifysource`, `makepkg -f`, and `.SRCINFO` comparison pass.
- `desktop-file-validate` passes after removing the extra Game main category.
- A static `readelf` audit covers 296 ELF files and gates new external SONAMEs.
- AppImage contents have no setuid/setgid files or device nodes. Symlinks stay
  inside the extracted tree; the package contains no home paths or install hooks.
- `vercmp` and updater tests cover prerelease ordering, wrong/ambiguous artifacts,
  checksum/origin validation, Windows-only releases, and metadata rollback.
- `pacman -Qi`, `-Ql`, and `-Qkk` inspected; initial installation had 676 files,
  all verified unchanged. All package payload paths are under `/usr`.

## Real desktop

CachyOS, KDE Plasma/KWin 6.7.5, Wayland, RTX 3070, NVIDIA 615.71.09,
PipeWire 1.6.8 with PulseAudio compatibility.

The installed application resolves `/usr/lib/fthr-clips/_internal/FTHRclips`,
loads its Qt/multimedia runtime, registers the hotkey socket, and starts PulseAudio
capture of the default output monitor at 48 kHz stereo. The UI is visible through
Qt's `xcb` backend; its accessibility tree exposes the clip library, settings,
input devices, and the capture error. Native Wayland has an invisible-window
problem also tracked by upstream PR #10. The package defaults only KDE to `xcb`.

KWin exposes neither `zwlr_screencopy_manager_v1` nor ext-image-copy-capture.
Engine output confirms both attempts fail, refuses an XWayland capture fallback,
and stops. Consequently no successful replay/NVENC recording is claimed. This
happens before encoder initialization, so it does not demonstrate an NVIDIA
encoding defect. AMD hardware qualification cannot be performed on this machine.
The direct unmodified AppImage also produces a startup `BufferError` in the
engine-connect thread; upstream PRs #10/#16 already address that race.

## namcap interpretation

The complete PKGBUILD and built package were checked. The recipe's x86_64 naming
warning reflects upstream's explicitly x86_64-only artifact. Package reports
include 19 missing-dependency errors for libraries/Python/Qt modules that are
actually bundled inside PyInstaller's private tree. Runtime uses that tree;
installing duplicate system Qt/Python/GTK packages is not the remedy.

There are also upstream missing PIE/FULL RELRO warnings and unused-library/RPATH
reports. Hardening requires an upstream rebuild, outside a binary repackaging.
These findings remain advisory rather than being hidden by a fake dependency
list. The independent ELF dependency, artifact-layout, and desktop checks are
mandatory CI gates. Static basename closure cannot prove every dynamic lookup;
real desktop testing remains required for release PRs. CI never runs the app.
