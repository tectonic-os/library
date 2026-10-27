# This is a hook because the overlay that holds the PAM profiles is copied
# after `component.sh` runs.
#
# No deb package adds pam_faillock to the PAM stack. pam_faillock needs an
# entry above pam_unix, one below it and one that clears the tally after a
# good login. Each entry is its own profile.
pam-auth-update --package
grep -q 'pam_faillock.so preauth' /etc/pam.d/common-auth
grep -q 'pam_faillock.so authfail' /etc/pam.d/common-auth
grep -q 'pam_faillock.so authsucc' /etc/pam.d/common-auth
grep -q 'pam_faillock.so' /etc/pam.d/common-account
grep -q 'pam_pwquality.so' /etc/pam.d/common-password

# `dictcheck = 1` fails every password change without a cracklib dictionary.
# The deb default path `/var/cache/cracklib` is a build cache during the image
# build, so the dictionary goes into `/usr` and `dictpath` points at it.
install -d /usr/share/cracklib
create-cracklib-dict -o /usr/share/cracklib/pw_dict /usr/share/dict/cracklib-small
printf 'dictpath = /usr/share/cracklib/pw_dict\n' >> /etc/security/pwquality.conf
