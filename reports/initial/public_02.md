# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.291 | +17.5% | 0.205 | +11.8% | 0.494 | +3.7% | 30% | 97 (330) |
| nw_kyc | 0.376 | +0.2% | 0.245 | +1.3% | 0.594 | +0.3% | 0% | 36 (31) |
| nw_renewal | 0.436 | +2.2% | 0.267 | +2.0% | 0.545 | -0.5% | -2% | 69 (55) |
| ALL | 0.357 | +6.9% | 0.234 | +5.6% | 0.534 | +0.8% | 11% | 202 (416) |

## Changes applied by the controller

5 applied — neutral: 1, harmful: 2, beneficial: 2

- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=-0.012 didΔ=+0.000 → **harmful**
- ks_cancel v3 (controller_approved) dims=['voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.480 → **beneficial**
- ks_cancel v5 (controller_approved) dims=['voice', 'prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- nw_renewal v4 (controller_approved) dims=['voice'] engageΔ=-0.029 didΔ=+0.000 → **harmful**

## Governance

```
{
  "approval_requests": 5,
  "decisions": {
    "approved": 5,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 5,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "ks_cancel": 1,
    "nw_renewal": 1
  }
}
```

## Incidents

```
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.207,
      "3": 0.0,
      "4": 0.0,
      "5": 0.0,
      "6": 0.0,
      "7": 0.0,
      "8": 0.0,
      "9": 0.0
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 450,
    "fixed_by": "controller_approved"
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D5 15:00"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 6 · validation runs: 1 · LLM fix calls: 0