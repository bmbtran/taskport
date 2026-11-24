# Measured results (pinned_3x)

Command: `python -m taskport.cli --repeats 3 --out experiments/pinned_3x` after `./bootstrap.sh`. Three external tasks, two processes, three repeats each, with fresh session IDs and the original upstream reward. The raw sample and hashes are in the neighboring JSON files.

| Measurement | Observation | Meaning |
| --- | ---: | --- |
| Clean task/runtime trials | 18 | 3 tasks × 2 runtimes × 3 repeats |
| Clean full rewards | 18/18 | Original reward scored 1.0 after state-interface control |
| Untouched full rewards | 0/18 | Original reward was below 1.0 before control |
| Harmful state faults | 18 | First or second qualifying email removed in target trial |
| Preflight detected faults | 18/18 | Exact state digest changed |
| False positives on clean trials | 0/18 | Only sampled pristine states considered negative |
| Forced counterfactual failures | 18/18 | On separate trials the upstream reward remained below 1.0 |
| Differential trace divergences | 18/18 | First different state operation identified |
| Revalidation after clean reset | 9/9 | New session passed after restoring original task state |
| Matched reference/target clean reward and trace | 9/9 | Same application bytes, different process and state directory |

This establishes a reliable *state-interface control* under two process instances and the selected fault injections. It does not measure human-like UI action portability, actual code-version drift, agent success, generalization to other apps, or ability to repair a broken existing state. Exact-state preflight can reject harmless changes, which are absent from the sampled negatives; the reported 0% false-positive rate is limited to pristine negative controls. The first trace divergence is a useful symptom locator; attributing the injected cause comes from the experimental ground truth and state comparison.
