"""Browser-level verifier; enabled in CI's browser-capable runner."""
import os
import json
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
        cls.results=[]
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
        out=Path('experiments/browser_ci')
        out.mkdir(parents=True,exist_ok=True)
        records=cls.results
        report={'interface':'browser','repeats':3,'runs':len(records),
                'unpatched_full_rewards':sum(r['reward']==1.0 for r in records if r['port'] in (5173,5174)),
                'unpatched_runs':sum(r['port'] in (5173,5174) for r in records),
                'archive_failures':sum(r['reward']<1.0 for r in records if r['task_id']=='2c49ae92-7006-5de3-a938-b3c2af582948' and r['port'] in (5173,5174)),
                'patched_archive_successes':sum(r['reward']==1.0 for r in records if r['port']==5175)}
        (out/'report.json').write_text(json.dumps(report,indent=2))
        (out/'trials.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))

    def test_ui_actions_satisfy_original_rewards_on_both_runtimes(self):
        for task_id in TASK_LABELS:
            task=ROOT/'external/tasks'/task_id
            state=extract_initial_state((task/'initial_setup.py').read_text())
            for repetition in range(3):
                for port in (5173,5174):
                    with self.subTest(task=task_id,repetition=repetition,port=port),tempfile.TemporaryDirectory() as temp:
                        url=f'http://127.0.0.1:{port}'
                        sid=uuid.uuid4().hex
                        inject_state(url,sid,state)
                        outcome=browser_trial(replace(make_manifest(task_id,state),permitted_interface='browser'),url,sid,task/'reward.py',Path(temp))
                        self.__class__.results.append({'task_id':task_id,'repetition':repetition,'port':port,'reward':outcome['reward'],'trace_length':len(outcome['trace']),'final_emails':outcome['final_emails']})
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
        manifest=replace(make_manifest(task_id,state),environment_pin=PATCH_PIN,permitted_interface='browser')
        for repetition in range(3):
            with self.subTest(repetition=repetition),tempfile.TemporaryDirectory() as temp:
                sid=uuid.uuid4().hex
                inject_state(base,sid,state)
                outcome=browser_trial(manifest,base,sid,task/'reward.py',Path(temp),runtime_pin=PATCH_PIN)
                self.__class__.results.append({'task_id':task_id,'repetition':repetition,'port':5175,'reward':outcome['reward'],'trace_length':len(outcome['trace']),'final_emails':outcome['final_emails']})
                self.assertEqual(outcome['reward'],1.0,outcome)
                self.assertTrue(all(e['folder']=='archive' for e in outcome['final_emails'] if e['subject']!='Lunch tomorrow?'))

if __name__=='__main__':unittest.main()
