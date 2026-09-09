---
name: api-discovery
description: Recognizing REST/GraphQL API surface worth deeper attention from swagger/openapi specs, kiterunner results, and endpoint naming conventions
---

# API Discovery

Modern applications' real attack surface is mostly API, not rendered HTML.
Your job is spotting which discovered API surface is worth prioritizing —
not cataloguing every endpoint.

## High-value signals

- **Versioned API changes**: a new `/api/v4/` appearing alongside an
  existing `/api/v3/` often means a rewritten, less-tested implementation of
  existing functionality — compare which endpoints exist in the new version
  vs old for ones that dropped an authorization check that existed before.
- **Exposed API documentation**: `/swagger.json`, `/openapi.yaml`,
  `/api-docs`, GraphQL introspection left enabled. These hand you the entire
  contract — every declared endpoint, param, and type — without having to
  discover it by crawling.
- **Internal/admin-prefixed API paths**: `/api/internal/`,
  `/api/admin/`, `/api/_internal/` discovered via kiterunner wordlists or JS
  extraction — internal APIs are frequently built with looser authorization
  assumptions ("no external user will ever call this directly").
- **Mobile-only API paths**: endpoints only referenced from a mobile app
  bundle (not the web JS) sometimes have weaker web-side protections since
  they weren't designed with browser-based attacks in mind.

## Methodology

1. When a swagger/openapi spec is found, diff its declared endpoint list
   against what's already in the `api_endpoints` table — every declared
   endpoint not yet tested is a queue candidate.
2. When a new API version appears, structurally diff the endpoint list
   against the previous version rather than treating it as a fresh surface.
3. Correlate kiterunner/content-discovery hits with JS-extracted routes —
   an endpoint found both ways is confirmed reachable, higher confidence
   than either source alone.

## False Positives

- Auto-generated framework default routes (health checks, metrics endpoints
  like `/actuator`, `/healthz`) — usually low value unless they leak
  configuration/environment data (which is its own `information_disclosure`
  concern, not an API-surface one).

## Summary

Prioritize new API versions, exposed specs, internal-prefixed paths, and
mobile-only endpoints — these consistently carry weaker authorization
assumptions than the well-trodden public web API surface.
