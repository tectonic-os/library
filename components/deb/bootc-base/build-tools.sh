#!/usr/bin/env bash
# This compiles bootc and bootupd from this component's pins into `$DESTDIR`.
# The tools workflow sets `DESTDIR` to stage the same bytes as a tarball.
set -euxo pipefail

source /ctx/lib/family.sh
source /ctx/lib/fetch-helpers.sh

# `DEST` has no trailing slash, so `${DEST}/usr` serves a staging tree and
# the image alike.
DEST="${DESTDIR:-/}"
DEST="${DEST%/}"

# The toolchain is purged at the end, so the compile stays in one layer.
# `autoremove` is safe, because `install_packages` marks every component's
# packages manual. binutils and some of its libraries still stay in the image.
BUILD_DEPS=(
    build-essential rustc cargo
    libostree-dev libzstd-dev libssl-dev pkgconf go-md2man
)
install_packages "${BUILD_DEPS[@]}"

# A bump that moves only one of the two bootc pins gives cargo a vendor tree
# for the wrong version.
if [ "$ASSET_BOOTC_VERSION" != "$ASSET_BOOTC_VENDOR_VERSION" ]; then
    echo "bootc is pinned at ${ASSET_BOOTC_VERSION} and its vendor tarball at" \
        "${ASSET_BOOTC_VENDOR_VERSION}; both pins move together" >&2
    exit 1
fi

src=/tmp/bootc
fetch_extract "$ASSET_BOOTC_URL" "$ASSET_BOOTC_SHA256" "$src"
cd "${src}/bootc-${ASSET_BOOTC_VERSION}" || exit

# The source ships `.cargo/vendor-config.toml` but does not apply it.
fetch_extract "$ASSET_BOOTC_VENDOR_URL" "$ASSET_BOOTC_VENDOR_SHA256" .
cat .cargo/vendor-config.toml >> .cargo/config.toml

# `CARGO_NET_OFFLINE` makes a missing vendor crate fail the build.
export CARGO_NET_OFFLINE=true
export CARGO_BUILD_LOCKED=true

# Upstream's release profile keeps debug symbols for an RPM to split out.
# Nothing splits them here, so the build strips them.
export CARGO_PROFILE_RELEASE_DEBUG=false
export CARGO_PROFILE_RELEASE_STRIP=true

# `install-all` adds a test binary and the `ostree container` symlinks. A
# product image needs neither.
make bin install DESTDIR="${DEST:-/}"
"${DEST}/usr/bin/bootc" --version

cd /
rm -rf "$src"

# ---- bootupd ----
if [ "$ASSET_BOOTUPD_VERSION" != "$ASSET_BOOTUPD_VENDOR_VERSION" ]; then
    echo "bootupd is pinned at ${ASSET_BOOTUPD_VERSION} and its vendor tarball" \
        "at ${ASSET_BOOTUPD_VENDOR_VERSION}; both pins move together" >&2
    exit 1
fi

src=/tmp/bootupd
fetch_extract "$ASSET_BOOTUPD_URL" "$ASSET_BOOTUPD_SHA256" "$src"
cd "${src}/bootupd-${ASSET_BOOTUPD_VERSION}" || exit
fetch_extract "$ASSET_BOOTUPD_VENDOR_URL" "$ASSET_BOOTUPD_VENDOR_SHA256" .

# bootupd's vendor tarball has no `.cargo` fragment, so this writes the
# crates.io redirect.
mkdir -p .cargo
cat >> .cargo/config.toml << 'CARGO'
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
CARGO

# bootupd installs the static GRUB configs on every install, so a missing
# `install-grub-static` fails `bootc install` after it partitions the disk.
# `install-systemd-unit` is left out, because nothing enables its update unit.
make all install install-grub-static DESTDIR="${DEST:-/}" PREFIX=/usr LIBEXECDIR=/usr/libexec
"${DEST}/usr/bin/bootupctl" --version

# The signed deb GRUB has no `blscfg` and cannot load `blsuki.mod` under
# Secure Boot, so this fragment fails every boot.
rm -f "${DEST}/usr/lib/bootupd/grub2-static/configs.d/10_blscfg.cfg"

# bootupd calls `grub2-editenv`, and the deb families name it `grub-editenv`.
# The link dangles in a staging tree until the tarball is unpacked.
ln -sf grub-editenv "${DEST}/usr/bin/grub2-editenv"

cd /
rm -rf "$src"

DEBIAN_FRONTEND=noninteractive apt-get purge -y "${BUILD_DEPS[@]}"
DEBIAN_FRONTEND=noninteractive apt-get autoremove -y --purge
