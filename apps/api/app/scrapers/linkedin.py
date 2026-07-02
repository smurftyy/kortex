"""LinkedIn scraper -- deliberately fail-closed, by design (Commit 14).

## Decision: no legitimate access exists today

- **Official API.** LinkedIn's Talent Solutions / Jobs API is not self-serve
  -- it requires an approved partner agreement, a business and legal
  relationship with LinkedIn, not something obtainable by signing up for an
  API key. No such agreement exists for this project.
- **Direct scraping of linkedin.com.** Explicitly rejected, whether or not
  it involves logging in. It violates LinkedIn's User Agreement (Section
  8.2, prohibiting scraping) and carries real litigated legal exposure
  (LinkedIn has sued over exactly this, e.g. *hiQ Labs v. LinkedIn*). Even
  ignoring the legal exposure, it would be the most technically fragile of
  all seven sources: auth walls, aggressive rate-limiting/CAPTCHA, and
  structural changes that can silently break selectors overnight.
- **Third-party aggregator API.** Not currently subscribed to. Building
  against a specific vendor's request/response shape today, with no account
  or contract, would mean writing a parser against a schema that doesn't
  exist -- speculative, so rejected for now.

Given that, this scraper is fail-closed by design: it makes zero network
requests and immediately reports the source as inaccessible. This is not a
placeholder awaiting a follow-up patch -- it is the correct, permanent
behavior until the project has actual compliant access.

**What would change this:** an approved LinkedIn Talent Solutions / Jobs API
partner agreement. That's a different order of magnitude from this
project's other known scraper follow-ups -- e.g. Web3.career needing a free
API token signup, or Cryptojobslist needing headless-browser tooling. Both
of those are engineering tasks one person can complete alone. LinkedIn's is
a business/legal negotiation with LinkedIn itself; no amount of engineering
work on this codebase flips this scraper from disabled to live.
"""

from __future__ import annotations

from typing import Any

from app.scrapers.base import BaseScraper, PermanentlyExcludedSourceError
from app.scrapers.schemas import NormalizedJob


class LinkedInAccessDeniedError(PermanentlyExcludedSourceError):
    """Raised by LinkedInScraper.fetch()/parse() -- see module docstring for
    why LinkedIn has no accessible data source for this project."""


class LinkedInScraper(BaseScraper):
    """Fail-closed by design -- see module docstring. Never makes a network
    request; `fetch()` raises before touching `self.http`."""

    source_board = "linkedin"

    async def fetch(self) -> Any:
        raise LinkedInAccessDeniedError(
            "LinkedIn has no compliant data source configured for this "
            "project (no partner API access; direct scraping is "
            "deliberately excluded -- see module docstring). This is the "
            "permanent state, not a transient outage."
        )

    def parse(self, raw: Any) -> list[NormalizedJob]:
        # Unreachable in normal operation -- run() calls fetch() first, and
        # fetch() always raises. Implemented defensively in case parse() is
        # ever called directly (as the RemoteOK test suite does against a
        # fixture), so it fails the same documented way rather than
        # crashing on the shape of `raw` or silently returning [].
        raise LinkedInAccessDeniedError(
            "LinkedIn has no compliant data source configured for this "
            "project -- parse() should be unreachable; see module "
            "docstring."
        )
