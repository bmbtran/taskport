import copy
import unittest
from taskport.core import Manifest, preflight, compare_traces, summarize, state_digest

STATE = {"labels": [{"id": "l1", "name": "Work"}], "emails": [{"id": "e1", "labels": ["l1"], "folder": "inbox"}]}

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.manifest = Manifest("benchmark-1", "gmail_mock", "pin-abc", state_digest(STATE), ("labels", "emails"), ("l1",), "browser", 1)

    def test_manifest_is_versioned_and_detects_changed_state(self):
        self.assertTrue(preflight(self.manifest, STATE, "pin-abc").ok)
        changed = copy.deepcopy(STATE)
        changed["labels"] = []
        result = preflight(self.manifest, changed, "pin-abc")
        self.assertFalse(result.ok)
        self.assertIn("missing_label:l1", result.reasons)
        self.assertIn("state_digest_mismatch", result.reasons)

    def test_version_mismatch_is_explicit(self):
        self.assertEqual(preflight(self.manifest, STATE, "other").reasons, ("environment_version_mismatch",))

    def test_trace_comparison_reports_first_divergence_without_claiming_cause(self):
        reference = [{"action":"open", "ok":True}, {"action":"star", "ok":True}]
        target = [{"action":"open", "ok":True}, {"action":"star", "ok":False}]
        result = compare_traces(reference, target)
        self.assertEqual(result["first_divergence"], 1)
        self.assertEqual(result["classification"], "action_divergence")

    def test_detection_metrics_count_false_positives_and_avoided_rollouts(self):
        trials = [{"fault":False,"blocked":False,"ran":True}, {"fault":True,"blocked":True,"ran":False}, {"fault":True,"blocked":False,"ran":True}, {"fault":False,"blocked":True,"ran":False}]
        result = summarize(trials)
        self.assertEqual(result["detection_recall"], .5)
        self.assertEqual(result["false_positive_rate"], .5)
        self.assertEqual(result["avoided_rollouts"], 1)

if __name__ == "__main__": unittest.main()

from taskport.benchmark import extract_initial_state, run_original_reward, inject_state, read_state
from pathlib import Path
import tempfile
import urllib.error
import subprocess
import time
import uuid

class BenchmarkAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.servers = []
        for directory, port in [(root / 'upstream-hub/websites/gmail_mock',5173),(root / 'external/gmail_target',5174)]:
            if not (directory / 'node_modules/vite/bin/vite.js').exists():
                raise unittest.SkipTest('install upstream Gmail mock dependencies first')
            process = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'], cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            cls.servers.append(process)
        import urllib.request
        for port in (5173,5174):
            for _ in range(60):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=.5).close()
                    break
                except Exception:
                    time.sleep(.1)
            else: raise RuntimeError(f'runtime {port} failed startup')

    @classmethod
    def tearDownClass(cls):
        for process in cls.servers:
            process.terminate()
            process.wait(timeout=5)

    def test_extract_state_from_upstream_without_running_setup_side_effects(self):
        source = 'import requests\nstate = {"emails": [{"id":"e1"}], "labels": []}\nraise RuntimeError("must not run")'
        self.assertEqual(extract_initial_state(source)["emails"][0]["id"], "e1")

    def test_reject_dynamic_setup_state(self):
        with self.assertRaises(ValueError):
            extract_initial_state('state = load_from_network()')

    def test_two_live_runtimes_have_independent_state_and_original_verifier(self):
        root = Path(__file__).resolve().parents[2]
        task = root / 'external/tasks/7966bc77-f7d9-5140-ac50-e41d3662baf2'
        if not task.exists(): self.skipTest('external benchmark archive not installed')
        state = extract_initial_state((task / 'initial_setup.py').read_text())
        sid = 'taskport-' + uuid.uuid4().hex
        inject_state('http://127.0.0.1:5173', sid, state)
        inject_state('http://127.0.0.1:5174', sid, state)
        changed = copy.deepcopy(state)
        changed['emails'][0]['labels'] = []
        inject_state('http://127.0.0.1:5174', sid, changed)
        self.assertNotEqual(read_state('http://127.0.0.1:5173', sid)['current_state'], read_state('http://127.0.0.1:5174', sid)['current_state'])
        with tempfile.TemporaryDirectory() as directory:
            result = run_original_reward(task / 'reward.py', 'http://127.0.0.1:5173', sid, Path(directory))
            self.assertEqual(result['score'], 0.0)
            self.assertIn('REWARD:',result['stdout'])
