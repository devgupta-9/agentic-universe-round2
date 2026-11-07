# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.278 | +12.1% | 0.201 | +9.3% | 0.481 | +1.0% | 26% | 104 (330) |
| nw_kyc | 0.374 | -0.2% | 0.240 | -0.9% | 0.595 | +0.6% | 0% | 36 (31) |
| nw_renewal | 0.432 | +1.2% | 0.261 | -0.2% | 0.552 | +0.7% | 4% | 54 (55) |
| ALL | 0.349 | +4.5% | 0.229 | +3.3% | 0.532 | +0.4% | 12% | 194 (416) |

## Changes applied by the controller

4 applied — neutral: 2, beneficial: 2

- nw_renewal v2 (controller_approved) dims=['voice'] engageΔ=-0.005 didΔ=+0.000 → **neutral**
- ks_cancel v2 (controller_approved) dims=['voice'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- ks_cancel v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.482 → **beneficial**
- ks_cancel v5 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 4,
  "decisions": {
    "approved": 4,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 4,
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
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.255,
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
    "mttr_minutes": 1590,
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