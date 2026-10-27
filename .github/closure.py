#!/usr/bin/env python3
"""Print the named components and everything they require, for one family.

An image that holds only a diff can fail on an unmet requirement, so the
closure adds a provider for each requirement. Run from the library root.

    closure.py <family> <base> <name>...
    closure.py --split <family> <base> <name>...

`--split` prints `<image> <component>` lines for the collection leg. Image 0
holds the named components with one provider of each capability. Each later
image holds alternative providers, closed over their requires.

A requirement that no component here provides is left alone. The base provides
some, such as `rechunking`. In the plain form, requirements print before the
component that needs them.

`create image` seeds the base component's requirements into every image, so the
closure covers them too. The base component declares a `base` reference that,
with its `version` default, matches `<base>` without its digest.

An entry for an imported component fails `tect check`, so no import is printed.
Its requirements are still closed over.

A `key` node provides `<kind>-key`. A component without `targets` targets every
family.
"""

import re
import sys
from pathlib import Path

COMPONENTS = Path("components")
LISTS = ("provides", "requires", "imports")
# A property and its value form one token.
# The reader never takes `witness="/usr/libexec/x"` as a name.
TOKEN = re.compile(
    r'//[^\n]*|[^\s{};"=]+=(?:"(?:[^"\\]|\\.)*"|[^\s{};]+)|"(?:[^"\\]|\\.)*"|[{};\n]|[^\s{};"]+'
)
BASE = re.compile(r'^base\s+"([^"]+)"', re.M)
# The base's reference reads the default of its `version` option.
VERSION = re.compile(r'^option\s+"version"[^{]*\{[^}]*?^\s*default\s+"([^"]*)"', re.M | re.S)


def nodes(text):
    """Yield each KDL node of a manifest as its enclosing nodes, its name and
    its string arguments. Each enclosing node is its name and its string
    arguments. A line that ends in a backslash continues on the next line."""
    text = re.sub(r"\\[ \t]*\n", " ", text)
    stack, current = [], None
    for token in TOKEN.findall(text):
        if token.startswith("//"):
            continue
        if token in ("\n", ";", "{", "}") and current:
            yield current
        if token == "{":
            stack.append((current[1], current[2]) if current else ("", []))
        elif token == "}" and stack:
            stack.pop()
        if token in ("\n", ";", "{", "}"):
            current = None
        elif current is None:
            current = (tuple(stack), token.strip('"'), [])
        elif token.startswith('"'):
            current[2].append(token[1:-1])
    if current:
        yield current


def declared(text, top):
    """Return the names each list node declares, by kind. A list node writes
    its names on its line or as the children of its block. If `top` is set,
    then a node inside an `on` gate is not counted."""
    out = {kind: [] for kind in LISTS}
    for parents, name, args in nodes(text):
        if name in LISTS and args and (not top or not parents):
            out[name] += args
        elif parents and parents[-1][0] in LISTS and (not top or len(parents) == 1):
            out[parents[-1][0]].append(name)
    return out


def is_base(text):
    return BASE.search(text) is not None


def base_needs(components, image):
    """Return the requirements and the imports of the one base component built
    from `image`."""
    wanted = image.split("@", 1)[0]
    matches = []
    for manifest in sorted(components.rglob("manifest.kdl")):
        text = manifest.read_text()
        found = BASE.search(text)
        if not found:
            continue
        version = VERSION.search(text)
        reference = found.group(1).replace("$version", version.group(1) if version else "")
        if reference != wanted:
            continue
        lists = declared(text, top=True)
        matches.append((manifest.parent, (lists["requires"], lists["imports"])))
    if not matches:
        sys.exit(f"closure.py: no base component under {components} builds from {wanted}")
    if len(matches) > 1:
        paths = ", ".join(str(directory) for directory, _ in matches)
        sys.exit(f"closure.py: {wanted} is the image of more than one base component: {paths}")
    return matches[0][1]


def targets(component, family):
    return not component[0] or family in component[0]


