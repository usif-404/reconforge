---
name: graphql-testing
description: Prioritizing GraphQL operations and authorization test hypotheses for mutations/queries discovered via JS extraction or introspection
---

# GraphQL Testing Priorities

GraphQL's flexible schema means authorization checks are easy to miss on any
individual field/resolver even when the overall API "looks" locked down.

## Signals to look for

- **New mutations appearing in JS** (per the methodology's own example:
  `createApiToken`, `impersonateUser`, `exportCustomerData`) — mutations are
  higher priority than queries because they cause state change or high-value
  data export.
- **Field-level authorization gaps**: a query returning a nested object
  graph may expose fields on a related type that aren't authorization-
  checked at that specific field, even if the top-level query is protected.
- **Batching/aliasing abuse potential**: multiple aliased queries in one
  request can bypass simple per-request rate limiting on brute-force-able
  fields (e.g. multiple guesses of a coupon code in a single GraphQL call).
- **Introspection left enabled in production** — hands you the entire
  schema, every type, every field, every mutation. Always worth checking if
  the program's scope permits (`GET`/`POST` introspection query).

## Methodology

1. From introspection (if available) or JS-extracted operation names, list
   every mutation first, then queries touching sensitive types (accounts,
   organizations, payments, users).
2. For each mutation, hypothesize: what authorization check would need to
   exist, and is there a way to reach it as the wrong role/tenant?
3. For nested queries, check whether authorization is enforced at the root
   field but not on nested/related object fields returned in the same
   response — this is the most GraphQL-specific class of authorization bug.

## Suggested manual tests to propose

- Call a sensitive mutation with a token from a different tenant/organization.
- Query a nested field path that traverses into another tenant's data via a
  relation (e.g. `user(id: X) { organization { members { email } } }`).
- Batch-alias the same field with different ID arguments in one request to
  probe rate-limit and IDOR-adjacent bulk access simultaneously.

## False Positives

- Public, intentionally-open queries (e.g. product catalog) are not
  authorization bugs just because they're unauthenticated by design.

## Summary

Mutations that change state or export data, and nested fields on otherwise-
protected root queries, are the two GraphQL-specific patterns worth
elevating above generic REST endpoint triage.
