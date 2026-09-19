import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1] / 'packages/fthr-clips-git/collect-uploader-licenses.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class LicenseTests(unittest.TestCase):
    def test_liblzma_component_evidence(self):
        header = '/* SPDX-License-Identifier: 0BSD */\nliblzma is distributed under the BSD Zero Clause License (0BSD).'
        expression = 'GPL-2.0-or-later AND 0BSD AND LicenseRef-Public-Domain AND LGPL-2.1-or-later'
        self.assertEqual(collector.component_expression('xz', ['liblzma.so.5'], expression, header), '0BSD')
        with self.assertRaises(RuntimeError):
            collector.component_expression('xz', ['xz'], expression, header)
        with self.assertRaises(RuntimeError):
            collector.component_expression('xz', ['liblzma.so.5'], expression, 'different license')
        self.assertEqual(collector.component_expression('zlib', ['libz.so.1'], 'Zlib'), 'Zlib')
