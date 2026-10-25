#!/bin/bash

source /ctx/lib/kernel-helpers.sh

# A module that replaces the image kernel records its kernel package and its
# headers package. If no module recorded a headers package, then the image runs
# the base Fedora kernel. kernel-devel-matched installs the headers for that
# kernel at build time.
KERNEL_DEVEL_PKG=kernel-devel-matched
KERNEL_DEVEL_REPO=()
if [ -f /usr/lib/kernel-build/kernel-devel-package ]; then
    KERNEL_DEVEL_PKG="$(cat /usr/lib/kernel-build/kernel-devel-package)"
elif [ -f /usr/lib/kernel-build/kernel-package ] \
    && [ "$(cat /usr/lib/kernel-build/kernel-package)" != kernel-core ]; then
    echo "/usr/lib/kernel-build/kernel-package names $(cat /usr/lib/kernel-build/kernel-package), but no module wrote /usr/lib/kernel-build/kernel-devel-package" >&2
    exit 1
fi
if [ -f /usr/lib/kernel-build/kernel-devel-repo ]; then
    KERNEL_DEVEL_REPO=(--enablerepo="$(cat /usr/lib/kernel-build/kernel-devel-repo)")
fi

# An unversioned headers package resolves to the newest kernel in the
# repository. If the image kernel is older, then dnf adds a second kernel to
# the image. The image kernel's version pins the headers to that kernel.
kernel_devel_install() {
    dnf5 -y install "${KERNEL_DEVEL_REPO[@]}" "${KERNEL_DEVEL_PKG}-$(kver)" "$@"
}

kernel_devel_remove() {
    dnf5 -y remove --noautoremove "$KERNEL_DEVEL_PKG" "$@"
}
