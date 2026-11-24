"""Browser-level verifier; enabled in CI's browser-capable runner."""
import os
from pathlib import Path
from dataclasses import replace
import subprocess
import tempfile
import time
import unittest
import uuid
from urllib.request import urlopen
from taskport.benchmark import extract_initial_state,inject_state
from taskport.experiment import make_manifest,TASK_LABELS
from taskport.browser import browser_trial
from taskport.repair import PATCH_PIN

ROOT=Path(__file__).resolve().parents[1]/'.cache'

@unittest.skipUnless(os.environ.get('TASKPORT_BROWSER')=='1','browser not available in this sandbox')
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servers=[]
        for path,port in [(ROOT/'upstream-hub/websites/gmail_mock',5173),(ROOT/'external/gmail_target',5174),(ROOT/'external/gmail_repaired',5175)]:
            cls.servers.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=path,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for port in (5173,5174,5175):
            for attempt in range(80):
                try:urlopen(f'http://127.0.0.1:{port}/',timeout=.3).close();break
                except Exception:time.sleep(.1)
            else:raise RuntimeError(f'runtime {port} did not start')

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:server.terminate();server.wait(timeout=5)

    def test_ui_actions_satisfy_original_rewards_on_both_runtimes(self):
        for task_id in TASK_LABELS:
            task=ROOT/'external/tasks'/task_id
            state=extract_initial_state((task/'initial_setup.py').read_text())
            for port in (5173,5174,5175):
                with self.subTest(task=task_id,port=port),tempfile.TemporaryDirectory() as temp:
                    url=f'http://127.0.0.1:{port}'
                    sid=uuid.uuid4().hex
                    inject_state(url,sid,state)
                    outcome=browser_trial(make_manifest(task_id,state),url,sid,task/'reward.py',Path(temp))
                    self.assertEqual(outcome['reward'],0.1 if task_id=='2c49ae92-7006-5de3-a938-b3c2af582948' else 1.0,outcome)
                    if task_id=='2c49ae92-7006-5de3-a938-b3c2af582948':
                        self.assertTrue(all(e['folder']=='all-mail' for e in outcome['final_emails'] if e['subject']!='Lunch tomorrow?'))
                    self.assertGreater(len(outcome['trace']),0)
                    self.assertEqual(outcome['interface'],'browser')

    def test_patched_runtime_repairs_archive_reward_mismatch(self):
        task_id='2c49ae92-7006-5de3-a938-b3c2af582948'
        task=ROOT/'external/tasks'/task_id
        state=extract_initial_state((task/'initial_setup.py').read_text())
        base='http://127.0.0.1:5175'
        sid=uuid.uuid4().hex
        inject_state(base,sid,state)
        with tempfile.TemporaryDirectory() as temp:
            manifest=replace(make_manifest(task_id,state),environment_pin=PATCH_PIN)
            outcome=browser_trial(manifest,base,sid,task/'reward.py',Path(temp),runtime_pin=PATCH_PIN)
            self.assertEqual(outcome['reward'],1.0,outcome)
            self.assertTrue(all(e['folder']=='archive' for e in outcome['final_emails'] if e['subject']!='Lunch tomorrow?'))

if __name__=='__main__':unittest.main()
