from controller.evidence import compare, auto_check, cohort_for, changed_dimensions, exploration_weights


def counts(dials, connected, engaged):
    return dict(dials=dials, connected=connected, engaged=engaged, hallucinations=0)


def config(weights):
    return {"cohorts": [], "allocations": {"default": {"voice": weights, "welcome_message": {"W1": 1}, "caller_id": {"D1": 1}}},
            "prompt_version": "P1", "schedule": {}}


def test_population_and_guardrail_are_required():
    assert not compare(counts(20, 10, 4), counts(20, 10, 9), "engagement_rate", .02, 24)["winner"]
    assert not compare(counts(10000, 8000, 4000), counts(10000, 6000, 4200), "engagement_rate", .02, 24)["winner"]
    result = compare(counts(10000, 4000, 2000), counts(10000, 4200, 2940), "engagement_rate", .02, 24)
    assert result["winner"] and result["primary_delta"] > .19


def test_auto_apply_obeys_dimensions_and_total_variation():
    policy = {"enabled": True, "allowed_dims": ["voice"], "max_shift": .2}
    assert auto_check(policy, config({"V1": 1}), config({"V1": .8, "V2": .2}))["allowed"]
    assert not auto_check(policy, config({"V1": 1}), config({"V1": .7, "V2": .3}))["allowed"]
    prompt_change = config({"V1": 1})
    prompt_change["prompt_version"] = "P2"
    assert not auto_check(policy, config({"V1": 1}), prompt_change)["allowed"]
    assert changed_dimensions(config({"V1": 1}), config({"V1": 10})) == []


def test_shared_cohort_uses_first_match_and_default():
    cohorts = [{"id": "first", "where": {"lang": ["ta"]}}, {"id": "second", "where": {"age_band": ["60+"]}}]
    assert cohort_for({"lang": "ta", "age_band": "60+"}, cohorts) == "first"
    assert cohort_for({"lang": "hi", "age_band": "18-30"}, cohorts) == "default"


def test_exploration_bounds_exposure_and_normalizes_without_float_drift():
    for size in range(2, 10):
        options = [f"V{i}" for i in range(size)]
        weights = exploration_weights(options, "V0")
        assert weights["V0"] >= .8
        assert all(w > 0 for w in weights.values())
        assert sum(weights.values()) == 1
        assert {k: v / sum(weights.values()) for k, v in weights.items()} == weights
