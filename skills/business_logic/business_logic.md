---
name: business-logic
description: Identifying business-logic and race-condition test hypotheses in payments, credits, coupons, subscriptions, refunds, and approval workflows
---

# Business Logic & Race Condition Testing

These bugs live in the application's specific rules, not in generic
vulnerability classes — they reward deep understanding of what the app is
supposed to do and where the implementation might not match that intent.

## Categories and hypotheses to propose

- **Payments/credits/coupons**: can a discount be applied twice, combined
  with an incompatible discount, applied to a negative-price cart to
  generate credit, or replayed after a webhook confirms payment but before
  the order is finalized?
- **Subscriptions**: can a downgrade/cancel be timed to retain premium
  features past the billing cycle, or can a free trial be re-triggered on
  the same account/payment method?
- **Refunds**: can a refund be requested for more than the paid amount, or
  triggered twice for the same order?
- **Approval workflows**: can a step be skipped by calling a later-stage
  endpoint directly instead of going through the required sequence?
- **Role transitions**: is there a window during a role change (e.g.
  upgrade to admin pending approval) where the elevated role is already
  effective before formal approval completes?

## Race conditions — where to look

Per the methodology, prioritize action verbs that involve consuming a
limited resource: **redeem, transfer, invite, payment, withdraw, claim**.
Propose testing these with concurrent/parallel requests (multiple identical
requests fired near-simultaneously) to check whether a check-then-act
pattern (check balance, then debit) can be exploited by racing multiple
requests before the first one's state update commits.

## Methodology

1. Identify which category the current endpoint/flow belongs to.
2. State the specific business rule that should hold (e.g. "a coupon should
   be redeemable exactly once per account").
3. Propose the minimal test that would break that specific rule — not a
   generic "test for race conditions."

## False Positives

- Idempotency keys or explicit "allow multiple redemptions" business
  decisions (e.g. stackable coupons by design) aren't bugs — confirm the
  intended business rule before flagging a deviation as a finding.

## Summary

Name the specific business rule first, then design the minimal test that
would violate it — generic scanning cannot find this category, which is why
the methodology treats it as core manual-hunting territory.
