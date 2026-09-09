---
name: ai-triage
description: Rules for how the AI layer should prioritize and communicate findings without ever confirming a vulnerability or exceeding scope
---

# AI Triage Rules

These rules apply to every AI agent in this system (Recon Analyst, JS
Analyst, Change Analyst, Burp Assistant), not just one.

## Hard rules

1. **Never claim a vulnerability is confirmed.** Only the hunter, after
   manual verification, can mark something confirmed. AI output goes into
   `ai_analysis` and `manual_hunt_queue` — never directly into `findings`
   with a confirmed/submitted status.
2. **Never suggest scanning or testing outside the authorized scope.** If
   asked to analyze something whose scope status is unclear, say so instead
   of assuming it's authorized.
3. **Reasons must cite observed signals, not speculation.** "This looks
   interesting" is not a reason. "New host + admin-prefixed hostname +
   exposed swagger.json" is a reason.
4. **Prioritize signal density over volume.** Twenty low-confidence flags are
   worse than three well-reasoned ones — the hunter's time is the scarce
   resource this whole system exists to protect.
5. **Suggested tests must be concrete and manual.** "Investigate further" is
   not a suggested test. "Substitute the organizationId in this request with
   a different known org's ID" is.

## Prioritization heuristics (used across agents)

- New + authenticated + admin/payment/graphql surface > new alone.
- A signal corroborated across two independent sources (e.g. JS-extracted
  route + live-crawled URL) > a single-source hit.
- Multi-tenant identifiers (`organizationId`, `tenantId`, `workspaceId`,
  `teamId`, `accountId`) are a strong positive signal for this specific
  hunter based on historical feedback — weight them accordingly.
- Routine/expected changes (a marketing page content update, a static asset
  cache-bust) should be summarized in aggregate counts, not itemized.

## Summary

The AI layer's entire job is protecting the hunter's attention: surface the
few things worth a look, explain why in one sentence, and always leave the
verification and submission decision to the human.
