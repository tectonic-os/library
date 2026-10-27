import unittest

from packages import lists

MANIFEST = """schema-version 1
packages "htop"
packages enablerepo="secureblue" {
    "trivalent"
    "trivalent-qt6-ui"
}
on "fedora" {
    packages {
        "dnf-plugins-core"
    }
}
on "debian" "ubuntu" { packages "apt-utils"; }
"""


class Lists(unittest.TestCase):
    def test_a_block_lists_its_names_and_drops_the_batch_property(self):
        self.assertEqual(
            lists(MANIFEST, "fedora"),
            ["htop", "trivalent", "trivalent-qt6-ui", "dnf-plugins-core"],
        )

    def test_a_gate_keeps_only_the_families_it_names(self):
        self.assertEqual(
            lists(MANIFEST, "debian"),
            ["htop", "trivalent", "trivalent-qt6-ui", "apt-utils"],
        )


if __name__ == "__main__":
    unittest.main()
