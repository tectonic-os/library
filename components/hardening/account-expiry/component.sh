# The base sets HOME=/var/home in this file, so this edits it in place.
sed -i '/^INACTIVE=/d' /etc/default/useradd
echo 'INACTIVE=30' >> /etc/default/useradd
