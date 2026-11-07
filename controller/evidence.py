"""Deterministic population comparisons and workflow policy checks."""
import math
from statistics import NormalDist


def rate(count, kpi):
    numerator, denominator = ((count["engaged"], count["connected"]) if kpi == "engagement_rate"
                              else (count["connected"], count["dials"]))
    return numerator / denominator if denominator else None


def interval(successes, n, z=2.576):
    if not n:
        return (0.0, 1.0)
    p, z2 = successes / n, z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    radius = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, center - radius), min(1.0, center + radius)


def difference(left, right, kpi, z):
    key, denominator = ("engaged", "connected") if kpi == "engagement_rate" else ("connected", "dials")
    n1, n2 = left[denominator], right[denominator]
    if not n1 or not n2:
        return {"delta": None, "lower": -1.0, "upper": 1.0, "n": min(n1, n2)}
    delta = right[key] / n2 - left[key] / n1
    # A half-count adjustment prevents a zero estimated variance at 0% or 100%.
    p1, p2 = (left[key] + .5) / (n1 + 1), (right[key] + .5) / (n2 + 1)
    error = z * math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {"delta": delta, "lower": delta - error, "upper": delta + error, "n": min(n1, n2)}


def compare(control, treatment, primary, max_drop, comparisons):
    z = NormalDist().inv_cdf(1 - .05 / (2 * max(1, comparisons)))
    guardrail = "pickup_rate" if primary == "engagement_rate" else "engagement_rate"
    effect = difference(control, treatment, primary, z)
    guard = difference(control, treatment, guardrail, z)
    enough = effect["n"] >= 200 and guard["n"] >= 200
    return {"winner": enough and effect["lower"] > .01 and guard["lower"] >= -max_drop,
            "primary_delta": effect["delta"], "primary_interval": [effect["lower"], effect["upper"]],
            "guardrail_delta": guard["delta"], "guardrail_interval": [guard["lower"], guard["upper"]],
            "minimum_sample_met": enough, "comparisons": comparisons, "z": z,
            "control": control, "treatment": treatment}


def distribution(weights):
    if not weights or any(not math.isfinite(w) or w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("A distribution needs finite nonnegative weights and positive total")
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items() if value > 0}


def effective(config, cohort, dimension):
    allocations = config["allocations"]
    return distribution(allocations.get(cohort, {}).get(dimension, allocations["default"][dimension]))


def exploration_weights(options, control):
    # Bound unknown exposure at 20%. Dyadic weights are exactly representable,
    # so repeated API normalization does not fabricate unrelated dimension changes.
    per_arm = 2 ** math.floor(math.log2(.2 / (len(options) - 1)))
    return {voice: 1 - per_arm * (len(options) - 1) if voice == control else per_arm for voice in options}


def cohort_for(features, definitions):
    for cohort in definitions:
        if all(features.get(key) in values for key, values in cohort["where"].items()):
            return cohort["id"]
    return "default"


def changed_dimensions(old, new):
    changed = [key for key in ("cohorts", "prompt_version", "schedule") if old.get(key) != new.get(key)]
    cohorts = set(old["allocations"]) | set(new["allocations"]) | {"default"}
    for dimension in ("voice", "welcome_message", "caller_id"):
        if any(effective(old, c, dimension) != effective(new, c, dimension) for c in cohorts):
            changed.append(dimension)
    return changed


def auto_check(policy, old, new):
    dimensions = changed_dimensions(old, new)
    reasons = []
    if not policy.get("enabled"):
        reasons.append("auto-apply disabled")
    if set(dimensions) - set(policy.get("allowed_dims", [])):
        reasons.append("changed dimension outside allowlist")
    shift = 0.0
    for cohort in set(old["allocations"]) | set(new["allocations"]) | {"default"}:
        for dimension in ("voice", "welcome_message", "caller_id"):
            before, after = effective(old, cohort, dimension), effective(new, cohort, dimension)
            shift = max(shift, .5 * sum(abs(before.get(k, 0) - after.get(k, 0)) for k in before.keys() | after.keys()))
    if shift > policy.get("max_shift", 0) + 1e-10:
        reasons.append("distribution shift exceeds policy")
    return {"allowed": not reasons, "reasons": reasons, "dimensions": dimensions, "max_shift": shift}
