#!/usr/bin/env python3
"""Print `<component> <package>...` for every component declaring packages for one family.

The `packages` job dry-runs each line in a container of that family. One line
per component lets the job name the component whose package does not resolve.
Run from the library root.

    packages.py <family>
    packages.py <family> --repos

`--repos` prints every `repo.sh` this family would source instead. The job runs
them first, because a package from a third-party archive resolves only after
its archive is added. A component that declares no packages is listed too. It
can enable an archive section that other components install from.

Only components that target the family are read, as in the `collection` leg of
that family.
"""

import re
import sys
from pathlib import Path

from closure import nodes

COMPONENTS = Path("components")
QUOTED = re.compile(r'"([^"]*)"')


def lists(text, family):
    """Every package name one manifest installs on one family, in file order.

    Packages outside a gate apply to every family the component targets.
    Packages inside a gate apply only to the families it names. A `packages`
    node writes its names on its line or as the children of its block.
    """
    if not targets(text, family):
        return []
    names = []
    for parents, name, args in nodes(text):
        gates = [given for kind, given in parents if kind == "on"]
        if any(family not in gate for gate in gates):
            continue
        if name == "packages" and args:
            names += args
        elif parents and parents[-1][0] == "packages":
            names.append(name)
    return names


def targets(text, family):
    """Whether a manifest builds on `family`. No `targets` is every family."""
    lines = re.findall(r'^targets\s(.*)$', text, re.M)
    return not lines or any(family in QUOTED.findall(line) for line in lines)


# `FAMILY_DIRS` lists the most specific directory first and the component root
# last, in the order that the tool's `layout::family_first` walks. The first
# `repo.sh` found is the only one used.
FAMILY_DIRS = {
    "debian": ["debian/", "deb/", ""],
    "ubuntu": ["ubuntu/", "deb/", ""],
    "fedora": ["fedora/", ""],
}


def repo(component, family):
    """The `repo.sh` this component ships for this family, if it ships one."""
    for at in FAMILY_DIRS.get(family, [""]):
        found = component / at / "repo.sh"
        if found.is_file():
            return found
    return None


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--repos"):
        sys.exit(__doc__)
    family, repos = argv[1], len(argv) == 3
    for manifest in sorted(COMPONENTS.rglob("manifest.kdl")):
        if any(part.startswith(".") for part in manifest.parts[:-1]):
            continue
        text = manifest.read_text()
        if not targets(text, family):
            continue
        if repos:
            found = repo(manifest.parent, family)
            if found:
                print(found.as_posix())
            continue
        names = lists(text, family)
        if names:
            print(manifest.parent.relative_to(COMPONENTS).as_posix(), *names)


if __name__ == "__main__":
    main(sys.argv)
