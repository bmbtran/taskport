"""Deterministic state-interface control; does not simulate browser actions."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import uuid
import hashlib
from .benchmark import read_state, run_original_reward, set_current
from .core import Manifest, preflight, state_digest, compare_traces, summarize

HUB_PIN = '53205689c3d88078c1375f76466d5bd799478828'
TASK_LABELS = {
    '378d436a-433a-51f8-a13f-92ecf1415e9f': (),
    '2c49ae92-7006-5de3-a938-b3c2af582948': ('l1','l3','l4'),
    '6ae03946-3ada-5a5e-a526-e3283ac528d2': (),
}


def make_manifest(task_id, initial_state):
    if task_id not in TASK_LABELS: raise ValueError(f'unsupported task: {task_id}')
    return Manifest(task_id,'gmail_mock',HUB_PIN,state_digest(initial_state),('emails','labels'),TASK_LABELS[task_id],'state_api',1)


def execute_reference(task_id, initial_state):
    """Control execution using task instructions, not evaluator code or hidden reward state."""
    state=copy.deepcopy(initial_state)
    trace=[]
    def change(email, field, value):
        previous=copy.deepcopy(email.get(field))
        if previous!=value:
            email[field]=value
            trace.append({'action':f'email.{field}', 'subject':email['subject'], 'before':previous, 'after':value, 'ok':True})

    def label(name,color):
        existing=next((l for l in state['labels'] if l['name']==name),None)
        if existing: return existing['id']
        label_id='taskport-'+name.lower().replace(' ','-')
        state['labels'].append({'id':label_id,'name':name,'color':color})
        trace.append({'action':'create_label','name':name,'color':color,'ok':True})
        return label_id

    if task_id=='378d436a-433a-51f8-a13f-92ecf1415e9f':
        urgent=label('Urgent-Q1','#ef4444')
        for email in state['emails']:
            if email['folder']=='inbox' and any(word in (email['subject']+' '+email['body']).lower() for word in ('deadline','overdue','asap')):
                change(email,'labels',list(dict.fromkeys([*email['labels'],urgent])))
                change(email,'starred',True)
                change(email,'important',True)
    elif task_id=='2c49ae92-7006-5de3-a938-b3c2af582948':
        for email in state['emails']:
            if email['folder']!='inbox':continue
            text=(email['subject']+' '+email['body']).lower()
            category=next((name for words,name in [(('phoenix',),'Work'),(('vacation','trip'),'Travel'),(('invoice','payment'),'Finance')] if any(w in text for w in words)),None)
            if category:
                label_id=next(l['id'] for l in state['labels'] if l['name']==category)
                change(email,'labels',list(dict.fromkeys([*email['labels'],label_id])))
                change(email,'folder','archive')
    elif task_id=='6ae03946-3ada-5a5e-a526-e3283ac528d2':
        mapping={name:label('Client-'+name,color) for name,color in [('Alpha','#ef4444'),('Beta','#3b82f6'),('Gamma','#22c55e')]}
        for email in state['emails']:
            if email['folder']!='inbox':continue
            text=(email['subject']+' '+email['body']+' '+email['from']['email']).lower()
            name=next((name for name in mapping if name.lower() in text),None)
            if name:change(email,'labels',list(dict.fromkeys([*email['labels'],mapping[name]])))
    else:raise ValueError(f'unsupported task: {task_id}')
    return state,trace


def trial(manifest,base_url,sid,reward_path,output_dir,runtime_pin=HUB_PIN):
    if manifest.permitted_interface!='state_api': raise ValueError('state_api interface required by manifest')
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    before=read_state(base_url,sid)
    check=preflight(manifest,before['current_state'],runtime_pin)
    result={'task_id':manifest.task_id,'sid':sid,'preflight':asdict(check),'trace':[],'reward':None,'interface':'state_api'}
    if check.ok:
        target,trace=execute_reference(manifest.task_id,before['current_state'])
        set_current(base_url,sid,target)
        actual=read_state(base_url,sid)
        if actual['initial_state']!=before['initial_state']:
            raise RuntimeError('initial state mutated during execution')
        result['trace']=trace
        result['reward']=run_original_reward(reward_path,base_url,sid,output_dir/'verifier')['score']
        result['final_digest']=state_digest(actual['current_state'])
    (output_dir/'outcome.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    return result


def run_suite(task_root,output_dir,repeats=3,ports=(5173,5174)):
    """Three external tasks, independent reference/target servers, fresh sid per trial."""
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    records=[]
    clean=[]
    fault_rows=[]
    benign_rows=[]
    repairs=[]
    for task_id in TASK_LABELS:
        task_dir=Path(task_root)/task_id
        source=(task_dir/'initial_setup.py').read_text()
        reward_path=task_dir/'reward.py'
        state=extract_task_state(source)
        manifest=make_manifest(task_id,state)
        (output_dir/f'manifest-{task_id}.json').write_text(json.dumps({**asdict(manifest),'instruction':json.loads((task_dir/'task.json').read_text())['instruction'],'reward_sha256':hashlib.sha256(reward_path.read_bytes()).hexdigest(),'setup_sha256':hashlib.sha256(source.encode()).hexdigest(),'success_criterion':'original_reward == 1.0'},indent=2))
        for repetition in range(repeats):
            by_port=[]
            for port in ports:
                base=f'http://127.0.0.1:{port}'
                sid=uuid.uuid4().hex
                inject_trial_state(base,sid,state)
                path=output_dir/task_id/str(repetition)/str(port)
                baseline=run_original_reward(reward_path,base,sid,path/'baseline')['score']
                outcome=trial(manifest,base,sid,reward_path,path/'clean')
                clean.append({'task_id':task_id,'repeat':repetition,'port':port,'baseline':baseline,'reward':outcome['reward'],'fault':False,'blocked':not outcome['preflight']['ok'],'ran':bool(outcome['trace'])})
                by_port.append(outcome)
                records.append({'kind':'clean',**clean[-1]})
                if port!=ports[-1]:continue
                faults=[]
                for index in (0,1):
                    damaged=copy.deepcopy(state)
                    damaged['emails'].pop(index)
                    faults.append((f'missing_email_{index+1}',damaged,HUB_PIN))
                for name,altered,pin in faults:
                    fault_sid=uuid.uuid4().hex
                    inject_trial_state(base,fault_sid,altered)
                    fault_result=trial(manifest,base,fault_sid,reward_path,path/name,runtime_pin=pin)
                    observed=fault_result['preflight']['reasons']
                    correct='state_digest_mismatch' in observed
                    # Independent research-only counterfactual: a new session runs despite the
                    # preflight block, then the original upstream reward measures the failure.
                    forced_sid=uuid.uuid4().hex
                    inject_trial_state(base,forced_sid,altered)
                    forced_state,forced_trace=execute_reference(task_id,altered)
                    set_current(base,forced_sid,forced_state)
                    forced_score=run_original_reward(reward_path,base,forced_sid,path/name/'counterfactual')['score']
                    row={'kind':'fault','name':name,'task_id':task_id,'repeat':repetition,'port':port,'fault':True,'blocked':not fault_result['preflight']['ok'],'ran':bool(fault_result['trace']),'attributed':correct,'reasons':observed,'counterfactual_reward':forced_score,'trace_comparison':compare_traces(outcome['trace'],forced_trace)}
                    fault_rows.append(row)
                    records.append(row)
                # Harmless difference: an unrelated label does not alter task intent.
                benign=copy.deepcopy(state)
                benign['labels'].append({'id':'taskport-irrelevant','name':'TaskPort irrelevant','color':'#6b7280'})
                benign_sid=uuid.uuid4().hex
                inject_trial_state(base,benign_sid,benign)
                benign_block=trial(manifest,base,benign_sid,reward_path,path/'benign_drift')
                forced_sid=uuid.uuid4().hex
                inject_trial_state(base,forced_sid,benign)
                forced_state,forced_trace=execute_reference(task_id,benign)
                set_current(base,forced_sid,forced_state)
                benign_score=run_original_reward(reward_path,base,forced_sid,path/'benign_drift'/'counterfactual')['score']
                benign_row={'kind':'benign','task_id':task_id,'repeat':repetition,'port':port,'fault':False,
                    'blocked':not benign_block['preflight']['ok'],'ran':False,'counterfactual_reward':benign_score,
                    'reasons':benign_block['preflight']['reasons']}
                benign_rows.append(benign_row)
                records.append(benign_row)
                restored_sid=uuid.uuid4().hex
                inject_trial_state(base,restored_sid,state)
                repaired=trial(manifest,base,restored_sid,reward_path,path/'repaired')
                repairs.append(repaired['reward']==1.0)
                records.append({'kind':'repair','task_id':task_id,'repeat':repetition,'reward':repaired['reward'],'new_session':True})
            if len(by_port)==2:
                records.append({'kind':'comparison','task_id':task_id,'repeat':repetition,'trace_comparison':compare_traces(by_port[0]['trace'],by_port[1]['trace']),'reward_match':by_port[0]['reward']==by_port[1]['reward']})
    metrics=summarize(clean+fault_rows+benign_rows)
    report={'scope':'state_api control; no browser actions', 'task_ids':list(TASK_LABELS), 'hub_pin':HUB_PIN, 'repeats':repeats,
        'clean':{'n':len(clean),'full_reward':sum(t['reward']==1.0 for t in clean),'baseline_full_reward':sum(t['baseline']==1.0 for t in clean)},
        'faults':{'n':len(fault_rows),'detection_recall':metrics['detection_recall'],'false_positive_rate':metrics['false_positive_rate'],'avoided_rollouts':metrics['avoided_rollouts'],'coarse_attribution_accuracy':sum(t['attributed'] for t in fault_rows)/len(fault_rows),
                  'counterfactual_failures':sum(t['counterfactual_reward']<1.0 for t in fault_rows),
                  'benign_blocks':sum(t['blocked'] for t in benign_rows),
                  'benign_counterfactual_successes':sum(t['counterfactual_reward']==1.0 for t in benign_rows),
                  'traces_with_divergence':sum(t['trace_comparison']['first_divergence'] is not None for t in fault_rows)},
        'repairs':{'attempted':len(repairs),'successful':sum(repairs),'method':'new clean session after fault; no in-place repair'},
        'comparisons':{'equal_rewards':sum(r['reward_match'] for r in records if r['kind']=='comparison'), 'equal_traces':sum(r['trace_comparison']['first_divergence'] is None for r in records if r['kind']=='comparison')},
        'limitations':['no browser UI execution','no deployed application code change tested; version mismatch is a contract unit test only','state updates through privileged mock endpoint','selected tasks only; no statistical generalization']}
    (output_dir/'trials.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    (output_dir/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    return report


from .benchmark import extract_initial_state as extract_task_state, inject_state as inject_trial_state
