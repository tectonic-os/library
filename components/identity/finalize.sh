# The finalize layer passes the image file's values as IMAGE_* variables.
# The upstream image's own os-release names the upstream distribution.
identity_os_release() {
    local file=/usr/lib/os-release
    local link=/etc/os-release
    local version="${IMAGE_VERSION:-dev}"
    local -A set=(
        [NAME]="${IMAGE_NAME:?identity: IMAGE_NAME is unset, so image.kdl declares no name}"
        [DEFAULT_HOSTNAME]="${IMAGE_ID:?identity: IMAGE_ID is unset in the finalize layer}"
        [PRETTY_NAME]="${IMAGE_PRETTY_NAME:-${IMAGE_NAME} ${version}}"
        [IMAGE_VERSION]="${version}"
    )
    local -a keys=(NAME DEFAULT_HOSTNAME PRETTY_NAME IMAGE_VERSION)
    if [ -n "${IMAGE_URL:-}" ]; then
        set[HOME_URL]="${IMAGE_URL}"
        set[DOCUMENTATION_URL]="${IMAGE_URL}"
        keys+=(HOME_URL DOCUMENTATION_URL)
    fi
    if [ -n "${IMAGE_ISSUES_URL:-}" ]; then
        set[SUPPORT_URL]="${IMAGE_ISSUES_URL}"
        set[BUG_REPORT_URL]="${IMAGE_ISSUES_URL}"
        keys+=(SUPPORT_URL BUG_REPORT_URL)
    fi

    local key value line text out=""
    for key in "${keys[@]}"; do
        # os-release quotes a value as a shell string does.
        value="${set[$key]//\\/\\\\}"
        value="${value//\"/\\\"}"
        value="${value//\$/\\\$}"
        value="${value//\`/\\\`}"
        set[$key]="\"${value}\""
    done
    text="$(< "${file}")"
    local -A found=()
    while IFS= read -r line; do
        key="${line%%=*}"
        if [ "${key}" != "${line}" ] && [ -n "${set[$key]+x}" ]; then
            out+="${key}=${set[$key]}"$'\n'
            found[$key]=1
        else
            out+="${line}"$'\n'
        fi
    done <<< "${text}"
    for key in "${keys[@]}"; do
        if [ -z "${found[$key]+x}" ]; then
            out+="${key}=${set[$key]}"$'\n'
        fi
    done

    # The upstream file can be a symlink into os.release.d, as on Fedora.
    # An overlay store on btrfs pads a rewritten file with NULs from the layer
    # below, so the hook writes a fresh file in its place.
    rm -f "${file}"
    printf '%s' "${out}" > "${file}"
    ln -sfn ../usr/lib/os-release "${link}"
}

identity_os_release
