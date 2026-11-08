# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.346 | +1.4% | 0.246 | +0.9% | 0.501 | +0.2% | 3% | 354 (408) |
| arav_kyc_1 | 0.353 | -0.3% | 0.214 | -0.3% | 0.595 | -0.0% | 0% | 393 (370) |
| arav_renewal_0 | 0.405 | +0.8% | 0.265 | +0.2% | 0.547 | +0.6% | 0% | 441 (440) |
| kest_cancel_2 | 0.341 | +0.5% | 0.244 | +0.3% | 0.502 | +0.6% | 3% | 418 (411) |
| kest_kyc_1 | 0.354 | +0.3% | 0.213 | -0.2% | 0.595 | +0.1% | 0% | 314 (339) |
| kest_renewal_0 | 0.402 | +0.7% | 0.264 | +0.3% | 0.545 | +0.5% | 0% | 447 (433) |
| nort_cancel_2 | 0.342 | +1.0% | 0.245 | +0.9% | 0.500 | +0.2% | 3% | 389 (393) |
| nort_kyc_1 | 0.354 | -0.1% | 0.214 | +0.2% | 0.597 | +0.2% | 0% | 374 (323) |
| nort_renewal_0 | 0.406 | +0.3% | 0.264 | +0.3% | 0.549 | +0.3% | 0% | 435 (411) |
| tide_cancel_2 | 0.353 | +4.0% | 0.243 | -0.3% | 0.515 | +3.2% | 26% | 399 (407) |
| tide_kyc_1 | 0.357 | +1.1% | 0.215 | +0.1% | 0.595 | +0.5% | 0% | 317 (356) |
| tide_renewal_0 | 0.404 | +0.8% | 0.264 | +0.0% | 0.545 | +0.5% | 0% | 429 (438) |
| ALL | 0.368 | +0.9% | 0.241 | +0.2% | 0.547 | +0.6% | 2% | 4710 (4729) |

## Changes applied by the controller

9 applied — neutral: 8, beneficial: 1

- tide_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nort_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nort_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- kest_cancel_2 v2 (controller_approved) dims=['voice'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- kest_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- arav_renewal_0 v2 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_cancel_2 v3 (controller_approved) dims=['voice'] engageΔ=+0.064 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 9,
  "decisions": {
    "approved": 9,
    "expired": 0
  },
  "rejection_reasons": {},
  "applied_via_approval": 9,
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