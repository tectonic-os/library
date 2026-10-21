# The nvidia module adds NVIDIA's repository with its pinned key.
REPO_ID="cuda-fedora$(rpm -E %fedora)-x86_64"

toolkit=cuda-toolkit
if [ "$OPT_VERSION" != latest ]; then
    toolkit="cuda-toolkit-${OPT_VERSION//./-}"
fi
# The `cuda` metapackage also installs NVIDIA's driver packages.
# The nvidia module already installs the driver at the release its `version`
# option selects.
# This layer installs the toolkit package alone.
dnf5 install -y --enablerepo="$REPO_ID" --setopt=install_weak_deps=False "$toolkit"
