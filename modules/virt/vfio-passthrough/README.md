# vfio-passthrough

VFIO GPU-passthrough host setup: the `iommu=pt` kernel argument. Pairs with
the [looking-glass](../looking-glass) kvmfr module.

## Driver binding moved to libvirt

This module used to bind the GPU's PCI IDs to `vfio-pci` from boot: a
kernel argument pre-loading the driver, modprobe ids and softdeps, a
dracut `force_drivers` entry, and a service rebinding the card's USB
controller before libvirtd. That is incompatible with
[virtio-nvgpu](../virtio-nvgpu), which needs the host NVIDIA driver to
own the card, so the binding is now per VM.

Define passthrough devices as libvirt hostdev entries with
`managed='yes'`: libvirt detaches each function from its host driver when
the domain starts and gives it back when it stops. `vfio-pci` is loaded
on demand by that path and needs no boot-time configuration of its own.
Stop the card's virtio-nvgpu guests before starting a passthrough
domain, or the detach has nothing to detach.

## Files

- `kargs.d/00-vfio.toml` -- `iommu=pt` only; the vfio driver binding was
  removed, see above.
