import tempfile
import unittest
from pathlib import Path
from taskport.cli import attest_runtimes

class AttestationTests(unittest.TestCase):
    def test_rejects_changed_target_app_config(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            ref=base/'ref';target=base/'target'
            ref.mkdir();target.mkdir()
            (ref/'vite.config.js').write_text('reference')
            (target/'vite.config.js').write_text('different')
            with self.assertRaisesRegex(ValueError,'runtime source mismatch'):
                attest_runtimes(ref,target,check_upstream_commit=False)

if __name__=='__main__':unittest.main()
