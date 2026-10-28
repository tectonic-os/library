# The Debian base has neither. The label marks a bootc image, and the CMD
# lets `podman run` boot it.
LABEL containers.bootc=1
CMD ["/sbin/init"]

# Every component layer mounts /var/cache and /var/log as build caches. Only
# a layer without those mounts can remove what the base left there.
# `bootc container lint` reports it otherwise.
RUN rm -rf /var/cache/* /var/log/*

# The Debian base sets `/etc/hostname` to `debuerreotype`. That name outranks
# the `DEFAULT_HOSTNAME` that the identity component writes into os-release.
# The file beside this one holds a single newline, so systemd falls back to
# `DEFAULT_HOSTNAME`.
#
# The build backend bind-mounts this path into every `RUN`, so only a `COPY`
# can replace it. Some buildah versions parse a heredoc's `EOF` as an
# instruction, so the file is copied from the component.
COPY --from=ctx @COMPONENT@/hostname /etc/hostname
