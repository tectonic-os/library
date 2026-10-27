# This runs after every component's packages, so the initramfs and the
# relocated package state hold them all.

# The deb kernel package installs vmlinuz under `/boot`. bootc reads it from
# `/usr/lib/modules/<kver>`.
kver="$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d -printf '%f\n')"
# `wc -l` counts an empty string as one line, so the empty case is tested first.
if [ -z "$kver" ] || [ "$(printf '%s\n' "$kver" | wc -l)" != 1 ]; then
    echo "bootc wants exactly one kernel; /usr/lib/modules has: ${kver}" >&2
    exit 1
fi
[ -f "/usr/lib/modules/${kver}/vmlinuz" ] \
    || cp "/boot/vmlinuz-${kver}" "/usr/lib/modules/${kver}/vmlinuz"
depmod "$kver"
initramfs="/usr/lib/modules/${kver}/initramfs.img"
dracut --force --kver "$kver" "$initramfs"

# dracut exits 0 when a module is missing, so this checks for the files that
# boot the deployment. A here-string avoids the SIGPIPE that `grep -q` causes
# in a pipeline under `pipefail`.
listing="$(lsinitrd "$initramfs")"
for path in usr/lib/bootc/initramfs-setup \
    usr/lib/systemd/system/bootc-root-setup.service \
    usr/bin/systemd-cryptsetup; do
    if ! grep -q "[ /]${path}\$" <<< "$listing"; then
        echo "the initramfs carries no ${path}, so a machine from this image cannot boot" >&2
        exit 1
    fi
done

# cryptsetup loads the TPM2 token plugin and the tss2 libraries at run time,
# so dracut cannot find them through link dependencies. The match is on file
# names, because each family has its own multiarch directory.
for name in libcryptsetup-token-systemd-tpm2.so libtss2-esys.so libtss2-rc.so \
    libtss2-mu.so libtss2-tcti-device.so; do
    if ! grep -q "/${name}[.0-9]*\$" <<< "$listing"; then
        echo "the initramfs carries no ${name}, so a TPM2 answer cannot unlock this image" >&2
        exit 1
    fi
done

# bootc applies `/var` only once at provisioning, so the package state moves
# under `/usr` to travel with the image. The build backend mounts `/var/cache`
# outside the image layer, so `/var/cache/debconf` stays.
mkdir -p /usr/lib/sysimage
for pair in \
    dpkg:/var/lib/dpkg \
    pam:/var/lib/pam \
    ucf:/var/lib/ucf \
    sgml-base:/var/lib/sgml-base \
    xml-core:/var/lib/xml-core \
    deb-systemd-helper-enabled:/var/lib/systemd/deb-systemd-helper-enabled \
    deb-systemd-user-helper-enabled:/var/lib/systemd/deb-systemd-user-helper-enabled; do
    from="${pair#*:}"
    to="/usr/lib/sysimage/${pair%%:*}"
    [ -L "$from" ] && continue
    # Each link exists before a derived build installs its package.
    if [ -d "$from" ]; then mv "$from" "$to"; else mkdir -p "$to"; fi
    mkdir -p "$(dirname "$from")"
    ln -sfT "$to" "$from"
done
# A derived build layer runs no tmpfiles, so the links must hold in the image.
# dpkg reports a missing admindir as no packages and exits 0.
packages="$(dpkg-query -W -f '.' | wc -c)"
if [ "$packages" -eq 0 ]; then
    echo "the relocated dpkg admindir answers for no packages at all" >&2
    exit 1
fi
echo "dpkg answers for ${packages} packages from /usr/lib/sysimage/dpkg"

: > /etc/machine-id
# Package scripts leave directories under /run, and `bootc container lint`
# reports them. `secrets` and `.containerenv` are build mounts that `rm`
# cannot remove.
find /run -mindepth 1 -maxdepth 1 ! -name secrets ! -name .containerenv \
    -exec rm -rf {} +

# `login-access` creates the console account, so the `ubuntu` account goes.
if getent passwd ubuntu > /dev/null; then
    userdel ubuntu
fi
# The `L` tmpfiles rule for the D-Bus machine ID keeps an existing file at boot.
rm -f /var/lib/dbus/machine-id
rm -f /etc/ssh/ssh_host_*
# libmount warns at boot about the placeholder fstab.
rm -f /etc/fstab

# `login-access` decides ssh, so the postinst's enablement goes.
rm -f /etc/systemd/system/multi-user.target.wants/ssh.service

# If NetworkManager is installed, then networkd's Ethernet match goes, so one
# manager configures each link.
if [ -x /usr/sbin/NetworkManager ]; then
    rm -f /usr/lib/systemd/network/89-ethernet.network
fi

# Docker's `force-unsafe-io` apt policy risks package state on power loss.
rm -f /etc/dpkg/dpkg.cfg.d/docker-apt-speedup
rm -f /etc/apt/apt.conf.d/docker-clean \
    /etc/apt/apt.conf.d/docker-gzip-indexes \
    /etc/apt/apt.conf.d/docker-no-languages \
    /etc/apt/apt.conf.d/docker-autoremove-suggests

# The tool's own finalize relocates /opt, so this leaves it alone.
# shellcheck disable=SC2114
rm -rf /boot /home /root /srv /mnt
mkdir -p /boot /sysroot /var/home /var/srv /var/mnt /var/usrlocal /var/roothome
chmod 0700 /var/roothome
ln -sT var/home /home
ln -sT var/roothome /root
ln -sT var/srv /srv
ln -sT var/mnt /mnt
# The tool's own finalize moves the /usr/local content into /usr/lib/usrlocal.
# It then renames this link to /usr/local.
ln -sT ../var/usrlocal /usr/local.bak
ln -sT sysroot/ostree /ostree
