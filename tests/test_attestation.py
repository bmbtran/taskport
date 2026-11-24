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

    def test_browser_runner_requires_browser_manifest(self):
        from taskport.core import Manifest
        from taskport.browser import browser_trial
        manifest=Manifest('t','gmail_mock','pin','digest',(),(),'state_api')
        with self.assertRaisesRegex(ValueError,'browser interface'):
            browser_trial(manifest,'http://localhost:1','sid','reward.py','/tmp/taskport-invalid-contract')

    def test_state_runner_requires_state_api_manifest(self):
        from taskport.core import Manifest
        from taskport.experiment import trial
        manifest=Manifest('t','gmail_mock','pin','digest',(),(),'browser')
        with self.assertRaisesRegex(ValueError,'state_api interface'):
            trial(manifest,'http://localhost:1','sid','reward.py','/tmp/taskport-invalid-contract')

if __name__=='__main__':unittest.main()
