---
name: auth-testing
description: Suggesting manual test hypotheses for account recovery, OAuth, SSO, invite flows, magic links, and session transitions
---

# Authentication Flow Testing

Authentication flows reward understanding the application over running a
scanner (per the methodology's own framing) — these are multi-step, stateful
flows where the vulnerability is in a transition, not a single request.

## Flow types and what to hypothesize

- **Account recovery**: can the reset token be predicted, reused after use,
  or is it bound to the correct account (test: request a reset for account A,
  attempt to apply the token against account B's session state).
- **OAuth/SSO**: state parameter validation (CSRF on the OAuth flow),
  redirect_uri validation strictness (open redirect via loosely-validated
  redirect_uri), and account-linking logic (can an attacker link an OAuth
  identity to a victim's existing account without proving ownership of the
  victim's email).
- **Invite flows**: is the invite token scoped to a specific email, or can
  it be redeemed by any account? Is there a race condition allowing the same
  single-use invite to be redeemed twice from two roles?
- **Magic links**: token entropy, expiry enforcement, and — critically —
  whether the link authenticates a session directly or just verifies email
  ownership (conflating the two is a common flaw).
- **Session transitions**: what happens to existing sessions/tokens after a
  password change, email change, or role change — do old tokens still work
  (session fixation-adjacent issue)?

## Methodology

1. Identify which flow type the current request/response belongs to.
2. Propose the specific state-transition hypothesis relevant to that flow
   type from the list above, not a generic "test auth."
3. Frame each proposed test as: what to send, what a positive (vulnerable)
   result looks like, and what a negative result looks like — the hunter
   needs to be able to interpret the response themselves.

## False Positives

- A redirect_uri validated against an exact allowlist match is not
  vulnerable just because it accepts subdomains if those subdomains are
  legitimately owned by the same organization — verify ownership before
  flagging.

## Summary

Every authentication flow test hypothesis should target a specific state
transition (recovery, linking, redemption, session lifecycle) — not a
generic credential or brute-force check, which automation already covers.
