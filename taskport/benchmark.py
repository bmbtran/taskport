"""Read upstream tasks without executing setup code; call original reward in a trial sandbox."""
import ast
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen


def extract_initial_state(source):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'state' for t in node.targets):
            try:
                result = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
                raise ValueError('dynamic initial state is unsupported') from exc
            if not isinstance(result, dict):
                raise ValueError('state must be a dict')
            return result
    raise ValueError('no literal initial state assignment')


def inject_state(base_url, sid, state):
    request = Request(f'{base_url}/post?sid={sid}', data=json.dumps({'action':'set', 'state':state}).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urlopen(request, timeout=15) as response:
        if response.status != 200: raise RuntimeError(f'injection failed: {response.status}')


def read_state(base_url, sid):
    with urlopen(f'{base_url}/go?sid={sid}', timeout=15) as response:
        return json.load(response)


def run_original_reward(reward_path, base_url, sid, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'sid').write_text(sid)
    source = Path(reward_path).read_text()
    if '__CUA_GYM_GMAIL_URL__' not in source or '/tmp/task_web_sid' not in source:
        raise ValueError('unsupported upstream verifier interface')
    source = source.replace('__CUA_GYM_GMAIL_URL__', base_url).replace('/tmp/task_web_sid', str(directory / 'sid'))
    (directory / 'reward.py').write_text(source)
    run = subprocess.run([sys.executable, str(directory / 'reward.py')], cwd=directory, capture_output=True, text=True, timeout=30)
    matches = re.findall(r'REWARD:\s*([0-9]+(?:\.[0-9]+)?)', run.stdout)
    if run.returncode != 0 or not matches:
        raise RuntimeError(f'upstream verifier failed: exit={run.returncode}, stdout={run.stdout[-500:]}, stderr={run.stderr[-500:]}')
    return {'score':float(matches[-1]),'stdout':run.stdout,'exit_code':run.returncode}


def set_current(base_url, sid, state):
    request = Request(f'{base_url}/post?sid={sid}', data=json.dumps({'action':'set_current', 'state':state}).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urlopen(request, timeout=15) as response:
        if response.status != 200: raise RuntimeError(f'current state update failed: {response.status}')
