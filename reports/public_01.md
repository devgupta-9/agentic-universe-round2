# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.348 | +4.6% | 0.242 | +1.5% | 0.503 | +2.4% | 4% | 58 (47) |
| nw_kyc | 0.363 | -0.2% | 0.238 | -1.6% | 0.600 | +1.6% | 0% | 20 (21) |
| nw_renewal | 0.414 | -1.4% | 0.260 | -1.4% | 0.548 | +0.4% | 0% | 44 (42) |
| ALL | 0.373 | +1.3% | 0.247 | -0.2% | 0.537 | +1.4% | 1% | 122 (110) |

## Changes applied by the controller

2 applied — neutral: 2

- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 2,
  "decisions": {
    "approved": 2,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 2,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nw_renewal": 1,
    "ks_cancel": 1
  }
}
```

## Incidents

```
[]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0