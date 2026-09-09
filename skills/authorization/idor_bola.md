---
name: idor-bola
description: Building an authorization test matrix from a known account/role/organization model - token substitution, tenant boundary checks, nested resource access
---

# IDOR / BOLA Test Matrix Construction

Given a request/response and a model of known accounts, roles, and
organizations, build a concrete, prioritized matrix of authorization tests —
this is the highest-value manual testing category per the methodology
(explicitly called out as where automation is weakest).

## Building the account/role model

Maintain a running state model like:

```
USER A  -> order 83921, organization 77
USER B  -> order 99128, organization 91
ADMIN   -> organization 77
```

Every new account/session/token the hunter captures should extend this
model, not replace it — cross-account tests require at least two identities.

## Standard test matrix (adapt to the specific endpoint)

1. **Token + foreign resource**: Token A + Resource B's ID.
2. **Foreign token + own resource reference**: Token B + Resource A's ID
   (checks the inverse direction — sometimes only one direction is checked).
3. **Cross-tenant/organization ID substitution**: swap the organization ID
   in path, query, or body while keeping the same token.
4. **Remove the organization/tenant header or field entirely** — some
   implementations only enforce scoping when the field is present, and
   silently return unscoped data when it's omitted.
5. **Nested resource boundary**: for a resource reached via a parent
   (`/orgs/{orgId}/orders/{orderId}`), test substituting only the nested ID
   while keeping the parent ID correct, and vice versa.
5. **Export/download equivalents**: if a viewable resource has an export,
   PDF, or download variant, test that variant separately — it's common for
   authorization to be enforced on the view endpoint but not the export one.
6. **Method/verb variation**: the same resource path with `PUT`/`PATCH`/
   `DELETE` may have different (or missing) authorization checks than `GET`.

## What a positive result looks like

A response containing data or performing an action that belongs to a
resource/organization the current token should not have access to — not
merely a 200 status code (some APIs return 200 with an empty/error body for
denied access; verify the body content, not just the status).

## False Positives

- Publicly-shared resources (explicitly public listings, shared links with
  their own valid capability token) are not IDOR just because the ID is
  guessable — the sharing model itself needs to be evaluated separately.
- Soft-deleted or already-closed resources sometimes remain readable by
  design for audit purposes — confirm the resource is meant to be private
  before flagging.

## Summary

Two identities, one resource, six substitution directions — that matrix,
applied consistently to every newly-discovered authenticated endpoint, is
where this methodology expects most real findings to come from.
