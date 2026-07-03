"""Tests for job scoring (app/scrapers/scoring.py).

See that module's docstring for the normalization/tier/recency decisions
this exercises -- in particular the recency-ambiguity resolution (non-
additive, best-tier-only) and the TIER1/TIER2 skill classification (project
-level constants intersected with the user's own `profile.skills`, since
the schema has no per-skill tiering column).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.schemas.preferences import PreferencesResponse
from app.schemas.profile import ProfileResponse
from app.scrapers.schemas import NormalizedJob
from app.scrapers.scoring import (
    HARD_EXCLUDE_SCORE,
    TIER1_SKILLS,
    TIER2_SKILLS,
    score_job,
)

_NOW = datetime(2026, 7, 3, tzinfo=UTC)


def _job(
    *,
    title: str = "Backend Developer",
    description: str = "A great opportunity.",
    location: str | None = None,
    apply_url: str = "https://example.com/jobs/1",
    posted_at: datetime | None = None,
) -> NormalizedJob:
    return NormalizedJob(
        source_board="greenhouse",
        title=title,
        company="Acme",
        location=location,
        description=description,
        apply_url=apply_url,
        posted_at=posted_at,
    )


def _profile(
    *,
    skills: list[str] | None = None,
    experience_level: str = "mid",
) -> ProfileResponse:
    return ProfileResponse(
        id="11111111-1111-1111-1111-111111111111",
        full_name="Test User",
        experience_level=experience_level,  # type: ignore[arg-type]
        target_roles=[],
        skills=skills or [],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _preferences(
    *,
    location_filter: list[str] | None = None,
    excluded_keywords: list[str] | None = None,
) -> PreferencesResponse:
    return PreferencesResponse(
        id="22222222-2222-2222-2222-222222222222",
        user_id="11111111-1111-1111-1111-111111111111",
        boards_enabled=["greenhouse"],
        location_filter=location_filter or [],
        excluded_keywords=excluded_keywords or [],
        digest_time_local="08:00",
        digest_timezone="Africa/Lagos",
        match_score_threshold=2.0,
        created_at=_NOW,
        updated_at=_NOW,
    )


# --- skill keyword match: TIER1 / TIER2 --------------------------------------


def test_tier1_skill_match_scores_3_points() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(title=f"{tier1_skill.title()} Developer")
    profile = _profile(skills=[tier1_skill])
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 3.0


def test_tier2_skill_match_scores_2_points() -> None:
    tier2_skill = next(iter(TIER2_SKILLS))
    job = _job(title=f"{tier2_skill.title()} Developer")
    profile = _profile(skills=[tier2_skill])
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 2.0


def test_skill_not_in_users_profile_does_not_score_even_if_in_tier_list() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(title=f"{tier1_skill.title()} Developer")
    profile = _profile(skills=[])  # user does not claim this skill
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 0.0


def test_skill_match_only_counted_once_per_skill_even_if_mentioned_twice() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(
        title=f"{tier1_skill.title()} Developer",
        description=f"You will use {tier1_skill} every day.",
    )
    profile = _profile(skills=[tier1_skill])
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 3.0


# --- internship/junior signal -------------------------------------------------


def test_internship_signal_in_title_scores_5_points() -> None:
    job = _job(title="Software Engineering Intern")
    profile = _profile(skills=[])
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 5.0


# --- location match -----------------------------------------------------------


def test_location_match_scores_3_points() -> None:
    job = _job(location="Remote")
    profile = _profile()
    preferences = _preferences(location_filter=["remote"])

    assert score_job(job, profile, preferences, now=_NOW) == 3.0


def test_location_mismatch_scores_0() -> None:
    job = _job(location="Berlin, Germany")
    profile = _profile()
    preferences = _preferences(location_filter=["remote", "lagos", "nigeria"])

    assert score_job(job, profile, preferences, now=_NOW) == 0.0


# --- experience level match ---------------------------------------------------


def test_experience_level_match_scores_2_points() -> None:
    """Uses a mid-level profile/title so junior-signal/tier-skill bonuses
    stay at 0 and this factor is isolated."""

    job = _job(title="Mid-Level Backend Engineer")
    profile = _profile(experience_level="mid")
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 2.0


def test_experience_level_mismatch_scores_0() -> None:
    job = _job(title="Backend Engineer")  # no level signal at all
    profile = _profile(experience_level="mid")
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 0.0


# --- recency -------------------------------------------------------------------


def test_recency_within_3_days_scores_2_points() -> None:
    job = _job(posted_at=_NOW - timedelta(days=1))
    profile = _profile()
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 2.0


def test_recency_within_7_days_scores_1_point() -> None:
    job = _job(posted_at=_NOW - timedelta(days=5))
    profile = _profile()
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 1.0


def test_recency_older_than_7_days_scores_0() -> None:
    job = _job(posted_at=_NOW - timedelta(days=30))
    profile = _profile()
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 0.0


def test_recency_missing_posted_at_scores_0() -> None:
    job = _job(posted_at=None)
    profile = _profile()
    preferences = _preferences()

    assert score_job(job, profile, preferences, now=_NOW) == 0.0


def test_recency_ambiguity_resolved_as_non_additive_best_tier_only() -> None:
    """PRD wording ("within 7 days +1.0, within 3 days +2.0") is ambiguous:
    read literally, "posted yesterday" satisfies *both* conditions and could
    double-count to +3.0. This project's chosen resolution: non-additive,
    best (tightest) tier only -- a job posted 1 day ago scores exactly 2.0,
    never 3.0. See app/scrapers/scoring.py's module docstring."""

    job = _job(posted_at=_NOW - timedelta(days=1))
    profile = _profile()
    preferences = _preferences()

    score = score_job(job, profile, preferences, now=_NOW)

    assert score == 2.0
    assert score != 3.0  # would be the (rejected) additive reading


