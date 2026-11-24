"""End-to-end upstream reward tests. Requires bootstrap of upstream sources."""
import copy
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid
from taskport.benchmark import extract_initial_state, inject_state, run_original_reward, read_state
from taskport.experiment import execute_reference, make_manifest, trial

ROOT = Path(__file__).resolve().parents[1] / '.cache'
TASKS = ('378d436a-433a-51f8-a13f-92ecf1415e9f', '2c49ae92-7006-5de3-a938-b3c2af582948', '6ae03946-3ada-5a5e-a526-e3283ac528d2')

class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servers=[]
        for path, port in [(ROOT/'upstream-hub/websites/gmail_mock',5173),(ROOT/'external/gmail_target',5174)]:
            if not (path/'node_modules/vite/bin/vite.js').exists(): raise unittest.SkipTest('bootstrap upstream mock first')
            cls.servers.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=path,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        from urllib.request import urlopen
        for port in (5173,5174):
            for i in range(60):
                try: urlopen(f'http://127.0.0.1:{port}',timeout=.4).close(); break
                except Exception: time.sleep(.1)
            else: raise RuntimeError(f'port {port} unavailable')

    @classmethod
    def tearDownClass(cls):
        for p in cls.servers: p.terminate(); p.wait(timeout=5)

    def test_three_upstream_tasks_reach_full_reward_on_both_runtimes(self):
        for task_id in TASKS:
            task_dir=ROOT/'external/tasks'/task_id
            state=extract_initial_state((task_dir/'initial_setup.py').read_text())
            manifest=make_manifest(task_id,state)
            for port in (5173,5174):
                with self.subTest(task=task_id,port=port), tempfile.TemporaryDirectory() as temp:
                    base=f'http://127.0.0.1:{port}'
                    sid=uuid.uuid4().hex
                    inject_state(base,sid,state)
                    baseline=run_original_reward(task_dir/'reward.py',base,sid,Path(temp)/'baseline')['score']
                    result=trial(manifest,base,sid,task_dir/'reward.py',Path(temp)/'trial')
                    self.assertTrue(result['preflight']['ok'])
                    self.assertLess(baseline,1.0)
                    self.assertEqual(result['reward'],1.0, result)
                    self.assertTrue(result['trace'])

    def test_preflight_blocks_drift_then_repair_revalidates(self):
        task_id=TASKS[1]
        task_dir=ROOT/'external/tasks'/task_id
        state=extract_initial_state((task_dir/'initial_setup.py').read_text())
        manifest=make_manifest(task_id,state)
        damaged=copy.deepcopy(state)
        damaged['labels']=[label for label in damaged['labels'] if label['id']!='l1']
        sid=uuid.uuid4().hex
        base='http://127.0.0.1:5174'
        inject_state(base,sid,damaged)
        with tempfile.TemporaryDirectory() as temp:
            blocked=trial(manifest,base,sid,task_dir/'reward.py',Path(temp)/'blocked')
            self.assertIsNone(blocked['reward'])
            self.assertIn('missing_label:l1',blocked['preflight']['reasons'])
            self.assertEqual(blocked['trace'],[])
            repaired_sid=uuid.uuid4().hex
            inject_state(base,repaired_sid,state)
            repaired=trial(manifest,base,repaired_sid,task_dir/'reward.py',Path(temp)/'repaired')
            self.assertEqual(repaired['reward'],1.0)

    def test_repeated_controlled_trials_are_reproducible_and_metrics_are_auditable(self):
        from taskport.experiment import run_suite
        with tempfile.TemporaryDirectory() as temp:
            report=run_suite(ROOT/'external/tasks',Path(temp),repeats=2,ports=(5173,5174))
            self.assertEqual(report['clean']['n'],12)
            self.assertEqual(report['clean']['full_reward'],12)
            self.assertEqual(report['faults']['n'],12)
            self.assertEqual(report['faults']['detection_recall'],1.0)
            self.assertAlmostEqual(report['faults']['false_positive_rate'],1/3)
            self.assertEqual(report['faults']['benign_blocks'],6)
            self.assertEqual(report['faults']['benign_counterfactual_successes'],6)
            self.assertEqual(report['faults']['avoided_rollouts'],12)
            self.assertEqual(report['repairs']['successful'],6)
            self.assertEqual(report['faults']['counterfactual_failures'],12)
            self.assertEqual(report['faults']['traces_with_divergence'],12)
            self.assertTrue((Path(temp)/'report.json').exists())
            self.assertTrue((Path(temp)/'trials.jsonl').exists())
