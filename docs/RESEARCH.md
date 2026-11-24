# Sources and feasibility evidence

- CUA-Gym upstream project and dataset workflow: https://github.com/xlang-ai/CUA-Gym and https://huggingface.co/datasets/xlangai/CUA-Gym. Its dataset card describes task JSON, setup scripts, reward scripts, endpoint placeholders, and warns that the dataset is not a direct benchmark leaderboard without a standardized execution protocol.
- CUA-Gym-Hub upstream mock apps: https://github.com/xlang-ai/CUA-Gym-Hub. Its README documents `/post?sid=` state injection, `/go?sid=` final-state inspection, and per-session isolation. App source `websites/gmail_mock/vite.config.js` stores state under `process.cwd()/.mock-states` and preserves the first injected initial state.
- CUA-Gym paper: https://arxiv.org/abs/2605.25624. Its setup/task/reward framing motivated externally defined tasks and independent reward invocation.

Pinned app commit: `53205689c3d88078c1375f76466d5bd799478828`. Pinned dataset revision: `3c021d06e2b01bbb6ad28cfddec41d856e4a78c5`. Archive SHA-256: `2198e335a8670297cad10405e58b06f3ee7acd8cceaf2d572a5c005e3736f79e`.

Feasibility check: dataset archive downloaded and hash verified; 13 Gmail `app_type` task bundles found, of which three with literal initial states and realizable state changes were selected. Vite Gmail mock installed and served in two independent processes. Original reward scripts returned partial/zero on unchanged tasks and 1.0 after control execution. Browser launch via `/usr/bin/chromium` failed with `process_singleton_posix.cc: socket() failed: Operation not permitted`; this prevents a reproducible UI trial in this environment.
