# fthr-clips-bin

Arch packaging for the official x86_64 Linux binary of
[FTHR Clips](https://github.com/FTHR-Community/FTHR-Clips).
[AUR package](https://aur.archlinux.org/packages/fthr-clips-bin).

```sh
paru -S fthr-clips-bin
```

**Linux alpha:** upstream qualifies Hyprland/AMD. KDE Wayland currently cannot
record: its compositor exposes neither of the two capture protocols implemented
by FTHR, and FTHR has no ScreenCast portal backend. Screenshots also fail (the Qt fallback
produces black output on the tested desktop). NVIDIA NVENC exists in the
engine but is not upstream-qualified; a compositor failure happens before encoder
selection. Installing this package does not remove those limitations.

## Packaging

The official AppImage is SHA-256 pinned, extracted with `unsquashfs` without
executing its runtime, and installed under `/usr/lib/fthr-clips`. Its PyInstaller
`_internal` tree, Qt plugins, engine, bundled libraries, and optional uploader
remain together. No FUSE, AppImageLauncher, system Python, or system Qt is needed
at runtime. The binary itself is unmodified. Licenses/notices go under
`/usr/share/licenses/fthr-clips-bin`.

The small upstream AppRun is adapted into `/usr/bin/fthr-clips`: a fixed install
path, caller-respecting Qt backend selection, and Qt's `-desktopfile fthr-clips`
option. A normal desktop entry and 512px hicolor icon provide desktop integration.
For this alpha, KDE uses Qt's XWayland UI backend to avoid the invisible native
Wayland window tracked by [upstream PR #10](https://github.com/FTHR-Community/FTHR-Clips/pull/10).
This only changes the UI; Wayland capture remains subject to the limitation above.
Set `QT_QPA_PLATFORM=wayland` explicitly to test the native UI. Reassess the
version-specific fallback on every release.

Runtime dependencies come from an ELF audit: `glibc`, `zlib`, `libglvnd`, `libdrm`,
`libxcb`, `wayland`. Important optional dependencies: `pipewire-pulse` or
`pulseaudio` for audio; `grim` for supported Wayland screenshots;
`openbsd-netcat` for compositor shortcut commands; `ffmpeg` for export/thumbnails;
`xdg-utils` for opening folders; `xorg-xwayland` for the KDE UI workaround;
GPU drivers and X11 helpers as described in PKGBUILD. `wayland-protocols` is a
build dependency upstream, not a runtime dependency here. Neither root nor
membership of `input` is required. KDE shortcuts are not registered automatically.

Upstream stores settings/logs in `~/.fthr` and clips in `~/FTHR_Clips` (or the
user-selected location). The package owns neither directory and has no install,
removal, or migration scripts touching user data. Uploading stays opt-in; the
bundled uploader is not activated by this package. No self-updater was found.

## Build and maintain

```sh
sudo pacman -S --needed base-devel git python squashfs-tools namcap desktop-file-utils
git clone https://github.com/Vaspyyy/fthr-clips-aur.git
cd fthr-clips-aur
makepkg -si
# Find and validate a newer upstream Linux release, including alpha/beta/rc:
./maintenance/update.sh
# Check only:
./maintenance/update.sh --check
# Full source, build, metadata, ELF, desktop, and advisory namcap checks:
./maintenance/validate.sh
```

GitHub `main` is authoritative. A daily GitHub Action and manual workflow dispatch
look for the highest supported upstream version with the exact Linux x86_64
AppImage. Windows-only releases are ignored. Alpha/beta/rc releases are deliberate;
`1.1.0-alpha` becomes `1.1.0alpha`, which `vercmp` orders before beta, rc, and stable.
There is no epoch. Unrecognized version/artifact naming fails for review.

The updater checks the adjacent official checksum and GitHub asset digest when
provided, verifies the downloaded bytes, resets pkgrel, regenerates `.SRCINFO`,
and builds as an ordinary user. Missing checksums, changed same-version artifacts,
new launcher/layout, unsafe permissions/symlinks, or new external ELF libraries
stop automation. Failed updates restore the original metadata.

Because these are experimental releases, automation opens an **update PR** instead
of blindly promoting a new binary. Review upstream changes and perform a real
desktop smoke test before merging. Existing update branches are never overwritten.
CI is explicitly dispatched for bot-created PRs because GitHub suppresses ordinary
PR events generated using `GITHUB_TOKEN`.

After reviewed package changes reach `main`, a separate workflow rebuilds without
AUR credentials, then publishes only `PKGBUILD`, `.SRCINFO`, and `LICENSE` through
AUR Git. It uses the dedicated `AUR_SSH_PRIVATE_KEY` secret and a pinned SSH host
key verified against AUR's published fingerprint. No private key is in Git.
AUR account SSH keys are account credentials, not package-scoped deploy keys;
revoke this dedicated key in the AUR profile if the automation is retired.
Do not edit AUR independently: send packaging changes to GitHub first.

Actions require repository permission to create pull requests and the dedicated
public key registered on the maintainer's AUR account. To trigger monitoring now:

```sh
gh workflow run update.yml -R Vaspyyy/fthr-clips-aur
```

The packaging/tooling is 0BSD. The application is GPL-3.0-only, generated artwork
MIT, with bundled third-party licenses retained. See [TESTING.md](TESTING.md) for
validation evidence and the limits of automated tests.
