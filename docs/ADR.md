# Architecture decision record

## ADR-001: externally defined tasks and pinned source

Decision: select three CUA-Gym Gmail bundles by UUID in `experiment.py`, use their original `task.json` instructions and `reward.py` scripts, and pin CUA-Gym-Hub by git commit. Pin the 52 MB task archive by SHA-256 and record setup/reward hashes per manifest. The instructions cover urgent triage, project labeling and archive, and client labeling with new labels. Purposeful selection makes a small feasibility experiment, not a representative benchmark score.

## ADR-002: safe setup and trial independence

Decision: extract top-level literal `state` via Python AST, reject dynamic expressions, and inject through the mock endpoint. Upstream setup scripts launch a browser and share `/tmp/task_web_sid`; executing them as-is would mingle trials. Each trial gets a random session ID and its original reward runs from a private copy pointing at its own SID file and local endpoint. Dynamic task setups need a reviewed adapter rather than silent execution.

## ADR-003: versioned contract and conservative preflight

Decision: record schema version, task ID, app, upstream commit pin, exact initial-state digest, required keys/label IDs, permitted interface, instruction, source hashes, and original-reward criterion. Preflight blocks on a contract mismatch. It detects all sampled harmful faults but also blocks nine unrelated-label controls that independently retain full reward. This measured false-positive cost argues for semantic checks in a later version.

## ADR-004: independent verifier and runtime isolation

Decision: separate Vite processes run in distinct directories and `.mock-states` stores. The original upstream reward independently fetches `/go` after UI or state execution. The two unmodified app copies are attested to identical source bytes; the repaired copy has one explicit code change. The verifier is independent of TaskPort's runner, though it remains part of the same upstream research suite.

## ADR-005: differential diagnosis and counterfactuals

Decision: inject two missing qualifying emails per task, block them preflight, then run separate forced trials and require the original reward below 1.0 before counting an avoided failed rollout. Compare clean and forced traces at the first different action. The known injected fault supplies the causal ground truth; trace difference alone does not identify it. An added unrelated label supplies a reward-preserving negative control. Fresh-session revalidation does not constitute in-place repair.

## ADR-006: browser execution in reproducible CI

Decision: a browser script reads only visible sender/subject/snippet rows to choose targets and clicks Gmail controls. Task setup and the independent verifier may use privileged endpoints; browser decisions and actions do not. Local Chromium failed on a denied process socket, so GitHub Actions installs Playwright Chromium and runs the browser tests with `TASKPORT_BROWSER=1`. Browser runs repeat each task three times on two unmodified processes, with full-reward outcomes on two tasks and one reproducible compatibility failure.

## ADR-007: narrow archive repair

Observation: the pinned Gmail UI's Archive action sets `folder: 'all-mail'`, while external project task `reward.py` checks `folder: 'archive'`. All six browser trials of this task on unmodified runtimes scored 0.1 despite completing six label/archive sequences. Decision: preserve reference and target unchanged; copy the pinned app into a third runtime and replace exactly one archive transition, rejecting the patch if upstream source differs. The original reward scored 1.0 in all three patched browser repetitions. Paired action traces were identical in all three comparisons while final email states differed. This repairs the benchmark/app contract for this one task and does not prove wider compatibility.

## ADR-008: excluded infrastructure

Kafka, Kubernetes, a dashboard, a custom mock app, and a model-driven agent were deferred. None is needed to establish the pinned task, independent verifier, runtime isolation, browser fault, or repair. A learned agent would add outcome variance before the portability contract is understood.
