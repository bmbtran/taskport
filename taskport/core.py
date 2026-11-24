"""Portable task contract and conservative preflight diagnostics."""
from dataclasses import dataclass
import hashlib
import json


def state_digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Manifest:
    task_id: str
    app: str
    environment_pin: str
    initial_digest: str
    required_keys: tuple[str, ...]
    required_label_ids: tuple[str, ...]
    permitted_interface: str
    schema_version: int = 1


@dataclass(frozen=True)
class Preflight:
    ok: bool
    reasons: tuple[str, ...]


def preflight(manifest, state, environment_pin):
    reasons = []
    if environment_pin != manifest.environment_pin:
        reasons.append("environment_version_mismatch")
    for key in manifest.required_keys:
        if key not in state:
            reasons.append(f"missing_key:{key}")
    labels = {label.get("id") for label in state.get("labels", []) if isinstance(label, dict)}
    for label in manifest.required_label_ids:
        if label not in labels:
            reasons.append(f"missing_label:{label}")
    if state_digest(state) != manifest.initial_digest:
        reasons.append("state_digest_mismatch")
    return Preflight(not reasons, tuple(reasons))


def compare_traces(reference, target):
    for i in range(max(len(reference), len(target))):
        a = reference[i] if i < len(reference) else None
        b = target[i] if i < len(target) else None
        if a != b:
            return {"first_divergence": i, "classification": "action_divergence" if a and b else "trace_length_divergence", "reference": a, "target": b}
    return {"first_divergence": None, "classification": "same_trace"}


def summarize(trials):
    positives = [t for t in trials if t["fault"]]
    negatives = [t for t in trials if not t["fault"]]
    tp = sum(t["blocked"] for t in positives)
    fp = sum(t["blocked"] for t in negatives)
    return {"detection_recall": tp / len(positives) if positives else None,
            "false_positive_rate": fp / len(negatives) if negatives else None,
            "avoided_rollouts": tp, "n": len(trials)}
