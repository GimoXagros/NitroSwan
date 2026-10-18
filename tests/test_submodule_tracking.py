"""Dependabot must follow the branches carrying NitroSwan's custom fixes."""
from configparser import ConfigParser
from pathlib import Path
import unittest


class SubmoduleTrackingTests(unittest.TestCase):
    def test_custom_branches_are_explicit(self):
        config = ConfigParser()
        config.read(Path(__file__).resolve().parents[1] / '.gitmodules')
        branches = {
            'Shared': ('NDS_Shared', 'agent/nitroswan-shared-r3'),
            'ARMV30MZ': ('ARMV30MZ', 'agent/opcode-fetch-waitstate'),
            'Sphinx': ('Sphinx', 'fix/2bpp-bg-tile-offset'),
            'WSCart': ('WSCart', 'agent/nitroswan-dspico-rom-cache-r3'),
        }
        for name, (repository, branch) in branches.items():
            with self.subTest(module=name):
                module = config[f'submodule "source/{name}"']
                self.assertEqual(module['url'], f'https://github.com/GimoXagros/{repository}.git')
                self.assertEqual(module['branch'], branch)