# --- hard excludes --------------------------------------------------------------


def test_excluded_keyword_hit_hard_excludes_even_with_other_positive_factors() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(
        title=f"{tier1_skill.title()} Intern",
        description="Paid in crypto only.",
        location="Remote",
        posted_at=_NOW,
    )
    profile = _profile(skills=[tier1_skill], experience_level="intern")
    preferences = _preferences(location_filter=["remote"], excluded_keywords=["crypto"])

    assert score_job(job, profile, preferences, now=_NOW) == HARD_EXCLUDE_SCORE


def test_seniority_signal_hard_excludes_even_with_other_positive_factors() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(
        title=f"Senior {tier1_skill.title()} Engineer",
        location="Remote",
        posted_at=_NOW,
    )
    profile = _profile(skills=[tier1_skill])
    preferences = _preferences(location_filter=["remote"])

    assert score_job(job, profile, preferences, now=_NOW) == HARD_EXCLUDE_SCORE


def test_hard_exclude_returns_score_rather_than_raising() -> None:
    job = _job(title="Senior Engineer")
    profile = _profile()
    preferences = _preferences()

    result = score_job(job, profile, preferences, now=_NOW)

    assert isinstance(result, float)
    assert result == HARD_EXCLUDE_SCORE


# --- combined --------------------------------------------------------------------


def test_combined_factors_sum_correctly() -> None:
    tier1_skill = next(iter(TIER1_SKILLS))
    job = _job(
        title=f"{tier1_skill.title()} Intern",
        description="Join our team.",
        location="Remote",
        posted_at=_NOW - timedelta(days=1),
    )
    profile = _profile(skills=[tier1_skill], experience_level="intern")
    preferences = _preferences(location_filter=["remote"])

    # tier1 skill (3.0) + internship signal (5.0) + location match (3.0)
    # + experience level match (2.0) + recency within 3 days (2.0)
    assert score_job(job, profile, preferences, now=_NOW) == 15.0
