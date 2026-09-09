---
name: url-discovery
description: Classifying discovered URLs into risk-relevant categories and deciding which deserve deeper crawling or JS analysis
---

# URL Discovery & Classification

Discovered URLs arrive from archives (waybackurls/gau/waymore) and live
crawling (katana/hakrawler/gospider), already regex-classified by
`url_classification.py` into: javascript, api, auth, admin, upload_download,
sensitive_files, idor_candidate, cloud, backend_files. Your job is the
judgment pass the regex can't do: which categorized URLs actually matter
given the surrounding context.

## Signals to look for

- A URL with an `idor_candidate` tag (numeric ID or `id=`/`user_id=`
  parameter) on an endpoint that also looks authenticated (returns 200 only
  with a session cookie/bearer token) — this is the strongest recon-stage
  signal for downstream IDOR/BOLA testing.
- `sensitive_files` hits that are NOT expected boilerplate (a `.git/` on a
  marketing site is routine to check but rarely fruitful; a `.env` reference
  on an app subdomain is worth immediate attention).
- Endpoints under `admin` or `internal` categories that returned any
  non-403/401 status during passive discovery.
- `backend_files` categories (`.php`, `.aspx`, `.jsp`) on hosts that are
  otherwise modern SPA/API stacks — often legacy, unmaintained code paths.

## Methodology

1. Group classified URLs by category, then by host.
2. Within `api` and `idor_candidate`, prioritize URLs with a fresh
   `first_seen` (new this run) over long-known ones — those have likely
   already been checked by you or other hunters.
3. Cross-reference `admin`/`auth` categorized URLs against the JS Analyst's
   extracted role-check findings for the same host — a URL matching a role
   string extracted from JS (e.g. `SUPPORT_AGENT`) is much higher signal.

## False Positives

- Wayback/archive results are frequently stale — a URL appearing in
  waybackurls output may 404 today. Don't score archive-only hits as highly
  as live-crawl hits until confirmed live.
- Generic REST collection endpoints (`/api/products`) without an ID or
  auth-gated response are low priority on their own.

## Summary

Classification narrows 38,000 URLs to a few hundred worth a second look;
your job is picking the handful worth a human's first look, weighted toward
freshness, authentication gating, and cross-signal correlation with JS
findings.
