# FTHR Clips for Arch Linux

Authoritative maintenance repository for two alternative packages of
[FTHR Clips](https://github.com/FTHR-Community/FTHR-Clips).

| Package | Upstream source | Runtime | Updates |
| --- | --- | --- | --- |
| [fthr-clips-bin](https://aur.archlinux.org/packages/fthr-clips-bin) | Official Linux release | Extracted upstream AppImage contents | Automatic release monitoring and reviewed update PRs |
| [fthr-clips-git](https://aur.archlinux.org/packages/fthr-clips-git) | Current upstream **linux** branch | Source-built engine, system Python/Qt | Paru development checks and local rebuilds |

```sh
paru -S fthr-clips-bin
# Or switch to development:
paru -S fthr-clips-git
```

They both provide/conflict with `fthr-clips`; pacman removes the installed variant
when you approve the switch. Neither replaces nor obsoletes the other. Packages
never own or remove `~/.fthr`, `~/FTHR_Clips`, or user-selected clip directories.

**KDE capture now works in `fthr-clips-git`:** upstream's ScreenCast/PipeWire
backend was tested on Plasma/KWin Wayland with an RTX 3070. A saved 1440p replay
contains real frames and audio; see [the confirmation on issue #20](https://github.com/FTHR-Community/FTHR-Clips/issues/20#issuecomment-5799875562)
and [TESTING.md](TESTING.md). Install `pipewire`, `dbus`, `xdg-desktop-portal` and
`xdg-desktop-portal-kde`, then approve the monitor in KDE's screen picker.
Screenshots remain a separate grim/Qt path and are not covered by this success.
The currently packaged binary release is still `1.1.0-alpha`, without this backend.

## Repository layout

```text
packages/
  fthr-clips-bin/    # standalone AUR recipe and metadata
  fthr-clips-git/    # standalone AUR recipe, launcher and offline build helpers
maintenance/        # validation, release updater, per-package AUR publication
tests/              # maintenance and package contract tests
.github/workflows/  # validation, monitored releases, independent AUR deployment
README.md
TESTING.md
LICENSE
```

## Binary package

The release recipe is unchanged by the monorepo migration. It verifies the
published SHA-256, extracts the AppImage without executing it, and preserves its
private PyInstaller/Qt/engine tree under `/usr/lib/fthr-clips`. It requires neither
FUSE nor AppImageLauncher. Its desktop identity corrections and KDE UI fallback
are retained. Runtime dependencies are `glibc`, `zlib`, `libglvnd`, `libdrm`,
`libxcb`, and `wayland`; system Python/Qt are build-only or unnecessary.

## Development package

The sole application source is
`git+https://github.com/FTHR-Community/FTHR-Clips.git#branch=linux`.
No fork, pending PR, or downstream feature patch is included. `pkgver()` uses
`git describe --tags --long --abbrev=7`, normalizing `v1.1.0-alpha-3-g64a7b0b`
to `1.1.0alpha0.r3.g64a7b0b`. Keeping `alpha` attached makes pacman sort the
prerelease below beta/rc/stable. Unnumbered prereleases receive an explicit zero
(`alpha0`) so later `alpha1`/`alpha2` also sort correctly. Unrecognized tags fail for review; no epoch.

The engine and playback mixer build with CMake in Release mode. System Python,
PySide6/Qt Multimedia, NumPy, OpenCV and `python-keyboard` run the UI directly.
The private source-style layout under `/usr/lib/fthr-clips` preserves upstream
engine, mixer and asset discovery without rewriting application code. Arch's
OpenCV 5 is newer than upstream's release lock: upstream's Python suite and
actual launch are checked, and scheduled builds catch later incompatibility.
The Windows-only installer contract is explicitly excluded from this Linux
package; all other tests, source checksums and license gates remain enabled.
The exact-whitespace failure is addressed separately in [upstream PR #46](https://github.com/FTHR-Community/FTHR-Clips/pull/46);
that pending change is not applied to the application source here.
The native layout avoids PyInstaller's wheel-specific Qt plugin assumptions.

Only the optional uploader follows upstream's frozen build, preserving its
sealed manifest and explicit in-app consent. Three pinned PyInstaller build-tool
wheels are declared, checksummed sources installed into a temporary tools tree.
There is no pip download, appimagetool, or network fetch in build/package steps.
Licenses for the uploader's actual collected runtime are inventoried from Arch
package ownership and copied alongside upstream notices. New unknown license
evidence stops the build. No uploading or account activation is performed by packaging.

### FFmpeg and licensing

The C++ engine/mixer compile and dynamically link against upstream's exact BtbN
LGPL archive, declared in `source` with a real SHA-256. The current pin is
`n8.1.2-34-g9b6c8969e0`; all seven shared libraries also match upstream's individual
hashes. A changed upstream manifest stops preparation until the recipe is reviewed.
Private libraries retain upstream `$ORIGIN` RPATH and unchanged bytes.

Arch FFmpeg enables GPL components and uses a different ABI. We do not substitute
it into the engine or weaken upstream's release license gate. FTHR itself is now
GPL-3.0-only; older comments saying GPL FFmpeg would newly make it GPL are stale.
Preserving the pinned LGPL engine is both the upstream build contract and the
least surprising ABI choice. Native Qt/OpenCV use their distribution dependencies.

Private `ffmpeg`/`ffprobe` commands are included as a fallback. Their archive has
a broken `-Wl:../lib` RPATH, corrected to `$ORIGIN/../lib` during packaging; shared
library hashes are unaffected. Upstream has also fixed its fetch path
([upstream issue #30](https://github.com/FTHR-Community/FTHR-Clips/issues/30)). Upstream's source-mode resolver prefers
`/usr/bin/ffmpeg` when present. That separate CLI behavior is preserved and does
not change the engine's linkage. License verification covers the source tree and
private FFmpeg provenance; an AppImage-only Qt-wheel gate is not applicable to
the system Qt runtime.

### Desktop and dependencies

Both packages install `/usr/bin/fthr-clips`, a freedesktop entry and a 512px hicolor
icon. The git desktop entry changes only `Exec=AppRun` to `Exec=fthr-clips`;
upstream categories and identity remain intact, including the outstanding identity
issue. No unmerged desktop PR is applied. The launcher retains the tested `xcb`
UI fallback **only on KDE**, unless `QT_QPA_PLATFORM` is already set. It was added
for the initial release's invisible native Wayland window; newer upstream window
fixes have not yet been qualified in native mode by this package. The fallback
preserves `WAYLAND_DISPLAY`, and portal capture works with it.

Git runtime: `python`, `pyside6`, `qt6-multimedia`, `python-numpy`, `python-opencv`,
`python-keyboard` (AUR), `glibc`, `gcc-libs`, `libpulse`, `wayland`, `ca-certificates`.
Build: `base-devel`, `git`, `cmake`, `pkgconf`, `patchelf`, `licenses`,
`python-installer`, `python-packaging`, `python-setuptools`, `libpipewire`, `dbus`.
PipeWire/D-Bus headers are required to compile the explicitly enabled portal backend.
The libraries are loaded dynamically; other capture backends do not require a
running portal service.
Tests: `python-pytest`, `python-pytest-qt`, `python-typing_extensions`.

For **KDE portal capture**, install `pipewire` (including `libpipewire`), `dbus`,
`xdg-desktop-portal` and `xdg-desktop-portal-kde`. Other desktops need their own
ScreenCast-capable portal backend. These are optional capture-path requirements,
not universal application-startup requirements.

Optional: `python-sounddevice` plus its PortAudio dependency for microphones;
`pipewire-pulse` or `pulseaudio` for desktop audio; `grim` for screenshots on
supported compositors; `openbsd-netcat` for compositor shortcut commands;
`xdg-utils`; `xorg-xwayland` for the KDE UI fallback; GPU drivers and X11 helpers
listed in each recipe. Wayland protocol XML is in upstream Git; no separate
`wayland-protocols` build dependency is needed. No privileged groups are added.

## Build, update and publish

```sh
git clone https://github.com/Vaspyyy/fthr-clips-aur.git
cd fthr-clips-aur/packages/fthr-clips-git
# Install the AUR dependency first if building manually:
paru -S --needed python-keyboard
makepkg -si
# From repository root, validate either package:
./maintenance/validate.sh fthr-clips-git
./maintenance/validate.sh fthr-clips-bin
# Existing release updater still defaults to the binary package:
./maintenance/update.sh --check
./maintenance/update.sh
```

GitHub `main` is authoritative for both recipes. Each package has independent
validation and AUR deployment: a development build failure does not block the
release package. Publication copies only tracked files from the selected package
directory into its own AUR Git repository, removes obsolete recipe files, and
makes no commit when already synchronized. A stale workflow cannot overwrite
newer package metadata. Do not edit the AUR repositories independently.

Build jobs have no AUR secret. Separate trusted-main deployment jobs use the
existing dedicated `AUR_SSH_PRIVATE_KEY` and verified pinned AUR host key. AUR
keys authorize the account, not a single package; revoke the dedicated key on
AUR if retiring automation. CI bootstraps `python-keyboard` from a reviewed pinned
AUR recipe, builds it as an unprivileged user and verifies its sources.

The daily release monitor still ignores Windows-only releases, deliberately
accepts Linux prereleases, compares official/API checksums, and opens a review PR.
It fails safely on unexpected naming, checksums, or AppImage layout. Bot-created
PR validation is explicitly dispatched. New releases require a desktop smoke test
before merge. The newer `v1.1.1-alpha` artifact currently changes the reviewed
AppRun launcher checksum, so the binary update is intentionally blocked pending
artifact review; no integrity gate is disabled. To force release monitoring:

```sh
gh workflow run update.yml -R Vaspyyy/fthr-clips-aur
```

VCS packages do **not** receive AUR commits just because upstream moves. Enable
`Devel` in paru.conf (already enabled on the tested machine). Normal checks:

```sh
paru -Qua --devel              # check AUR/development updates
paru -Syu --devel              # update system and development packages
paru -S --rebuild fthr-clips-git # force a fresh development build
```

`git-build.yml` can build current upstream daily when repository variable
`ENABLE_DAILY_GIT_BUILD=true`; manual dispatch always works. It validates only,
with no release updater, commits, PRs or AUR deployment. Failed runs remain visible
in GitHub Actions. To force that check:

```sh
gh workflow run git-build.yml -R Vaspyyy/fthr-clips-aur
```

Packaging/tooling is 0BSD. Application, artwork and bundled third-party notices
are retained in the installed package; see each recipe's license metadata.
