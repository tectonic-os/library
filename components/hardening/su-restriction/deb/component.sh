# Debian comments the line without `use_uid` and with other spacing. Its
# administrative group is `sudo`, and `wheel` is empty. A `wheel` rule would
# lock every user out of `su`.
sed -i 's/^#[[:space:]]*\(auth[[:space:]]\+required[[:space:]]\+pam_wheel\.so\)$/\1 use_uid group=sudo/' /etc/pam.d/su
grep -qE '^auth[[:space:]]+required[[:space:]]+pam_wheel\.so use_uid group=sudo$' /etc/pam.d/su
