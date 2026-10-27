# authselect manages this file, so this uncomments the line in place.
sed -i 's/^#\(auth[[:space:]]*required[[:space:]]*pam_wheel\.so use_uid\)$/\1/' /etc/pam.d/su
grep -qE '^auth[[:space:]]+required[[:space:]]+pam_wheel\.so use_uid$' /etc/pam.d/su
