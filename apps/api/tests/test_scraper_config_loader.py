"""Tests for the shared per-source company config loader (Commit 12).

`app/scrapers/config/boards.json` is the single source of truth for which
companies each ATS scraper targets — see docs/superpowers/specs/
2026-07-02-ats-scrapers-design.md for why a flat JSON file was chosen over
a DB table or env vars.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.scrapers.config.loader import CompanyConfig, ConfigLoadError, load_companies
from pydantic import ValidationError


def _write_config(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "boards.json"
    path.write_text(json.dumps(data))
    return path


def test_load_companies_returns_configured_entries_for_source(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            "greenhouse": [
                {"slug": "stripe", "company": "Stripe"},
                {"slug": "gitlab", "company": "GitLab"},
            ],
            "lever": [{"slug": "ro", "company": "Ro"}],
        },
    )

    companies = load_companies("greenhouse", path=path)

    assert companies == [
        CompanyConfig(slug="stripe", company="Stripe"),
        CompanyConfig(slug="gitlab", company="GitLab"),
    ]


def test_load_companies_returns_empty_list_for_unconfigured_source(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"greenhouse": [{"slug": "stripe", "company": "Stripe"}]})

    companies = load_companies("workable", path=path)

    assert companies == []


def test_load_companies_raises_on_malformed_entry(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"greenhouse": [{"slug": "stripe"}]})  # missing "company"

    with pytest.raises(ValidationError):
        load_companies("greenhouse", path=path)


def test_seed_boards_json_loads_for_all_three_commit_12_sources() -> None:
    for source in ("greenhouse", "lever", "workable"):
        companies = load_companies(source)
        assert len(companies) >= 1
        assert all(isinstance(c, CompanyConfig) for c in companies)


# --- ConfigLoadError: unrecognized source ---------------------------------


def test_load_companies_raises_config_load_error_for_unknown_source(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"greenhouse": [{"slug": "stripe", "company": "Stripe"}]})

    with pytest.raises(ConfigLoadError, match="unknown source"):
        load_companies("not-a-real-source", path=path)  # type: ignore[arg-type]


# --- ConfigLoadError: missing/malformed config file -----------------------


def test_load_companies_raises_config_load_error_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.json"

    with pytest.raises(ConfigLoadError) as exc_info:
        load_companies("greenhouse", path=missing_path)

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_load_companies_raises_config_load_error_for_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "boards.json"
    path.write_text("{not valid json")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_companies("greenhouse", path=path)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


# --- ConfigLoadError: wrong-shaped data under a source key ----------------


def test_load_companies_raises_config_load_error_when_source_value_is_not_a_list(
    tmp_path: Path,
) -> None:
    path = _write_config(tmp_path, {"greenhouse": "stripe"})

    with pytest.raises(ConfigLoadError) as exc_info:
        load_companies("greenhouse", path=path)

    assert isinstance(exc_info.value.__cause__, TypeError)


def test_load_companies_raises_config_load_error_when_list_items_are_not_objects(
    tmp_path: Path,
) -> None:
    path = _write_config(tmp_path, {"greenhouse": ["stripe"]})

    with pytest.raises(ConfigLoadError) as exc_info:
        load_companies("greenhouse", path=path)

    assert isinstance(exc_info.value.__cause__, TypeError)


# --- ConfigLoadError: duplicate slug within one source --------------------


def test_load_companies_raises_config_load_error_on_duplicate_slug(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            "greenhouse": [
                {"slug": "stripe", "company": "Stripe"},
                {"slug": "stripe", "company": "Stripe Inc"},
            ]
        },
    )

    with pytest.raises(ConfigLoadError, match="duplicate slug"):
        load_companies("greenhouse", path=path)


# --- CompanyConfig field validation ----------------------------------------


def test_company_config_rejects_blank_slug() -> None:
    with pytest.raises(ValidationError):
        CompanyConfig(slug="   ", company="Acme")


def test_company_config_rejects_blank_company() -> None:
    with pytest.raises(ValidationError):
        CompanyConfig(slug="acme", company="")


def test_load_companies_raises_on_blank_slug_entry(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"greenhouse": [{"slug": "", "company": "Stripe"}]})

    with pytest.raises(ValidationError):
        load_companies("greenhouse", path=path)


def test_company_config_rejects_unexpected_extra_field() -> None:
    with pytest.raises(ValidationError):
        CompanyConfig(slug="acme", company="Acme", url="https://example.com")  # type: ignore[call-arg]


def test_load_companies_raises_on_entry_with_extra_field(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {"greenhouse": [{"slug": "stripe", "company": "Stripe", "url": "https://evil.example"}]},
    )

    with pytest.raises(ValidationError):
        load_companies("greenhouse", path=path)
