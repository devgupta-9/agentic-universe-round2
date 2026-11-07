# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.359 | +7.7% | 0.242 | +1.7% | 0.514 | +4.7% | 10% | 61 (47) |
| nw_kyc | 0.356 | -2.1% | 0.233 | -3.9% | 0.601 | +1.7% | 0% | 23 (21) |
| nw_renewal | 0.410 | -2.4% | 0.261 | -1.1% | 0.540 | -1.1% | 0% | 63 (42) |
| ALL | 0.375 | +1.8% | 0.247 | -0.4% | 0.539 | +1.8% | 3% | 147 (110) |

## Changes applied by the controller

2 applied — beneficial: 1, neutral: 1

- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.014 didΔ=+0.000 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 3,
  "decisions": {
    "approved": 2,
    "rejected": 1,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
  "applied_via_approval": 2,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "ks_cancel": 1,
    "nw_renewal": 2
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