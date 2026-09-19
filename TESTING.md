# Validation notes

## Development package and monorepo (2026-09-19)

Source: upstream `linux` commit `64a7b0b35a22d9153259d3599e47ec0ed50efd8c`;
package `1.1.0alpha0.r3.g64a7b0b-1`. No pending PRs applied.

- All static source checksums pass; only Git uses SKIP.
- Native Release build: 13 CTest contracts pass, VA-API hardware probe skips.
  Full headless Python suite: 1,008 passed, 15 skipped. Tested with Python 3.14.7,
  PySide6 6.11.2, NumPy 2.5.3 and OpenCV 5.0.0.
- Upstream source license gate passes. All seven FFmpeg shared-library hashes
  match upstream after packaging. Private CLI RPATH is relocated separately.
- 11 ELF files pass layout/dependency auditing. Engine/mixer `ldd` resolves
  private FFmpeg correctly; no absolute build-host RPATH, privileged bits or
  unsafe symlinks. Package files stay under `/usr`.
- `namcap PKGBUILD` passes. Package advisories cover private Python imports,
  guarded Windows imports, private FFmpeg, and unstripped binaries. The real
  insecure CLI RPATH finding was fixed. Desktop validation accepts upstream's
  multiple-category hint; pending desktop identity changes are not applied.
- Maintenance tests cover both metadata files, branch/version order, source
  checksums, updater rollback/paths, independent package deployment, stale/no-op
  publication, obsolete file removal and isolated VCS version regeneration.
- The binary recipe and metadata are byte-identical to their pre-migration
  versions. Its runtime behavior is unchanged.

Installed-package testing on KDE Wayland + RTX 3070:

- User-authorized pacman lifecycle script passed bin → git → bin → git and
  removal/reinstallation. Checksums of every pre-existing FTHR settings/clip file
  were unchanged by the transactions, including custom clip directories.
- `pacman -Qi`, `-Ql`, and `-Qkk` inspected: 205 files, zero altered files in the
  first installed payload. All owned paths are under `/usr`.
- Both terminal launch and KDE's installed desktop entry open a visible UI.
  KService resolves the correct name, executable and theme icon. Native Wayland
  remains invisible on KWin, so the launcher keeps a KDE-only xcb fallback.
- Engine and playback mixer resolve at their installed source-style paths.
  PortAudio microphone capture starts; PulseAudio captures the default monitor
  at 48 kHz stereo. Loading OpenCV before the mixer also succeeds.
- Screenshot IPC reaches grim, which rejects KWin's unsupported protocol; Qt's
  fallback produces a black PNG. Replay reaches the engine, then fails at absent
  KWin capture protocols before encoder selection. Neither improves over bin.
- The window has an icon, but its desktop identity still resolves to `python3`;
  task-manager grouping remains an upstream limitation. No pending desktop PR
  is applied. Desktop validation accepts upstream's multiple-category hint.
- The sealed optional uploader and its licenses were validated; no upload or
  account activation was performed. Test app processes were closed afterward.
