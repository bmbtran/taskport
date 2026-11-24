# Findings

## State-interface control

Command: `python -m taskport.cli --repeats 3 --out experiments/pinned_3x`. Three external tasks, two isolated app processes, three repeats each. See the [summary](../experiments/pinned_3x/report.json), [trial records](../experiments/pinned_3x/trials.jsonl), and versioned manifests in the same directory.

| Measurement | Observation |
| --- | ---: |
| Clean full rewards after privileged state control | 18/18 |
| Untouched full rewards | 0/18 |
| Harmful missing-email faults blocked before rollout | 18/18 |
| Forced harmful counterfactuals below full reward | 18/18 |
| Differential trace divergences on harmful faults | 18/18 |
| Benign unrelated-label states blocked | 9/9 |
| Benign forced counterfactuals with full reward | 9/9 |
| False-positive rate across clean and benign negative controls | 9/27 = 33.3% |
| Fresh-session revalidations after restoration | 9/9 |
| Matched clean rewards and traces across two processes | 9/9 |

The exact initial-state digest is effective on these harmful mutations and overly strict on the measured benign ones. `18 avoided rollouts` refers to blocked harmful trials whose separately forced counterparts earned less than full reward; it is not a measurement of saved wall-clock time.

## Visible-browser experiment

GitHub Actions run `45360880284`, commit `faf33a2`, installed Chromium and ran the visible-UI integration tests. See the [browser summary](../experiments/browser_ci/report.json) and [21 raw trial records](../experiments/browser_ci/trials.jsonl).

| Task | Unmodified reference and target | Repaired runtime |
| --- | ---: | ---: |
| Urgent labeling, star, importance | 6/6 full reward | Not tested |
| Project labeling and archive | 0/6 full reward; every run scored 0.1 | 3/3 full reward |
| Client label creation and assignment | 6/6 full reward | Not tested |

The project task failed because the unmodified UI archived to `all-mail` while its upstream verifier expected `archive`. The one-line patched runtime changed that representation and passed without modifying the benchmark reward. The failure is a concrete task portability/compatibility issue, not an agent planning failure.

The browser runner is deterministic and these results cover one app, three selected tasks, and three repetitions. They do not estimate model-agent success or guarantee the patch generalizes. The labeled browser actions and original reward provide stronger evidence than the state-interface control for actual UI behavior.
