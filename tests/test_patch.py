import unittest
from taskport.repair import patch_archive

class RepairTests(unittest.TestCase):
    def test_changes_only_archive_transition(self):
        source="const archiveEmails = () => { emailIds.includes(e.id) ? { ...e, folder: 'all-mail' } : e }; const other = 'all-mail';"
        patched=patch_archive(source)
        self.assertIn("folder: 'archive'",patched)
        self.assertIn("const other = 'all-mail'",patched)
        self.assertEqual(patched.count("folder: 'archive'"),1)

    def test_fails_closed_if_upstream_code_moved(self):
        with self.assertRaises(ValueError):patch_archive('const archiveEmails = () => {}')
