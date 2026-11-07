# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.345 | +1.0% | 0.244 | +0.1% | 0.504 | +0.7% | 9% | 386 (408) |
| arav_kyc_1 | 0.356 | +0.7% | 0.214 | -0.2% | 0.598 | +0.5% | 0% | 333 (370) |
| arav_renewal_0 | 0.407 | +1.1% | 0.264 | +0.1% | 0.548 | +0.9% | 0% | 410 (440) |
| kest_cancel_2 | 0.344 | +1.5% | 0.243 | -0.1% | 0.505 | +1.3% | 8% | 391 (411) |
| kest_kyc_1 | 0.354 | +0.3% | 0.214 | +0.1% | 0.593 | -0.1% | 0% | 337 (339) |
| kest_renewal_0 | 0.401 | +0.3% | 0.264 | +0.1% | 0.545 | +0.5% | 0% | 408 (433) |
| nort_cancel_2 | 0.343 | +1.2% | 0.245 | +0.9% | 0.501 | +0.5% | 3% | 389 (393) |
| nort_kyc_1 | 0.354 | -0.0% | 0.214 | +0.4% | 0.595 | -0.0% | 0% | 340 (323) |
| nort_renewal_0 | 0.405 | +0.1% | 0.264 | +0.3% | 0.548 | -0.0% | 0% | 423 (411) |
| tide_cancel_2 | 0.348 | +2.6% | 0.243 | -0.3% | 0.511 | +2.4% | 17% | 408 (407) |
| tide_kyc_1 | 0.353 | -0.2% | 0.214 | -0.4% | 0.590 | -0.3% | 0% | 348 (356) |
| tide_renewal_0 | 0.402 | +0.4% | 0.264 | +0.1% | 0.543 | +0.1% | 0% | 402 (438) |
| ALL | 0.368 | +0.7% | 0.241 | +0.1% | 0.547 | +0.5% | 2% | 4575 (4729) |

## Changes applied by the controller

11 applied — neutral: 8, beneficial: 3

- arav_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nort_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nort_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- arav_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- tide_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- kest_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_cancel_2 v3 (controller_approved) dims=['voice'] engageΔ=+0.064 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v3 (controller_approved) dims=['voice'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**
- kest_cancel_2 v3 (controller_approved) dims=['voice'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 11,
  "decisions": {
    "approved": 11,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 11,
  "auto_applied": 0,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "arav_cancel_2": 1,
    "arav_renewal_0": 1,
    "nort_cancel_2": 1,
    "nort_renewal_0": 1,
    "tide_cancel_2": 1,
    "tide_renewal_0": 1,
    "kest_cancel_2": 1,
    "kest_renewal_0": 1
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