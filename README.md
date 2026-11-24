# TaskPort

TaskPort tests whether externally defined CUA-Gym tasks survive transfer between independently initialized Gmail mock runtimes. It includes two explicitly different execution modes: a state-interface control and visible browser actions. A third, versioned runtime tests a one-line repair for an upstream browser/reward incompatibility. The browser script is deterministic; these are **not model-agent success rates**.

## Reproduce

Requires Python 3.12, Node 24 or compatible, npm, git, curl, tar with zstd, and access to GitHub, Hugging Face, and npm. Run from the repository root:

```bash
./bootstrap.sh
python -m unittest discover -s tests -v
python -m taskport.cli --repeats 3 --out experiments/reproduction
```

`bootstrap.sh` pins CUA-Gym-Hub to commit `53205689c3d88078c1375f76466d5bd799478828` and verifies the task archive SHA-256 `2198e335a8670297cad10405e58b06f3ee7acd8cceaf2d572a5c005e3736f79e`. It installs the three selected external task bundles into `.cache/external/tasks`, creates reference and target runtime directories, and applies a narrowly scoped archive patch in a third directory. Source and npm dependencies remain outside git.

For browser tests, install Python Playwright and its Chromium browser in a browser-capable environment, then run `TASKPORT_BROWSER=1 python -m unittest discover -s tests -v`. GitHub Actions performs this and publishes `browser-study` trial artifacts. This local execution sandbox denies Chromium's process socket, so its default unit run skips the two browser tests. The published [browser results](experiments/browser_ci/report.json) and [raw trials](experiments/browser_ci/trials.jsonl) came from a successful GitHub Actions run.

## What each stage measures

1. **External task contract:** read `task.json`; parse a literal state from the task's setup code without launching its shared `/tmp` browser; record task instruction, initial digest, source hashes, application pin, and permitted interface.
2. **Preflight:** reject missing required state or mismatched version before execution. The state control also tests two harmful missing-email faults and a harmless added-label change against the original reward.
3. **Execution:** the state control uses the mock's privileged `/post` API; the browser runner reads rendered sender/subject/snippet text and clicks label, star, important, and archive controls. Their manifests mark the two interfaces separately.
4. **Independent verification:** invoke the upstream `reward.py` with a private session file after each trial; compare state-operation or browser-action traces across runs.
5. **Repair validation:** the unmodified UI archives to `all-mail`, whereas one upstream reward demands `archive`. A third runtime changes only that UI archive transition and runs the same task and original reward again.

See [state experiment results](experiments/pinned_3x/report.json), [browser results](experiments/browser_ci/report.json), [architecture decisions](docs/ADR.md), [research sources](docs/RESEARCH.md), [findings](docs/RESULTS.md), and [failed attempts](docs/FAILURES.md), and [first-principles tutorial](docs/TUTORIAL.md).

## Limits

Three purposively selected tasks from one mock app do not estimate general task portability. The browser runner follows a deterministic task-specific policy using visible rows; no model agent chooses actions. Two baseline processes use identical pinned app code; the repaired third process is the controlled code-version difference. Exact-state preflight detects the missing-email faults but blocks benign added-label states too. First trace divergence identifies a symptom, not a proven root cause. A repair success means the original reward passed in a fresh session of the patched app; it does not automatically migrate an in-progress session.