- Direct private FFmpeg/ffprobe commands work from outside their install directory;
  a one-second OpenH264/AAC encode probes as 1.000000 seconds. The original archive's
  malformed CLI RPATH is reported in [upstream issue #30](https://github.com/FTHR-Community/FTHR-Clips/issues/30).

The first lifecycle-tested package used the preliminary version
`1.1.0alpha.r3.g64a7b0b-1`; final metadata adds `alpha0` to order numbered alphas
correctly. Subsequent changes add license notices and an explicit pytest-qt
`python-typing_extensions` test dependency; application code remains unchanged.

### Clean Arch and automation checks

Both packages build in a fresh `archlinux:base-devel` container using declared
packages and the reviewed `python-keyboard` AUR bootstrap. Source retrieval and
preparation finish first; Docker networking is then disconnected for build,
tests and packaging. Both offline builds pass, including 1,008 Python tests,
13 CTest passes and one hardware skip. Source verification with `--holdver`,
metadata comparisons, desktop validation and ELF audits also pass. No `/workspace`
paths appear in the installed payload. The maintenance suite has 32 passing tests.

The migrated binary updater's live check finds `v1.1.0-alpha`, verifies its
published digest and makes no changes. The [release-monitor run](https://github.com/Vaspyyy/fthr-clips-aur/actions/runs/35435502842)
passes. Independent binary validation/publication also succeeds while git jobs
run; unchanged binary metadata produces no AUR commit.

Remote [package CI](https://github.com/Vaspyyy/fthr-clips-aur/actions/runs/35435493799),
[both AUR deployments](https://github.com/Vaspyyy/fthr-clips-aur/actions/runs/35435493918),
and the [development-branch check](https://github.com/Vaspyyy/fthr-clips-aur/actions/runs/35435501518)
pass at `7e772c9`. A fresh public AUR clone matches all six tracked git recipe
files byte for byte. The AUR page lists Ransom as maintainer. No fake upstream
commit bump is published by the scheduled development check.

Paru 2.1.0 has `Devel` enabled on the test machine. A probe using isolated
`XDG_STATE_HOME` and cache directories records the actual upstream URL and
`branch = "linux"`: the current commit yields no update, while an older upstream
tag yields `fthr-clips-git ... -> latest-commit`. Real user tracking state is
untouched by this probe; a normal paru installation registers its own baseline.

Final end-to-end installation used `paru -S --rebuild --redownload fthr-clips-git`
from the public AUR (`dcead82`). Installed version is
`1.1.0alpha0.r3.g64a7b0b-1`; `pacman -Qkk` reports 205 files and zero alterations.
Paru's real `devel.toml` now records the upstream URL, `branch = "linux"`, and
`64a7b0b35a22d9153259d3599e47ec0ed50efd8c`. Its development check reports no update
at that commit. Terminal launch was repeated on this final build: visible UI,
correct engine discovery, resolved libraries, microphone and PulseAudio detection.

## Previously validated binary release

Validated release: upstream `v1.1.0-alpha`, Arch `1.1.0alpha-2`, 2026-09-18.
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

## Completed publication and lifecycle checks

- A fresh GitHub checkout and a fresh public AUR clone both build; all source
  checks pass and AUR `PKGBUILD`/`.SRCINFO` match GitHub byte for byte.
- The user ran the supplied sudo lifecycle test on revision 1 and reported PASS. It installs,
  removes, verifies existing settings/clips by SHA-256, and reinstalls. Final
  `pacman -Qkk` reports zero altered files.
- Plain terminal launch and KDE's `kioclient exec` desktop-entry launch start the
  final installed program with its bundled engine. Application inventory confirms
  a visible FTHR Clips window. The icon file matches upstream exactly. Qt resolves it through the active
  desktop icon theme. The window exports a 48px `_NET_WM_ICON`.
- Screenshot hotkey IPC reaches the app. `grim` fails because KWin lacks its
  capture protocol, then Qt's XWayland fallback writes an entirely black PNG.
  Screenshots are therefore **not functional** on this tested desktop.
- Remote package CI, upstream-monitor workflow dispatch, and authenticated AUR
  deployment have all completed successfully. The deploy job verified AUR
  already matches the reviewed package, exercising the configured secret/key.
- A new-release PR cannot be observed until a newer release exists; release
  selection, checksum rejection and transactional update paths are unit tested.
- Native desktop screenshot automation was unavailable (portal denied), so no
  visual screenshot assertion for the Plasma taskbar/menu icon is claimed.

Upstream follow-up: [desktop identity PR #19](https://github.com/FTHR-Community/FTHR-Clips/pull/19),
[capture limitation issue #20](https://github.com/FTHR-Community/FTHR-Clips/issues/20).

KDE's actual `KService::serviceByDesktopName("fthr-clips")` resolves the installed
entry with name `FTHR Clips`, executable `fthr-clips`, menu ID
`fthr-clips.desktop`, `noDisplay=false`, and an icon resolved by the current
Win11-black theme via hicolor inheritance. Revision 2 adds the observed
`StartupWMClass=FTHR Clips` for XWayland grouping; it changes desktop metadata
only. The direct UI/engine binaries remain byte-identical to revision 1.
