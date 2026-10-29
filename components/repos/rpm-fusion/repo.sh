dnf5 install -y \
    "https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
    "https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm"
dnf5 config-manager setopt rpmfusion-free.priority=90
dnf5 config-manager setopt rpmfusion-free-updates.priority=90
dnf5 config-manager setopt rpmfusion-nonfree.priority=90
dnf5 config-manager setopt rpmfusion-nonfree-updates.priority=90
