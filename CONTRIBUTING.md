# Contributing to the module collection

This guide adds the collection's acceptance criteria to the
[organisation's contributing guide](https://github.com/tectonic-os/.github/blob/main/CONTRIBUTING.md),
which sets the pull request title, the squash merge and the
[AI use policy](https://github.com/tectonic-os/.github/blob/main/AI_POLICY.md).
Every image that imports a module runs its scripts as root at build time, so
the collection accepts a module only when it meets every criterion below. A
maintainer reviews every pull request, and `CODEOWNERS` requires that review
on every path.

## A module is accepted when

1. **Every input is pinned and hashed.** A download is an `asset` whose `pin`
   carries a `sha256`, or a `version` that is a full git commit. A script
   fetches only what an `asset` declares, reads it from the `ASSET_*`
   variables, and never pipes a download into a shell. `fetch_verified` and
   `fetch_extract`, which `tect` provides in `/ctx/lib/fetch-helpers.sh`,
   check the hash and fail the layer on a mismatch. CI fails a pin that carries neither a `sha256` nor a
   commit.
2. **The licence of every file is known.** The collection is Apache-2.0, and
   `REUSE.toml` gives that licence to every file that states none. A file
   whose content came from elsewhere states its own copyright and licence in
   an SPDX header, and its licence text goes in `LICENSES/`. CI runs
   `reuse lint`.
3. **Its scripts pass the collection's lint and follow the shell rules
   below.** CI runs `shellcheck -s bash` and `shfmt -i 4 -ci -bn -sr` on every
   script and `ruff check` on every Python file.
4. **It declares its families and capabilities, and its tests pass.**
   `supports` names the base families the module builds on, and `provides`
   and `requires` name the capabilities it offers and needs. On a pull
   request, CI imports every changed module, with what it requires, on
   Fedora, Debian and Ubuntu. The few modules that the `SKIP` list in
   `build.yml` names cannot build in isolation, so a maintainer checks them
   by hand. It resolves every declared package name on
   Debian and Ubuntu, and it runs the `test_*.py` beside each module it
   imports with `python3 -m unittest discover -s <module directory>`.
5. **A SCAP claim carries its evidence.** A module that declares `satisfies`
   sits under `hardening/` and supports `rhel`. On a pull request, CI refuses
   a claim in a module the hardening leg does not import. On every push to
   `main` and on the weekly build, the hardening leg builds that set on
   CentOS Stream 10, scans the booted image, and fails when a claimed rule
   does not pass.
6. **It reaches the network only where it declares it.** The collection
   builds under `security-policy { network "strict" }`. A package step,
   which installs what `packages`, `package-groups`, `copr` and a `repo` file
   declare, keeps the network. A module whose `module.sh` or `finalize.sh` fetches an asset or
   installs through a package manager declares `network "scripts"`. A
   removal works offline and needs no declaration. Every other script step
   runs with no network. `tect check` names most modules that need the
   declaration, and the build fails on the rest.
7. **Every commit is signed off** under the
   [Developer Certificate of Origin](https://developercertificate.org/) with
   `git commit -s`. CI checks that each commit carries a `Signed-off-by` for
   its own author. A merge commit is exempt, because GitHub's "Update branch"
   writes one without a sign-off, so resolve a conflict in a signed commit of
   its own.

## Shell rules

The lint cannot check these, so the review does.

- `module.sh` and `finalize.sh` carry no shebang and no `set`. The generated
  layer runs them under `set -euxo pipefail`, and an option a script changes
  reaches every script after it in that layer.
- An assertion is an `if`. A bare `! command` is exempt from errexit, so a
  broken command reads as a passing check.
- A `sed -i` on a file the base owns is followed by a `grep -q` for the
  result, because a `sed` that matches nothing exits 0.
- `|| true` and `2> /dev/null` appear only where the failure is the expected
  answer, with a comment that says why.
- Every expansion is quoted, and an argument list is an array passed as
  `"${args[@]}"`.
- A tool is detected with `command -v`.
- An error goes to stderr, names the path, command or value the user must
  act on, and exits non-zero.
- A helper that `tect` provides under `/ctx/lib/`, or one in the family's
  `build-environment/lib/`, comes before a new one.

## Pull requests from forks

A pull request from a fork runs its module scripts in CI with a read-only
token and no secrets. The workflows run on `pull_request`, and none runs on
`pull_request_target`, `workflow_run` or `issue_comment`. CI fails if a
workflow names one of those events, or if a workflow that a pull request
starts names a secret or grants a write permission. That check runs from the
pull request's own tree, so a maintainer's review of every change under
`.github/` is what holds it.
