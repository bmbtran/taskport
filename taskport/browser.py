"""Visible-UI browser runner for three pinned Gmail tasks.

It reads rendered rows and clicks controls. The privileged endpoints are used
only by setup, preflight, and the independent upstream verifier.
"""
from dataclasses import asdict
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from .benchmark import read_state,run_original_reward
from .core import preflight
from .experiment import HUB_PIN

URGENT='378d436a-433a-51f8-a13f-92ecf1415e9f'
PROJECT='2c49ae92-7006-5de3-a938-b3c2af582948'
CLIENT='6ae03946-3ada-5a5e-a526-e3283ac528d2'


def _create_label(page,name,color_index,trace):
    page.get_by_text('Labels',exact=True).locator('..').locator('button').click()
    dialog=page.locator('div.fixed').filter(has=page.get_by_text('New label',exact=True))
    dialog.get_by_placeholder('Label name').fill(name)
    dialog.locator('button.rounded-full.border-2').nth(color_index).click()
    dialog.get_by_role('button',name='Create',exact=True).click()
    page.get_by_role('link',name=name,exact=True).wait_for()
    trace.append({'action':'create_label','name':name,'ok':True})


def _row(page,subject):
    return page.get_by_text(subject,exact=True).locator('xpath=ancestor::div[contains(concat(" ", normalize-space(@class), " "), " group ")][1]')


def _apply_label(page,row,name,trace,subject):
    row.get_by_role('button',name='Select').click()
    page.get_by_role('button',name='Label',exact=True).click()
    menu=page.get_by_text('Apply label:',exact=True).locator('..')
    menu.get_by_text(name,exact=True).click()
    row.get_by_role('button',name='Select').click()
    trace.append({'action':'apply_label','subject':subject,'name':name,'ok':True})


def _decide(task_id,visible_text):
    text=visible_text.lower()
    if task_id==URGENT:
        return 'Urgent-Q1' if any(w in text for w in ('deadline','overdue','asap')) else None
    if task_id==PROJECT:
        for words,name in [(('phoenix',),'Work'),(('vacation','trip'),'Travel'),(('invoice','payment'),'Finance')]:
            if any(w in text for w in words):return name
        return None
    if task_id==CLIENT:
        for name in ('Alpha','Beta','Gamma'):
            if name.lower() in text:return 'Client-'+name
        return None
    raise ValueError('unsupported task')


def browser_trial(manifest,base_url,sid,reward_path,output_dir,runtime_pin=HUB_PIN):
    if manifest.permitted_interface!='browser': raise ValueError('browser interface required by manifest')
    output_dir=Path(output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    check=preflight(manifest,read_state(base_url,sid)['current_state'],runtime_pin)
    result={'task_id':manifest.task_id,'sid':sid,'preflight':asdict(check),'trace':[],'reward':None,'interface':'browser'}
    if not check.ok:
        (output_dir/'outcome.json').write_text(json.dumps(result,indent=2))
        return result
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            context=browser.new_context(viewport={'width':1440,'height':900})
            page=context.new_page()
            page.goto(f'{base_url}/?sid={sid}',wait_until='domcontentloaded')
            page.get_by_text('Labels',exact=True).wait_for()
            page.locator('div.group').first.wait_for()
            if manifest.task_id==URGENT:_create_label(page,'Urgent-Q1',0,result['trace'])
            if manifest.task_id==CLIENT:
                for name,index in [('Client-Alpha',0),('Client-Beta',4),('Client-Gamma',3)]:
                    _create_label(page,name,index,result['trace'])
            # Work from visible sender, subject, and snippet text. No hidden app state or reward script.
            rows=[]
            for row in page.locator('div.group').all():
                visible=row.inner_text()
                subject=row.locator('span.text-gray-900').first.inner_text()
                name=_decide(manifest.task_id,visible)
                if name:rows.append((subject,name))
            for subject,name in rows:
                row=_row(page,subject)
                if manifest.task_id==URGENT:
                    row.get_by_role('button',name='Star',exact=True).click()
                    result['trace'].append({'action':'star','subject':subject,'ok':True})
                    row.get_by_role('button',name='Mark as important').click()
                    result['trace'].append({'action':'mark_important','subject':subject,'ok':True})
                _apply_label(page,row,name,result['trace'],subject)
                if manifest.task_id==PROJECT:
                    row.hover()
                    row.get_by_role('button',name='Archive').click()
                    result['trace'].append({'action':'archive','subject':subject,'ok':True})
            page.screenshot(path=str(output_dir/'final.png'),full_page=True)
            page.wait_for_timeout(600)
            result['reward']=run_original_reward(reward_path,base_url,sid,output_dir/'verifier')['score']
            result['final_emails']=[{'subject':e['subject'],'labels':e['labels'],'folder':e['folder']} for e in read_state(base_url,sid)['current_state']['emails']]
        finally:
            browser.close()
    (output_dir/'outcome.json').write_text(json.dumps(result,indent=2))
    return result
