#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_DIR="$PROJECT_DIR/.cache"
HUB_PIN=53205689c3d88078c1375f76466d5bd799478828
DATASET_REV=3c021d06e2b01bbb6ad28cfddec41d856e4a78c5
DATASET_SHA=2198e335a8670297cad10405e58b06f3ee7acd8cceaf2d572a5c005e3736f79e
mkdir -p "$CACHE_DIR/external/tasks"
if [ ! -d "$CACHE_DIR/upstream-hub/.git" ]; then
  git init -q "$CACHE_DIR/upstream-hub"
  git -C "$CACHE_DIR/upstream-hub" remote add origin https://github.com/xlang-ai/CUA-Gym-Hub.git
  git -C "$CACHE_DIR/upstream-hub" fetch -q --depth 1 origin "$HUB_PIN"
  git -C "$CACHE_DIR/upstream-hub" checkout -q --detach FETCH_HEAD
fi
[ "$(git -C "$CACHE_DIR/upstream-hub" rev-parse HEAD)" = "$HUB_PIN" ]
ARCHIVE="$CACHE_DIR/external/cua_gym_tasks_v1.tar.zst"
if [ ! -f "$ARCHIVE" ]; then
  curl -fLsS --retry 2 "https://huggingface.co/datasets/xlangai/CUA-Gym/resolve/$DATASET_REV/artifacts/cua_gym_tasks_v1.tar.zst" -o "$ARCHIVE"
fi
echo "$DATASET_SHA  $ARCHIVE" | sha256sum -c -
if [ ! -f "$CACHE_DIR/external/tasks/378d436a-433a-51f8-a13f-92ecf1415e9f/task.json" ]; then
  tar --zstd -xf "$ARCHIVE" -C "$CACHE_DIR/external/tasks" --wildcards \
    '378d436a-433a-51f8-a13f-92ecf1415e9f/*' \
    '2c49ae92-7006-5de3-a938-b3c2af582948/*' \
    '6ae03946-3ada-5a5e-a526-e3283ac528d2/*' 2>/dev/null
fi
npm ci --prefix "$CACHE_DIR/upstream-hub/websites/gmail_mock" --ignore-scripts --no-audit --no-fund
mkdir -p "$CACHE_DIR/external/gmail_target"
cp -a "$CACHE_DIR/upstream-hub/websites/gmail_mock/." "$CACHE_DIR/external/gmail_target/"
cp -a "$CACHE_DIR/upstream-hub/shared" "$CACHE_DIR/shared"
mkdir -p "$CACHE_DIR/external/gmail_repaired"
cp -a "$CACHE_DIR/upstream-hub/websites/gmail_mock/." "$CACHE_DIR/external/gmail_repaired/"
(cd "$PROJECT_DIR" && python -c "from taskport.repair import patch_file; patch_file('${CACHE_DIR}/external/gmail_repaired/src/context/StoreContext.jsx')")
rm -rf "$CACHE_DIR/upstream-hub/websites/gmail_mock/.mock-states" "$CACHE_DIR/external/gmail_target/.mock-states" "$CACHE_DIR/external/gmail_repaired/.mock-states"
rm -rf "$CACHE_DIR/upstream-hub/websites/gmail_mock/.mock-files" "$CACHE_DIR/external/gmail_target/.mock-files" "$CACHE_DIR/external/gmail_repaired/.mock-files"
python -m pip install -q requests
printf 'Pinned external tasks and two independent Gmail runtime directories ready.\n'