def read(path):
    text = path.read_text()
    targeted, provides = set(), set()
    for parents, name, args in nodes(text):
        if parents or not args:
            continue
        if name == "targets":
            targeted.update(args)
        elif name == "key":
            provides.add(args[0] + "-key")
    lists = declared(text, top=False)
    provides.update(lists["provides"])
    return targeted, provides, set(lists["requires"]), set(lists["imports"])


def imported(components, base_imports, names):
    """Return every component that the base or one of `names` imports,
    followed transitively."""
    out = set()
    todo = list(base_imports)
    for name in names:
        if name in components:
            todo.extend(components[name][3])
    while todo:
        path = todo.pop()
        if path in out or path not in components:
            continue
        out.add(path)
        todo.extend(components[path][3])
    return out


def split(components, family, names):
    """Split the named components into images that each hold one provider of
    anything. A component joins the first image that provides none of what it
    provides."""
    images = []
    for name in sorted(n for n in names if n in components and targets(components[n], family)):
        for members, held in images:
            if not components[name][1] & held:
                members.append(name)
                held.update(components[name][1])
                break
        else:
            images.append(([name], set(components[name][1])))
    groups = [members for members, _ in images] or [[]]
    # A component needing what only an alternative provides follows it out of the
    # first image. The later images are closed over their requires anyway.
    changed = True
    while changed:
        changed = False
        first = groups[0]
        held = set().union(*(components[m][1] for m in first))
        for name in list(first):
            wants = components[name][2] - held
            home = next((i for i, other in enumerate(groups[1:], 1)
                         if any(wants & components[m][1] for m in other)), None)
            if home is not None:
                first.remove(name)
                groups[home].append(name)
                changed = True
                break
    return groups


def main(argv):
    splitting = argv[1:2] == ["--split"]
    argv = [argv[0]] + argv[2:] if splitting else argv
    if len(argv) < 3:
        sys.exit(__doc__)
    family, base, wanted = argv[1], argv[2], argv[3:]

    components = {}
    for manifest in sorted(COMPONENTS.rglob("manifest.kdl")):
        name = manifest.parent.relative_to(COMPONENTS).as_posix()
        if any(part.startswith(".") for part in manifest.parts[:-1]):
            continue
        if is_base(manifest.read_text()):
            continue
        components[name] = read(manifest)
        # A component provides its own path, so a requirement can name it.
        components[name][1].add(name)

    needs = base_needs(COMPONENTS, base)
    if not splitting:
        for name in close(components, family, needs, wanted):
            print(name)
        return
    first, *rest = split(components, family, wanted)
    held = imported(components, needs[1], first)
    for name in first:
        if name not in held:
            print(f"0 {name}")
    for index, alternates in enumerate(rest, 1):
        for name in close(components, family, needs, alternates):
            print(f"{index} {name}")


def close(components, family, needs, wanted):
    seeded_by_row, base_imports = needs
    provider = {}
    for name in sorted(components):
        provides = components[name][1]
        if not targets(components[name], family):
            continue
        for capability in sorted(provides):
            provider.setdefault(capability, name)

    # A capability a named component provides is met by that component, so a diff
    # touching one of two providers never pulls in the other.
    for name in wanted:
        if name in components and targets(components[name], family):
            for capability in components[name][1]:
                provider[capability] = name

    order, seen, brought = [], set(), set()

    def bring(path):
        if path not in components:
            return
        brought.add(path)
        for capability in components[path][1]:
            provider[capability] = path
        visit(path)

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        for path in sorted(components[name][3]):
            bring(path)
        for capability in sorted(components[name][2]):
            needed = provider.get(capability)
            if needed and needed != name:
                visit(needed)
        order.append(name)

    for path in base_imports:
        bring(path)
    for capability in seeded_by_row:
        seeded = provider.get(capability)
        if seeded:
            visit(seeded)
    for name in wanted:
        if name in components and targets(components[name], family):
            visit(name)
    return [name for name in order if name not in brought]


if __name__ == "__main__":
    main(sys.argv)
