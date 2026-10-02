<!-- The title is a typed subject, `<type>(<scope>): <description>`, of at most 64 characters. -->

## What this changes


## Acceptance

Each criterion is set out in [CONTRIBUTING.md](https://github.com/tectonic-os/modules/blob/main/CONTRIBUTING.md).

- [ ] Every input is an `asset` pinned to a `sha256` or a full commit.
- [ ] Every file's licence is known, and a file from elsewhere carries its own SPDX header.
- [ ] The scripts pass `shellcheck` and `shfmt` and follow the shell rules.
- [ ] `supports`, `provides` and `requires` are declared, and the module's tests pass.
- [ ] A `satisfies` claim sits under `hardening/` in a module that supports `rhel`.
- [ ] A script that fetches or installs through a package manager declares `network "scripts"`.
- [ ] Every commit is signed off with `git commit -s`.
