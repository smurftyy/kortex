"""Job match scoring.

The task that requested this module cited "PRD_kortex.md section 4.4" for
the scoring table below; no file named `PRD_kortex.md` exists anywhere in
this repo (same gap already flagged in `app/scrapers/dedup.py` for section
4.3). The task's own message supplied the scoring table's numbers directly,
so this module implements those verbatim rather than guessing — but three
real gaps remain where the missing PRD would presumably have said more than
the task's summary did. Each is a documented judgment call, not a silent
guess:

## 1. TIER1 / TIER2 skill classification

Neither `SCHEMA_kortex.md` nor the migration tier `profiles.skills` at all
— it's one flat `TEXT[]`. There is no column anywhere that says which of a
user's skills counts as "TIER1" vs "TIER2". `TIER1_SKILLS`/`TIER2_SKILLS`
below are therefore **project-level constants**, not derived from any DB
column — a curated, intentionally small starting classification of which
skill keywords count as core (TIER1, +3.0) vs secondary (TIER2, +2.0),
meant to be edited/grown over time (per the task's own instruction to keep
these as named constants "since these will need tuning later without
touching scoring logic"). To keep the score personalized rather than
identical for every user, a skill only scores if it clears *two* gates: it
must be classified in one of these constants, **and** the user must
actually claim it in `profiles.skills` (case-insensitive). A claimed skill
that isn't in either constant contributes 0 under this factor — a real,
known gap of "the curated list hasn't caught up with this skill yet",
distinct from "the user doesn't have a relevant skill".

Matching is per-skill, not per-occurrence: a skill mentioned in both the
title and the description scores once, not twice — the PRD line ("+3.0 per
TIER1 match") reads as "per matched skill", not "per mention", since
counting repeated mentions of the same word in a long description would
make the score sensitive to how verbose a listing is, not how relevant it
is.

## 2. Experience-level keyword mapping

`profiles.experience_level` is a 3-value enum (`intern`/`junior`/`mid`)
with no associated keyword list anywhere in the schema for what text in a
posting should count as "matching" each level.
`EXPERIENCE_LEVEL_KEYWORDS` below is this module's own judgment call,
checked against title+description. `mid` has the weakest signal of the
three — postings rarely self-label "mid-level" the way they reliably
self-label "intern" or "senior" — which is a real, inherent limitation of
keyword matching for this level, not a bug in the keyword list.

## 3. Recency: additive vs. non-additive (flagged explicitly, per the task)

"Posted within 7 days: +1.0, within 3 days: +2.0" is ambiguous on its face
— every listing posted within 3 days is *also* within 7 days, so a literal
reading double-counts a job posted yesterday as +1.0 **and** +2.0 = +3.0.
**Decision: non-additive, best (tightest) tier only.** A job posted within
3 days scores +2.0 and *not* an additional +1.0; a job posted within 7 but
not 3 days scores +1.0; older (or `posted_at` missing entirely) scores 0.
This reads as the PRD's evident intent — two tiers of "how recent", not a
stackable bonus — but the wording gap is real and this default could be
wrong; flagging rather than silently picking the additive reading.

## Hard excludes

`preferences.excluded_keywords` (real per-user field — checked against
title+description) and a fixed `SENIORITY_EXCLUSION_KEYWORDS` constant
(title only — checking the whole description risks a false hard-exclude
from an incidental mention like "mentored by a senior engineer" in an
otherwise-junior posting; title is where a posting's own level is reliably
stated) both short-circuit to `HARD_EXCLUDE_SCORE` (-999.0) with no further
computation. This returns a score, it never raises — per `preferences.
match_score_threshold` (SCHEMA_kortex.md section 3, default 2.0),
-999 already reads as "don't show this" everywhere downstream that
compares against a threshold, without a separate error path to handle.

## Location match

`preferences.location_filter`'s own schema comment (`e.g. ['remote',
'lagos', 'nigeria']`) matches the task's scoring line verbatim
("remote/Lagos/Nigeria") — confirming `job.location` (case-insensitive
substring containment) against that real field is the intended input,
not a guess.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from app.schemas.preferences import PreferencesResponse
from app.schemas.profile import ProfileResponse
from app.scrapers.schemas import NormalizedJob

HARD_EXCLUDE_SCORE = -999.0

TIER1_SKILL_MATCH_SCORE = 3.0
TIER2_SKILL_MATCH_SCORE = 2.0
JUNIOR_SIGNAL_BONUS = 5.0
LOCATION_MATCH_BONUS = 3.0
EXPERIENCE_LEVEL_MATCH_BONUS = 2.0
RECENCY_WITHIN_3_DAYS_BONUS = 2.0
RECENCY_WITHIN_7_DAYS_BONUS = 1.0

# Project-level classification, not a DB column -- see module docstring
# section 1. Intentionally small; grow these over time as the target
# candidate pool's real stack becomes clearer.
TIER1_SKILLS: frozenset[str] = frozenset(
    {"python", "javascript", "typescript", "java", "sql", "react", "node", "git", "docker", "aws"}
)
TIER2_SKILLS: frozenset[str] = frozenset(
    {
        "html",
        "css",
        "linux",
        "agile",
        "testing",
        "graphql",
        "mongodb",
        "redis",
        "kubernetes",
        "rest",
    }
)

JUNIOR_SIGNAL_KEYWORDS: frozenset[str] = frozenset(
    {"intern", "internship", "junior", "graduate", "entry level", "entry-level", "new grad"}
)

# Title-only -- see module docstring's "Hard excludes" section for why.
SENIORITY_EXCLUSION_KEYWORDS: frozenset[str] = frozenset(
    {"senior", "lead", "principal", "staff", "director", "head of", "vp", "chief"}
)

# See module docstring section 2.
EXPERIENCE_LEVEL_KEYWORDS: dict[str, frozenset[str]] = {
    "intern": frozenset({"intern", "internship"}),
    "junior": frozenset({"junior", "entry level", "entry-level", "new grad", "graduate"}),
    "mid": frozenset({"mid level", "mid-level", "intermediate"}),
}


def _contains_keyword(text: str | None, keyword: str) -> bool:
    if not text:
        return False
    return re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE) is not None


def _contains_any(text: str | None, keywords: Iterable[str]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _location_matches(location: str | None, location_filter: list[str]) -> bool:
    if not location or not location_filter:
        return False
    location_lower = location.lower()
    return any(pref.lower() in location_lower for pref in location_filter)


def _skill_match_score(job: NormalizedJob, profile: ProfileResponse) -> float:
    text = f"{job.title} {job.description}"
    score = 0.0
    for skill in {s.lower() for s in profile.skills}:
        if skill in TIER1_SKILLS and _contains_keyword(text, skill):
            score += TIER1_SKILL_MATCH_SCORE
        elif skill in TIER2_SKILLS and _contains_keyword(text, skill):
            score += TIER2_SKILL_MATCH_SCORE
    return score


def _recency_score(posted_at: datetime | None, now: datetime) -> float:
    if posted_at is None:
        return 0.0
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)

    age = now - posted_at
    if age <= timedelta(days=3):
        return RECENCY_WITHIN_3_DAYS_BONUS
    if age <= timedelta(days=7):
        return RECENCY_WITHIN_7_DAYS_BONUS
    return 0.0


def score_job(
    job: NormalizedJob,
    profile: ProfileResponse,
    preferences: PreferencesResponse,
    *,
    now: datetime | None = None,
) -> float:
    """Score one job against one user's profile/preferences.

    Hard-exclude conditions short-circuit and return `HARD_EXCLUDE_SCORE`
    immediately -- never raises. See the module docstring for every
    normalization/tier/recency decision this encodes.
    """

    reference_time = now if now is not None else datetime.now(UTC)
    text = f"{job.title} {job.description}"

    if _contains_any(text, preferences.excluded_keywords):
        return HARD_EXCLUDE_SCORE
    if _contains_any(job.title, SENIORITY_EXCLUSION_KEYWORDS):
        return HARD_EXCLUDE_SCORE

    score = 0.0
    score += _skill_match_score(job, profile)

    if _contains_any(job.title, JUNIOR_SIGNAL_KEYWORDS):
        score += JUNIOR_SIGNAL_BONUS

    if _location_matches(job.location, preferences.location_filter):
        score += LOCATION_MATCH_BONUS

    experience_keywords = EXPERIENCE_LEVEL_KEYWORDS.get(profile.experience_level, frozenset())
    if _contains_any(text, experience_keywords):
        score += EXPERIENCE_LEVEL_MATCH_BONUS

    score += _recency_score(job.posted_at, reference_time)

    return score
