from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_template_review_registry import build_registry, classify


class RegistryArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous = Path.cwd()
        self.addCleanup(os.chdir, self.previous)
        os.chdir(self.temp.name)
        self.git('init', '-q')
        self.path = 'synthetic-form.pdf'
        self.data = b'Not a real official PDF; synthetic Git archive fixture only.\n'
        Path(self.path).write_bytes(self.data)
        self.git('add', '--', self.path)
        self.git('-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        self.commit = self.git('rev-parse', 'HEAD').strip()
        self.blob = self.git('rev-parse', f'HEAD:{self.path}').strip()
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.inventory = {
            'refs': {'refs/heads/main': self.commit},
            'files': [{'ref': 'refs/heads/main', 'commit': self.commit, 'path': self.path,
                       'candidate': True, 'sha256': self.digest, 'git_blob': self.blob,
                       'size': len(self.data), 'mode': '100644'}],
            'auditor_commit': self.commit,
        }
        self.output = Path('evidence')

    def git(self, *args):
        return subprocess.check_output(['git', *args], stderr=subprocess.STDOUT, timeout=20).decode()

    def test_archives_real_git_bytes_without_official_acceptance(self):
        result = build_registry(self.inventory, self.output)
        self.assertEqual((self.output / 'blobs' / self.digest).read_bytes(), self.data)
        self.assertFalse(result['records'][0]['legal_acceptance'])
        self.assertFalse(result['records'][0]['pixel_acceptance'])
        self.assertIsNone(result['records'][0]['official_source_url'])

    def test_deduplicates_content_preserving_all_ref_origins(self):
        other = copy.deepcopy(self.inventory['files'][0])
        other['ref'] = 'refs/heads/backup-before-merge'
        self.inventory['refs'][other['ref']] = self.commit
        self.inventory['files'].append(other)
        result = build_registry(self.inventory, self.output)
        self.assertEqual(result['unique_archived_blobs'], 1)
        self.assertEqual(len(result['records'][0]['origins']), 2)

    def test_wrong_hash_removes_only_new_output(self):
        self.inventory['files'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash verification'):
            build_registry(self.inventory, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(Path(self.path).read_bytes(), self.data)

    def test_wrong_git_provenance_is_rejected(self):
        self.inventory['files'][0]['git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'recorded commit/path'):
            build_registry(self.inventory, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_evidence_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'
        marker.write_text('retained')
        with self.assertRaisesRegex(ValueError, 'never overwritten'):
            build_registry(self.inventory, self.output)
        self.assertEqual(marker.read_text(), 'retained')

    def test_size_bound_fails_closed(self):
        with patch('build_template_review_registry.MAX_ARCHIVE_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'bounded size'):
                build_registry(self.inventory, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_ref_coverage_is_rejected(self):
        self.inventory['refs']['refs/tags/v-synthetic'] = self.commit
        with self.assertRaisesRegex(ValueError, 'no indexed entries'):
            build_registry(self.inventory, self.output)

    def test_symlink_classification_never_claims_document(self):
        self.assertEqual(classify('official.pdf', '120000'), 'symlink_not_a_verified_document')


if __name__ == '__main__':
    unittest.main()
