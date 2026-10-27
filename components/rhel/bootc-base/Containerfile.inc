# The Rocky base has neither. The label marks a bootc image, and the CMD
# lets `podman run` boot it.
LABEL containers.bootc=1
CMD ["/sbin/init"]

# Every component layer mounts /var/cache and /var/log as build caches. Only
# a layer without those mounts can remove what the base left there.
# `bootc container lint` reports it otherwise.
RUN rm -rf /var/cache/* /var/log/*
