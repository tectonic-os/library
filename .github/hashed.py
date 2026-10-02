#!/usr/bin/env python3
"""Fail when an asset pin in a module.kdl carries no hash.

Usage: hashed.py <module.kdl>...

A pin is hashed when it carries a sha256, or when its version is a full git
commit, which names the content the way a hash does.
"""

import re
import sys
from pathlib import Path

from pins import pins

COMMIT = re.compile(r"[0-9a-f]{40}")


NAME = re.compile(r'^\s*asset\s+"([^"]+)"', re.MULTILINE)


def unhashed(text):
    fields = dict(pins(text))

    # pins() reads one field per line, so an asset it read no `url` from is
    # reported rather than passed.
    def hashed(name):
        prefix = f"ASSET_{name.upper().replace('-', '_')}"
        return f"{prefix}_URL" in fields and (
            f"{prefix}_SHA256" in fields
            or COMMIT.fullmatch(fields.get(f"{prefix}_VERSION", ""))
        )

    return sorted(name for name in set(NAME.findall(text)) if not hashed(name))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    found = [
        f'{path}: asset "{asset}" carries no sha256 and no commit that this check can read'
        for path in argv[1:]
        for asset in unhashed(Path(path).read_text())
    ]
    if found:
        print("\n".join(found), file=sys.stderr)
        sys.exit("hashed.py: pin each asset above to a sha256 or a full commit")


if __name__ == "__main__":
    main(sys.argv)
