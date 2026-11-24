# TaskPort

TaskPort probes the portability of externally defined CUA-Gym Gmail tasks between two independently initialized mock app processes. The implemented experiment executes a deterministic **state-interface control**. It does not drive a browser, and its numbers are **not CUA-agent success rates**.

## Reproduce

Requires Python 3.12, Node 24 or compatible, npm, git, curl, tar with zstd, and access to GitHub, Hugging Face, and npm. Run from the repository root:

```bash
./bootstrap.sh
python -m unittest discover -s tests -v
python -m taskport.cli --repeats 3 --out experiments/reproduction
```

The bootstrap pins CUA-Gym-Hub to commit `53205689c3d88078c1375f76466d5bd799478828` and verifies the task archive SHA-256 `2198e335a8670297cad10405e58b06f3ee7acd8cceaf2d572a5c005e3736f79e`. It installs the three selected external task bundles into `.cache/external/tasks` and creates separate runtime directories. Source and app dependencies remain outside git.

## Experiment

Three original task instructions and `reward.py` files are used unchanged in meaning. Task setup scripts declare literal initial states; TaskPort parses those literals with `ast.literal_eval` instead of running their browser-launch side effects. Every episode gets a fresh session ID. An exact state digest and runtime pin form the preflight contract. A task-specific deterministic control changes the Gmail mock through its privileged state endpoint, and the original reward script independently reads the resulting state. The reference and target processes have separate current-state storage.

The two injected harmful faults remove a different qualifying email from each task's initial state. A preflight-blocked run is paired with a separate research-only forced run; the upstream reward confirms the failure and its trace is compared with a clean trace. A repair result means a **new clean session** passes again. The version mismatch unit test checks only declared metadata, not an actual code upgrade.

See [experiment results](experiments/pinned_3x/report.json), [trial evidence](experiments/pinned_3x/trials.jsonl), [findings](docs/RESULTS.md), [architecture decisions](docs/ADR.md), [research sources](docs/RESEARCH.md), and [failures and rejected options](docs/FAILURES.md).

## Architecture

`bootstrap.sh` pins external bytes → `benchmark.py` extracts state and invokes original reward → `core.py` defines the versioned contract, validator, trace comparator, and metrics → `experiment.py` executes selected tasks, counterfactual faults, and revalidation → `cli.py` owns two independent local server lifecycles and writes JSON evidence.

The test suite includes contract, parser safety, runtime isolation, original-reward baseline, six full-reward task/runtime cases, preflight block, and repeated fault experiment assertions. Each trial writes an `outcome.json`; top-level manifests, trials, and summary remain tracked. The raw per-trial verifier copies and runtime files are ignored.

## Limits

The reference control reads structured state and writes `/post` directly, so it bypasses UI behavior and cannot establish browser action portability. Three tasks from one Gmail mock were selected for feasibility, without random sampling. Both runtimes use the same pinned application code; their differences are controlled task-state changes. Exact digest preflight rejects benign state differences too, though this sample contains no benign drift. Trace comparison points to the first differing operation; it does not prove a causal root cause. See the ADR for the work needed before claiming CUA portability.
