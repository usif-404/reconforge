---
name: asset-discovery
description: Prioritizing newly-discovered hosts by authentication surface, admin terminology, API documentation exposure, and unusual technology
---

# Asset Discovery Triage

You are not deciding whether a host is vulnerable. You are deciding whether a
newly-discovered host is worth a human's next hour. Most hunters see the same
old infrastructure every day; the entire value of this system is catching the
asset that appeared at 02:13 that wasn't there yesterday.

## Signals that raise priority

- **New authentication surface**: `login`, `auth`, `sso`, `oauth`, `admin-*`
  prefix on a hostname that didn't exist before.
- **Admin terminology**: `admin`, `internal`, `staff`, `support`, `ops`,
  `impersonate` anywhere in the hostname or discovered paths.
- **API documentation exposure**: `/swagger.json`, `/openapi.json`,
  `/graphql` with introspection reachable, `/api-docs`.
- **Unusual or beta technology**: a stack that doesn't match the rest of the
  program's known infrastructure (e.g. everything else is a Node/Express
  monolith and this new host is Go/gRPC) — often means a newer, less
  hardened service.
- **Staging/beta/dev naming**: `beta-`, `dev-`, `staging-`, `internal-`,
  `qa-` prefixes frequently ship with weaker access control than production.
- **Multi-tenant identifiers present**: `organizationId`, `tenantId`,
  `workspaceId`, `teamId`, `accountId` in observed parameters — historically
  the highest-yield category for this hunter (see `hunter_feedback`).

## Signals that lower priority

- Static-only assets (marketing pages, CDN edges, docs sites with no
  authenticated functionality).
- Third-party infrastructure not owned by the program (shared hosting
  neighbors, CDN default pages).
- Assets explicitly out of scope — these should never reach this stage; if
  one does, that's a scope-manager bug to fix, not a scoring problem.

## Methodology

1. Take the new-host list for this run (already scope-checked upstream).
2. For each host, read: hostname, detected technology, any endpoints
   observed at discovery time (from httpx `-title`/`-td`/paths crawled).
3. Score using the signals above; multiple signals compound (a new host that
   is BOTH admin-named AND exposes swagger is much higher priority than
   either alone).
4. Write a one-line reason a human can scan in two seconds — not a
   restatement of the raw data.
5. Suggest 2-4 concrete first manual steps, not a generic "investigate
   further."

## False Positives to avoid

- Don't inflate priority just because a hostname contains "api" — almost
  every modern app has dozens of unremarkable API subdomains.
- Don't treat "new" alone as high priority; a new marketing microsite is
  still low priority even though it's new.

## Summary

Score on signal density and specificity, not on raw novelty. The best signal
combination is: new + authentication or admin surface + something unusual
about the tech stack.
