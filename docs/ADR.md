# Architecture decision record

## ADR-001: externally defined tasks and pinned source

Decision: use three CUA-Gym Gmail bundles identified by UUID in `experiment.py`, the original upstream `reward.py`, and the CUA-Gym-Hub Gmail mock pinned by git commit. Pin the 52 MB task archive by SHA-256 and record setup/reward hashes per manifest. The selected instructions cover urgent triage, project labeling with archive, and client labeling with new labels. The rewards have different intermediate scoring rules. These are public, externally authored tasks; the project does not invent an app or its success criterion. The selection is purposive, so results do not estimate broader task performance.

## ADR-002: safe setup and trial independence

Decision: extract top-level literal `state` via Python AST, reject dynamic initial-state expressions, and inject through the mock endpoint. Upstream setup scripts launch a browser and share `/tmp/task_web_sid`; running them as-is would mingle trials. Each trial instead uses a random session ID and its verifier gets a private patched copy pointing to its own SID file and local endpoint. The original reward logic is retained. New tasks with dynamic setup need a reviewed adapter; do not silently execute them.

## ADR-003: versioned contract and conservative preflight

Decision: the manifest records schema version, task ID, app, upstream commit pin, exact initial-state digest, required keys/label IDs, permitted state interface, instruction, source hashes and original-reward criterion. Preflight blocks on any contract mismatch. It has strong detection on these injected faults but can reject harmless changes. A deployed code version is not cryptographically attested by the HTTP server; runtime launch and manifest pin must be compared against checked-out source when reproducing.

## ADR-004: independent verifier and separate runtime processes

Decision: two separate Vite processes run in distinct directories, with separate `.mock-states` stores and browser-independent session IDs. The original upstream reward independently reads `/go` after the executor updates `/post`. This detects cases where the executor reports success but the final state does not meet benchmark criteria. Because the verifier and mock are from the same research suite, they are independent of TaskPort's executor but not independent of the upstream benchmark itself.

## ADR-005: measured faults and differential diagnosis

Decision: inject two missing-email faults per task; preflight blocks before rollout. Run a separate forced counterfactual and require original reward below 1.0 to count a harmful rollout avoided. Compare clean and forced state-operation traces and report the first divergence. Class attribution is only `state_digest_mismatch` for these faults; trace divergence cannot uniquely identify the underlying missing email without state inspection. Repair validation is a fresh, clean trial, not an in-place repair algorithm.

## ADR-006: explicitly scoped execution interface

Decision: deterministic task-specific control through state API. Chromium launch fails here due denied Unix process socket; state API lets the compatibility contract, reward, runtime isolation, and controlled-fault claims be verified. This is a scaffold for browser execution, not a substitute for it. A future browser runner must use visible UI observations and actions only, record screenshots/action traces, run against both processes, and repeat the same upstream reward experiments. Until then, no UI success or agent portability claim is supported.
