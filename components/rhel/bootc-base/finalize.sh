# This runs after every component's packages, so the initramfs holds them all.

# ---- the initramfs ----
# The EL kernel package already puts vmlinuz where bootc looks for it.
mapfile -t kvers < <(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
if [ "${#kvers[@]}" -ne 1 ]; then
    echo "bootc wants exactly one kernel; /usr/lib/modules has: ${kvers[*]}" >&2
    exit 1
fi
kver="${kvers[0]}"
[ -f "/usr/lib/modules/${kver}/vmlinuz" ] || {
    echo "the kernel package left no /usr/lib/modules/${kver}/vmlinuz" >&2
    exit 1
}
depmod "$kver"
initramfs="/usr/lib/modules/${kver}/initramfs.img"
dracut --force --kver "$kver" "$initramfs"

# dracut exits 0 when a module is missing, so this checks for the files that
# mount the deployment.
listing="$(lsinitrd "$initramfs")"
for path in usr/lib/ostree/ostree-prepare-root \
    usr/lib/bootc/initramfs-setup; do
    if ! grep -q "[ /]${path}\$" <<< "$listing"; then
        echo "the initramfs carries no ${path}, so it cannot mount a deployment" >&2
        exit 1
    fi
done

# ---- what a build must not bake in ----
: > /etc/machine-id
# Package scripts leave directories under /run, and `bootc container lint`
# reports them. `secrets` and `.containerenv` are build mounts that `rm`
# cannot remove.
find /run -mindepth 1 -maxdepth 1 ! -name secrets ! -name .containerenv \
    -exec rm -rf {} +
rm -f /etc/ssh/ssh_host_*
# libmount warns at boot about the placeholder fstab.
rm -f /etc/fstab

# ---- the bootloader payload ----
# bootupd generates its update payload from /usr/lib/ostree-boot. The shim
# and GRUB packages unpack under /boot/efi, so that directory moves there.
mkdir -p /usr/lib/ostree-boot
mv /boot/efi /usr/lib/ostree-boot/efi
bootupctl backend generate-update-metadata

# ---- the ostree-shaped root ----
# This matches the layout of `centos-bootc:stream10`. The tool's own finalize
# relocates /opt. `bootc install` fills /boot, and `bootc container lint`
# warns about the kernel files that the package leaves there.
# shellcheck disable=SC2114 # replacing the system directories is the point
rm -rf /home /root /srv /mnt /boot
mkdir -p /boot /sysroot /var/home /var/srv /var/mnt /var/roothome
chmod 0700 /var/roothome
ln -sT var/home /home
ln -sT var/roothome /root
ln -sT var/srv /srv
ln -sT var/mnt /mnt
ln -sT sysroot/ostree /ostree
