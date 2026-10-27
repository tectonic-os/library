# bootc's `--composefs-backend` needs libostree 2025.3 or newer. This check
# runs before the toolchain install, so an older base fails fast. dpkg answers
# because pkg-config is a build dependency that is not installed yet.
NEEDS_OSTREE=2025.3
HAS_OSTREE="$(dpkg-query -W -f '${Version}' libostree-1-1)"
if ! dpkg --compare-versions "$HAS_OSTREE" ge "$NEEDS_OSTREE"; then
    echo "this base carries libostree ${HAS_OSTREE}, and bootc" \
        "${ASSET_BOOTC_VERSION} needs >= ${NEEDS_OSTREE}" >&2
    exit 1
fi

# By default `build-tools.sh` compiles bootc and bootupd from the pins in
# `manifest.kdl`. If `prebuilt-tools` is set, then a tarball built from the
# same pins replaces the compile. An absent tarball or a hash mismatch falls
# back to the compile.
vendor="$(. /etc/os-release && echo "$ID")"
tools=/tmp/bootc-tools.tar.zst
from_source=yes
if [ "${OPT_PREBUILT_TOOLS:-0}" = 1 ]; then
    pin="ASSET_BOOTC_TOOLS_${vendor^^}"
    url="${pin}_URL"
    sha="${pin}_SHA256"
    if curl --retry 3 -fsSLo "$tools" "${!url}" \
        && echo "${!sha}  ${tools}" | sha256sum --status -c -; then
        tar --use-compress-program=zstd -xf "$tools" -C /
        from_source=no
    else
        echo "bootc-base: prebuilt-tools is set and no tarball matching" \
            "${!sha} is at ${!url}; compiling from the pins instead" >&2
    fi
    rm -f "$tools"
fi
[ "$from_source" = no ] || bash "${COMPONENT_DIR}/build-tools.sh"
ldconfig
bootc --version
bootupctl --version

# This uses the `usr/lib/efi` payload layout, because bootupd versions the
# `usr/lib/ostree-boot` layout with `rpm -qf`. bootupd drops a component named
# after another bootloader, so the signed GRUB is named `grub2`.
#
# The vendor directory is the os-release ID, because `grubx64.efi` embeds it
# as the prefix where shim looks for GRUB. Ubuntu ships no signed MokManager.
shim_dir="/usr/lib/efi/shim/$(dpkg-query -W -f '${Version}' shim-signed)/EFI"
grub_dir="/usr/lib/efi/grub2/$(dpkg-query -W -f '${Version}' grub-efi-amd64-signed)/EFI"

install -D -m 0644 /usr/lib/shim/shimx64.efi.signed "${shim_dir}/${vendor}/shimx64.efi"
install -D -m 0644 /usr/lib/shim/shimx64.efi.signed "${shim_dir}/BOOT/BOOTX64.EFI"
# Ubuntu ships no signed fallback. The removable path boots without it.
if [ -f /usr/lib/shim/fbx64.efi.signed ]; then
    install -D -m 0644 /usr/lib/shim/fbx64.efi.signed "${shim_dir}/BOOT/fbx64.efi"
fi
if [ -f /usr/lib/shim/mmx64.efi.signed ]; then
    install -D -m 0644 /usr/lib/shim/mmx64.efi.signed "${shim_dir}/${vendor}/mmx64.efi"
fi
install -D -m 0644 /usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed \
    "${grub_dir}/${vendor}/grubx64.efi"

# bootc installs with `--generic-image`, so no NVRAM entry exists and firmware
# starts `EFI/BOOT/BOOTX64.EFI`. Without GRUB in its own directory, shim runs
# the fallback and the fallback resets the machine. The fallback reads
# `BOOTX64.CSV` to write an NVRAM entry.
install -D -m 0644 /usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed \
    "${shim_dir}/BOOT/grubx64.efi"
install -D -m 0644 /usr/lib/shim/BOOTX64.CSV "${shim_dir}/${vendor}/BOOTX64.CSV"

# This is upstream's static GRUB stub from `make install-grub-static`. It is
# read from the installed tree, because the prebuilt path unpacks no source.
# The stub finds /boot by the UUID that `bootupctl backend install
# --write-uuid` writes, or by the `boot` label. The signed deb GRUB carries
# the `search`, `source` and `configfile` commands that the stub needs.
install -D -m 0644 /usr/lib/bootupd/grub2-static/grub-static-efi.cfg \
    "${grub_dir}/${vendor}/grub.cfg"

# bootc checks for `/usr/lib/bootupd/updates` and `bootupctl` to decide
# whether GRUB can be installed.
bootupctl backend generate-update-metadata /
