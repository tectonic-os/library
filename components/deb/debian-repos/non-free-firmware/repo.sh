# `debian:forky` lists only `main` in `debian.sources`. The firmware is in
# `non-free-firmware` of the same signed archive, so no key is added.
# A second `.sources` file for the same suite makes apt warn on every update,
# so this edits the file in place.
sources=/etc/apt/sources.list.d/debian.sources
if [ ! -f "$sources" ]; then
    echo "no $sources: this base does not configure apt the way debian:forky does" >&2
    exit 1
fi
sed -i '/^Components:/ { /non-free-firmware/! s/$/ non-free-firmware/ }' "$sources"
grep -q 'non-free-firmware' "$sources"
