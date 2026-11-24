# Sources and feasibility evidence

- CUA-Gym upstream project and dataset workflow: https://github.com/xlang-ai/CUA-Gym and https://huggingface.co/datasets/xlangai/CUA-Gym. Its dataset card describes task JSON, setup and reward scripts, endpoint placeholders, and cautions that the dataset is not a leaderboard without a standardized execution protocol.
- CUA-Gym-Hub mock apps: https://github.com/xlang-ai/CUA-Gym-Hub. Its README documents `/post?sid=` state injection, `/go?sid=` final-state inspection, and per-session isolation. The pinned Gmail source `websites/gmail_mock/vite.config.js` stores state under `process.cwd()/.mock-states`; its archive action in `src/context/StoreContext.jsx` writes `all-mail`.
- CUA-Gym paper: https://arxiv.org/abs/2605.25624. Its setup/task/reward framing motivated externally defined tasks and original reward invocation.

Pinned app commit: `53205689c3d88078c1375f76466d5bd799478828`. Pinned dataset revision: `3c021d06e2b01bbb6ad28cfddec41d856e4a78c5`. Archive SHA-256: `2198e335a8670297cad10405e58b06f3ee7acd8cceaf2d572a5c005e3736f79e`.

Feasibility: archive downloaded and hash verified; three Gmail tasks with literal initial states selected; upstream app built and run in independent processes. Chromium launch locally failed at `process_singleton_posix.cc: socket() failed: Operation not permitted`; GitHub Actions run `45360880284` supplied a browser-capable environment and passed the repeated UI tests. The original reward exposes an archive representation mismatch that source inspection and a controlled one-line patch explain.
