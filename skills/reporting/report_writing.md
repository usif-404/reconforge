---
name: report-writing
description: Checklist for writing a submission-ready report after a finding is manually confirmed, optimizing for validity and reviewer speed
---

# Report Writing Checklist

This skill is not invoked by an AI agent that submits anything — no agent in
this system writes to a platform. It's a checklist for you, the human, once
a `Finding` has moved to `confirmed` status and you're about to write it up.

Per HackerOne's own guidance referenced in the methodology: automated,
low-signal scanner reports are unacceptable, and reputation is weighted by
validity, criticality, and bounty size — not report count. Every report
should read like it took real understanding of the application to produce.

## Before writing

- Reproduce the finding a second time, from a clean state, to rule out a
  fluke (session state leftover from earlier testing, a race you triggered
  accidentally, a cached response).
- Confirm actual impact — what specifically can be read, modified, or done
  that shouldn't be possible, not just "the request succeeded."

## Report structure

1. **Summary** — one or two sentences: what the vulnerability is and its
   impact, in plain language a non-technical triager could understand.
2. **Steps to reproduce** — numbered, minimal, and literal. Include exact
   requests (method, path, headers that matter, body) rather than prose
   descriptions of what to click.
3. **Proof of concept** — request/response pairs or a short video/screenshot
   sequence showing the boundary being crossed (e.g. Account A's token
   retrieving Account B's data).
4. **Impact** — be specific and proportionate. Don't inflate a low-impact
   IDOR into "complete account takeover" language it doesn't support.
5. **Suggested remediation** — a short, concrete suggestion (e.g. "enforce
   organization_id scoping on this query") shows you understood the root
   cause, not just the symptom.

## Before submitting

- Re-check the program's current scope and policy page — scope changes
  over time, and what was authorized when you started testing may have
  changed.
- Confirm this isn't a duplicate — search Hacktivity/your own knowledge base
  for similar prior reports on the same program.

## Summary

A report that reads like it required real application understanding — not a
raw scanner output — is both more likely to be accepted quickly and better
for long-term reputation than a higher volume of thinner reports.
