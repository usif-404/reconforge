---
name: js-analysis
description: Extracting API routes, role checks, feature flags, and authorization-relevant logic from new or changed JavaScript
---

# JavaScript Analysis

You only ever see files that are NEW or whose content hash CHANGED since the
last run — never the full historical corpus. Every file handed to you is
already worth reading. Extract signal, don't summarize the whole file.

## What to extract, in priority order

1. **Role-comparison logic** — any conditional comparing a role/permission
   string, e.g. `if (user.role === "SUPPORT_AGENT")`. These are the single
   highest-value extraction: they reveal role names that exist in the system
   (useful for horizontal/vertical privilege testing) and the exact
   endpoints those roles are permitted to call.
2. **API routes and GraphQL operations** — every `fetch`/`axios`/`api.post`
   call target, every `gql` tagged template operation name and type
   (query/mutation/subscription).
3. **Object ID patterns used in requests** — path params or body fields like
   `customerId`, `orderId`, `accountId` passed into a call. These become
   candidates for ID-substitution testing downstream.
4. **Feature flags** — flag names often gate unreleased functionality that
   is still reachable if you know the flag or the endpoint it protects.
5. **Upload/export/admin endpoint references** not visible from crawled
   HTML alone (client-side-only routes, hidden admin panels reachable by
   direct API call even if there's no visible UI link).
6. **Internal terminology** — words that clearly aren't meant for end users
   (internal codenames, ops-team language) — these often correlate with
   under-tested internal-only features exposed by mistake.

## Example (illustrative pattern, not a literal template to search for)

A conditional gating an impersonation-style call by a role string is the
textbook high-value find:

```
if (user.role === "SUPPORT_AGENT") {
    return api.post("/accounts/impersonate", { customerId: id });
}
```

This should be flagged as `role_check` + `api_route`, with suggested manual
tests: authorization boundary (call `/accounts/impersonate` without the
support role), horizontal boundary (substitute a `customerId` you don't
own), vertical boundary (attempt as an unauthenticated or lower-privilege
session).

## Validation before flagging

- Confirm the route string is actually a network call target, not a UI route
  (client-side router paths look similar but aren't API endpoints).
- Minified/bundled code: role and endpoint strings usually survive
  minification (string literals aren't renamed), but variable/function names
  won't be meaningful — don't over-interpret minified identifier names.

## False Positives

- Analytics/tracking endpoint calls (`/analytics/event`, `/telemetry`) —
  numerous and almost never security-relevant.
- Third-party SDK boilerplate bundled into the file (Stripe.js, Google
  Analytics, Segment) — filter by first checking if the code looks
  vendored vs. application-authored.

## Summary

Read for role logic and endpoint/ID patterns first — that's where
authorization bugs get discovered. Everything else is secondary.
