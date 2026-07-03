"""Cryptojobslist scraper -- deliberately fail-closed, for now.

See docs/superpowers/specs/2026-07-03-cryptojobslist-scraper-design.md for
the full investigation. Summary:

- `robots.txt` explicitly `Disallow`s `/api/` -- whatever lives there isn't
  offered for programmatic use.
- `/jobs/` is explicitly `Allow`'d in `robots.txt`, and the officially
  linked feed at `https://api.cryptojobslist.com/rss.xml` (advertised on the
  homepage itself, "RSS feed") looked like a real, sanctioned integration
  point -- the Web3.career-shaped outcome. Live-testing both found the same
  problem: every content path (`/jobs/`, `sitemap.xml`, the RSS feed) is
  behind Cloudflare bot management (`cf-mitigated: challenge` on responses
  to a plain, honestly-identified HTTP client), and the RSS feed
  specifically returns `200` with zero `<item>` entries on `GET` and a
  Cloudflare challenge on `HEAD` -- not a stable, fetchable data source
  either way.
- This project's `ScraperHTTPClient` (`app/scrapers/http.py`) is a plain
  `httpx.AsyncClient` with no JavaScript execution -- it cannot pass a
  Cloudflare browser challenge by construction, regardless of headers/UA
  tuning. `app/scrapers/linkedin.py`'s own module docstring already flagged
  this exact gap when it was written ("Cryptojobslist needing
  headless-browser tooling"); this investigation confirms it.

## Why this reuses LinkedIn's fail-closed pattern, but isn't the same kind
## of exclusion

Unlike `LinkedInScraper` (a business/legal wall -- no engineering fixes a
missing partner agreement), Cryptojobslist's blocker is a tooling gap: a
JS-capable headless browser (e.g. Playwright/Chromium) would get past a
bot-management JS challenge the way a real browser does. That's real,
buildable engineering work this project could do -- it just doesn't fit
`BaseScraper`/`ScraperHTTPClient`'s "one HTTP request in, one HTTP response
out" contract (a headless browser isn't an `httpx.AsyncBaseTransport`), so
it's a separate architecture change, not this commit's scope.
`CryptojobslistHeadlessBrowserRequiredError` is a distinct subclass from
`LinkedInAccessDeniedError` so this distinction stays visible in code, even
though both are `PermanentlyExcludedSourceError` today.

**What would change this:** headless-browser tooling wired into a
`BaseScraper`-compatible fetch path. Until then this is the correct
behavior, not a placeholder silently returning `[]`.
"""

from __future__ import annotations

from typing import Any

from app.scrapers.base import BaseScraper, PermanentlyExcludedSourceError
from app.scrapers.schemas import NormalizedJob


class CryptojobslistHeadlessBrowserRequiredError(PermanentlyExcludedSourceError):
    """Raised by CryptojobslistScraper.fetch()/parse() -- see module
    docstring for why Cryptojobslist has no plain-HTTP-client-accessible
    data source for this project today."""


class CryptojobslistScraper(BaseScraper):
    """Fail-closed by design -- see module docstring. Never makes a network
    request; `fetch()` raises before touching `self.http`."""

    source_board = "cryptojobslist"

    async def fetch(self) -> Any:
        raise CryptojobslistHeadlessBrowserRequiredError(
            "Cryptojobslist has no plain-HTTP-client-accessible data source "
            "for this project (every content path -- HTML pages, sitemap, "
            "the linked RSS feed -- sits behind Cloudflare bot management "
            "that challenges non-browser clients; see module docstring). "
            "This requires headless-browser tooling this project does not "
            "yet have, not a transient outage."
        )

    def parse(self, raw: Any) -> list[NormalizedJob]:
        # Unreachable in normal operation -- run() calls fetch() first, and
        # fetch() always raises. Implemented defensively in case parse() is
        # ever called directly against a fixture, so it fails the same
        # documented way rather than crashing on the shape of `raw` or
        # silently returning [].
        raise CryptojobslistHeadlessBrowserRequiredError(
            "Cryptojobslist has no plain-HTTP-client-accessible data source "
            "for this project -- parse() should be unreachable; see module "
            "docstring."
        )
