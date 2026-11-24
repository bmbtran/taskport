# TaskPort from first principles

## 1. What is a portable computer-use task?

A benchmark task has three parts: an instruction, a starting world, and a way to judge the resulting world. For TaskPort, these come from CUA-Gym. The instruction might ask for project emails to receive labels and then be archived. The starting world is a specific Gmail mock state, and the original `reward.py` evaluates the final state through the mock's `/go` endpoint.

Moving a task to another runtime can fail even when the task text and click sequence are identical. The app might initialize with different labels, a control might write a different state representation, or the verifier might be unavailable. A normal task success rate combines these infrastructure problems with the agent's planning and action mistakes. TaskPort isolates the portability contract first with a deterministic reference runner.

## 2. What does a manifest represent?

The manifest is a versioned assertion about one task: its ID, application, upstream source pin, exact initial-state digest, required keys and label IDs, permitted execution interface, and original verifier. Each generated JSON manifest also records the instruction and hashes of the setup and reward scripts. The preflight function checks these assumptions against the target before taking an action.

An exact SHA-256 state digest is easy to reason about and catches missing task data. It is also too strict. Adding an unrelated label does not prevent a task from succeeding, yet it changes the digest. The 9/9 benign controls were blocked even though their independently forced executions earned full reward. That measured false-positive behavior is why a future validator should distinguish semantically required state from irrelevant state. The current validator avoids pretending that it already knows how to make this distinction for all tasks.

## 3. Why are there separate app processes and sessions?

Each Gmail mock process stores session files under its own working directory. Reference and target copies live in different directories, have separate process lifetimes, and receive fresh random session IDs. This separates one trial's initial and current state from another's. The project also verifies the two unmodified copies have identical source bytes, which makes an initial process-isolation control. A third copy changes one known app transition to test a code-level repair.

The mock preserves the first injected state as its baseline. Updating the current state later does not rewrite that baseline. This allows the original reward to compare before and after, and it requires a fresh session whenever we want a new initial world. The upstream setup script uses a shared `/tmp/task_web_sid` file and launches Chrome. TaskPort instead parses its literal state with `ast.literal_eval`, injects that state, and gives each verifier call a private SID file. The reward logic itself is unchanged.

## 4. Why have two execution interfaces?

The **state-interface control** reads structured current state and writes a desired current state through `/post`. It validates task setup, isolation, preflight, trace recording, reward invocation, and fault measurement. It bypasses the Gmail UI, so it cannot measure computer-use behavior. Its manifest says `state_api`.

The **browser runner** opens the task in Chromium, reads visible sender, subject, and snippet text, then clicks Gmail's create-label, label, star, important, and archive controls. It never uses the privileged state API to choose or execute actions. Setup and verification still use that API outside the browser runner. Its manifest says `browser`. The browser policy is deterministic and task-specific, so these experiments measure the app-task compatibility of a reference workflow, not the intelligence of a learned agent.

The local execution sandbox denied Chromium's process socket. GitHub Actions provided a browser-capable environment, installed Playwright Chromium, and ran the repeated browser experiments. The browser study records original-reward scores, action traces, and final email summaries.

## 5. What does independent verification buy us?

The runner's trace says what actions it attempted. That is not evidence that the task succeeded. After a run, the upstream reward script independently fetches the final mock state and scores it. Keeping reward code outside the runner exposes discrepancies between attempted actions and the task's actual acceptance criteria. It also avoids writing a self-fulfilling test whose expected result is copied from TaskPort's own transformation.

Independent here means independent of TaskPort's executor. It does not mean that CUA-Gym's reward is infallible. The project-archive task demonstrates that the upstream app and reward disagree about the representation of an archived email.

## 6. How did the archive failure arise?

The browser runner performed the requested project labeling and clicked Archive for six matching emails. It generated the same successful-looking sequence on both unmodified app processes. Yet all six project task browser trials scored 0.1. Source inspection found that Gmail's Archive handler sets `folder: 'all-mail'`, while the original `reward.py` awards its archive components only when `folder: 'archive'`. The unchanged seventh email accounts for the remaining 0.1 reward.

TaskPort preserves those unmodified failures as evidence. A third runtime applies one guarded replacement in the app's Archive handler. Its patch refuses to run if the expected upstream source expression changes. On the patched app, the same browser workflow earned full reward in three out of three repeated trials. The original task and reward remained intact. All three paired comparisons confirmed matching browser action traces with different final states and reward scores. Differential diagnosis must inspect final-state evidence as well as action traces.

This is a compatibility repair to one mock app. It does not mean every real email app represents archive the same way, and it does not justify changing the benchmark reward to make the test pass.

## 7. How do the fault experiments work?

For each of the three tasks, three repetitions compare two unmodified processes. The state-interface control completes all 18 clean task/runtime trials. On the target, the experiment separately removes the first or second qualifying email before rollout, giving 18 harmful injected faults. Exact-digest preflight blocks each. A separate research-only counterfactual deliberately runs each damaged task despite the block. The original reward remains below 1.0 on all 18. This supports calling them avoided *failed* rollouts, though no time savings were measured.

A third injected condition adds an irrelevant label. This gives nine benign trials that preflight blocks and nine separate forced executions that all reach full reward. Counting the 18 pristine controls and nine benign controls as negative cases gives a measured false-positive rate of 9/27, or 33.3%. That number describes this designed sample, not an estimate for unseen tasks.

A fresh unmodified state is then injected into a new session and validated again. Nine of nine revalidations earn full reward. This verifies recovery by resetting the task environment. It is not a procedure that edits a damaged live session in place.

## 8. How should you interpret traces and scores?

A trace contains the ordered actions and their observed execution status. TaskPort finds the first difference between a clean state-operation trace and a forced harmful trial. This narrows where behavior diverged, but it cannot prove which missing email caused the difference without state evidence and known injection labels. The browser study reveals an even subtler case: the action sequence stays the same while an app implementation change alters the final folder values.

Detection recall on the 18 injected harmful faults is 18/18. Clean browser success is 12/18 on the unmodified runtimes because one of the three tasks fails in all six repeats. The repaired archive task passes 3/3 on the patched runtime. None of these small purposively selected counts should be converted into a broad CUA benchmark claim.

## 9. Why were other approaches rejected?

A dashboard, Kubernetes, Kafka, and a custom mock app would increase scope without resolving the task-app-verifier contract. An unpinned hosted demo would make results hard to reproduce. Directly executing upstream setup scripts would create shared SID and browser side effects. Writing the expected final state through `/post` and calling it a browser success would overclaim. A learned agent could be added after the reference workflow and environment semantics are stable, using the same independent verifier to separate agent mistakes from environment incompatibilities.

Read `docs/ADR.md` for the exact decisions, `docs/FAILURES.md` for failed implementation attempts, and `docs/RESULTS.md` for the measured evidence.
