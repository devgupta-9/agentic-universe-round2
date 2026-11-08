# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.343 | +0.4% | 0.241 | +0.7% | 0.500 | +0.1% | 3% | 53 (52) |
| nw_kyc | 0.361 | -4.3% | 0.240 | -0.7% | 0.598 | -2.4% | 0% | 24 (21) |
| nw_renewal | 0.422 | +0.4% | 0.258 | -1.5% | 0.557 | +1.8% | 0% | 50 (39) |
| ALL | 0.373 | -0.6% | 0.247 | -0.4% | 0.539 | +0.2% | 1% | 127 (112) |

## Changes applied by the controller

2 applied — neutral: 2

- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
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