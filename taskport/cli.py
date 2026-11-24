"""Start independent mock processes and run the pinned state-interface experiment."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen
from .experiment import run_suite, HUB_PIN


def attest_runtimes(reference, target, check_upstream_commit=True):
    """Check copied app bytes and pinned git source before claiming same-version trials."""
    def digest(root):
        files=[p for p in root.rglob('*') if p.is_file() and
               not any(part in ('node_modules','.mock-states','.mock-files','.git','dist') for part in p.relative_to(root).parts)]
        data=hashlib.sha256()
        for path in sorted(files):
            data.update(str(path.relative_to(root)).encode())
            data.update(hashlib.sha256(path.read_bytes()).digest())
        return data.hexdigest()
    if digest(reference)!=digest(target): raise ValueError('runtime source mismatch')
    if check_upstream_commit:
        upstream=reference.parents[1]
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip()
        if head!=HUB_PIN: raise ValueError(f'upstream commit mismatch: {head}')
    return digest(reference)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--out',type=Path,default=Path('experiments/latest'))
    args=parser.parse_args()
    if args.repeats<1: parser.error('--repeats must be positive')
    cache=Path(__file__).resolve().parents[1]/'.cache'
    ports=(5173,5174)
    dirs=(cache/'upstream-hub/websites/gmail_mock',cache/'external/gmail_target')
    source_hash=attest_runtimes(*dirs)
    processes=[]
    try:
        for directory,port in zip(dirs,ports):
            if not (directory/'node_modules/vite/bin/vite.js').exists():
                raise RuntimeError(f'missing app dependencies in {directory}; run ./bootstrap.sh')
            processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=directory,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for process,port in zip(processes,ports):
            for attempt in range(80):
                if process.poll() is not None: raise RuntimeError(f'runtime {port} exited early')
                try: urlopen(f'http://127.0.0.1:{port}',timeout=.3).close();break
                except Exception: time.sleep(.1)
            else: raise RuntimeError(f'runtime {port} did not become ready')
        report=run_suite(cache/'external/tasks',args.out,args.repeats,ports)
        report["runtime_source_sha256"]=source_hash
        (args.out/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True))
        print(json.dumps(report,indent=2))
    finally:
        for process in processes:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill()


if __name__=='__main__':main()
