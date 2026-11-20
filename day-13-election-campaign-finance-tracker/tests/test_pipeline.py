"""Tests for Day 13 — Election Campaign Finance Tracker.

Fixture tests cover the pure finance functions; file tests verify the
committed tables against the plan's rules (candidate-totals rule §2.0,
cash identity, no-double-count per universe, nonpartisan symmetry,
data-size rule, offline reproducibility with tolerance — Day 9 lesson).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

# The day folder must be on sys.path before the src imports: the
# orchestrator runs pytest from the portfolio root (Day 12 pattern).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.finance import (
    burn_rate,
    check_cash_identity,
    other_receipts,
    party_share,
    principal_committees,
    small_dollar_share,
    top_n,
    top_n_share,
)

PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def candidates() -> pd.DataFrame:
    return pd.read_csv(PROC / "candidates.csv")


@pytest.fixture(scope="module")
def committees() -> pd.DataFrame:
    return pd.read_csv(PROC / "committees.csv")


@pytest.fixture(scope="module")
def party_office() -> pd.DataFrame:
    return pd.read_csv(PROC / "party_office.csv")


@pytest.fixture(scope="module")
def state_totals() -> pd.DataFrame:
    return pd.read_csv(PROC / "state_totals.csv")


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    record: dict[str, Any] = json.loads(
        (PROC / "data_source.json").read_text(encoding="utf-8")
    )
    return record


# --- Pure-function tests (fixtures, no files) ----------------------------


def test_small_dollar_share_basic() -> None:
    assert small_dollar_share(600.0, 400.0) == pytest.approx(0.4)
    assert small_dollar_share(0.0, 0.0) is None
    assert small_dollar_share(100.0, 0.0) == pytest.approx(0.0)


def test_burn_rate_basic() -> None:
    assert burn_rate(100.0, 80.0) == pytest.approx(0.8)
    assert burn_rate(100.0, 150.0) == pytest.approx(1.5)  # > 1 is possible
    assert burn_rate(0.0, 50.0) is None
    assert burn_rate(-10.0, 50.0) is None


def test_other_receipts_residual() -> None:
    assert other_receipts(1000.0, 700.0) == pytest.approx(300.0)
    assert other_receipts(500.0, 500.0) == pytest.approx(0.0)


def test_party_share_basic() -> None:
    assert party_share(30.0, 100.0) == pytest.approx(0.3)
    assert party_share(0.0, 0.0) == pytest.approx(0.0)


def test_top_n_share_basic() -> None:
    amounts = pd.Series([50.0, 30.0, 20.0])
    assert top_n_share(amounts, 1) == pytest.approx(0.5)
    assert top_n_share(amounts, 2) == pytest.approx(0.8)
    assert top_n_share(amounts, 3) == pytest.approx(1.0)
    assert top_n_share(pd.Series([0.0, 0.0]), 1) == pytest.approx(0.0)


def test_top_n_deterministic_tiebreak() -> None:
    df = pd.DataFrame(
        {
            "candidate_id": ["C2", "C1", "C3"],
            "receipts": [100.0, 100.0, 50.0],
        }
    )
    out = top_n(df, "receipts", 2)
    assert list(out["candidate_id"]) == ["C1", "C2"]
    assert list(out["rank"]) == [1, 2]


def test_principal_committees_set() -> None:
    df = pd.DataFrame({"principal_committee_id": ["C00000001", "", None, "C00000002"]})
    assert principal_committees(df) == {"C00000001", "C00000002"}


def test_check_cash_identity_flags_bad_row() -> None:
    good = pd.DataFrame(
        {
            "cash_bop": [100.0],
            "receipts": [50.0],
            "disbursements": [30.0],
            "cash_cop": [120.0],
        }
    )
    assert len(check_cash_identity(good)) == 0
    bad = pd.DataFrame(
        {
            "cash_bop": [100.0],
            "receipts": [50.0],
            "disbursements": [30.0],
            "cash_cop": [999.0],
        }
    )
    assert len(check_cash_identity(bad)) == 1


def test_cn_first_row_is_data_not_header() -> None:
    """Plan §3.1b: bulk files are headerless — the first cn row is a
    data row (candidate H0AK00105), never a header."""
    import zipfile

    with zipfile.ZipFile(RAW / "cn24.zip") as zf:
        first = zf.read("cn.txt").decode("utf-8").splitlines()[0]
    fields = first.split("|")
    assert fields[0] == "H0AK00105"
    assert fields[1] == "LAMB, THOMAS"
    assert fields[2] == "NNE"


# --- Committed-table tests ----------------------------------------------


def test_candidates_no_duplicate_ids(candidates: pd.DataFrame) -> None:
    assert candidates["candidate_id"].is_unique


def test_candidates_with_totals_have_receipts(
    candidates: pd.DataFrame, record: dict[str, Any]
) -> None:
    with_totals = candidates[candidates["has_totals"]]
    assert len(with_totals) == record["candidate_table"]["candidate_table_with_totals"]
    assert len(with_totals) > 4000
    assert with_totals["receipts"].notna().all()
    # One filed candidate (P40004681) reports -$0.76 receipts — an
    # amendment-rounding artifact in the FEC data, reported as filed.
    assert with_totals["receipts"].min() > -1.0


def test_candidates_without_totals_have_blank_money(
    candidates: pd.DataFrame,
) -> None:
    no_totals = candidates[~candidates["has_totals"]]
    assert len(no_totals) > 0
    assert no_totals["receipts"].isna().all()
    assert no_totals["disbursements"].isna().all()


def test_committees_exclude_principals(
    candidates: pd.DataFrame, committees: pd.DataFrame
) -> None:
    principals = principal_committees(candidates)
    assert not set(committees["committee_id"]) & principals
    assert committees["committee_id"].is_unique


def test_committee_types_mapped(
    committees: pd.DataFrame, record: dict[str, Any]
) -> None:
    """Every committee type has a full label in data_source.json, and the
    label is kept in top_committees.csv (committees.csv drops the long
    label to stay under 1 MB — plan §11 item 21)."""
    mapping = record["committee_type_full_mapping"]
    assert set(committees["committee_type"]) <= set(mapping)
    top = pd.read_csv(PROC / "top_committees.csv")
    assert top["committee_type_full"].notna().all()
    assert set(committees["committee_type"]) <= {
        "C",
        "D",
        "E",
        "H",
        "I",
        "N",
        "O",
        "P",
        "Q",
        "S",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    }


def test_party_table_includes_every_party(
    candidates: pd.DataFrame, party_office: pd.DataFrame
) -> None:
    """Nonpartisan symmetry: no party present in the candidate table is
    dropped from the party × office table."""
    parties = set(candidates[candidates["has_totals"]]["party"].dropna())
    assert parties <= set(party_office["party"])
    assert party_office["receipts_share"].sum() == pytest.approx(1.0, abs=1e-6)


def test_state_totals_sum_to_candidate_total(
    candidates: pd.DataFrame,
    state_totals: pd.DataFrame,
    record: dict[str, Any],
) -> None:
    """State table + excluded 00/US-coded candidates = candidate total."""
    total = float(candidates["receipts"].fillna(0).sum())
    excluded = float(record["state_table"]["excluded_receipts_usd"])
    assert state_totals["receipts"].sum() + excluded == pytest.approx(total, rel=1e-9)
    assert state_totals["receipts_share"].sum() == pytest.approx(
        state_totals["receipts"].sum() / total, rel=1e-9
    )
    assert "00" not in set(state_totals["state"])
    assert "US" not in set(state_totals["state"])


def test_top_candidates_sorted_and_bounded() -> None:
    top = pd.read_csv(PROC / "top_candidates.csv")
    assert len(top) == 10
    assert list(top["rank"]) == list(range(1, 11))
    assert top["receipts"].is_monotonic_decreasing
    assert top["receipts_share"].sum() <= 1.0


def test_small_dollar_share_bounds(candidates: pd.DataFrame) -> None:
    shares = candidates["small_dollar_share"].dropna()
    assert ((shares >= 0) & (shares <= 1)).all()


def test_burn_rate_blank_for_zero_receipts(candidates: pd.DataFrame) -> None:
    zero = candidates[candidates["receipts"].fillna(0) <= 0]
    assert zero["burn_rate"].isna().all()


def test_cash_identity_hold_rate(record: dict[str, Any]) -> None:
    """Plan §11 item 14: aggregate hold rate ≥ 80% confirms the layout."""
    cash = record["cash_identity"]
    assert cash["webk"]["hold_rate"] >= 0.80
    assert cash["webl"]["hold_rate"] >= 0.80


def test_api_fetch_complete(record: dict[str, Any]) -> None:
    api = record["api_fetch"]
    assert api["pages_fetched"] == api["api_pages"]
    assert api["rows_fetched"] == api["api_total_count"]


def test_sql_vs_pandas_party_totals(candidates: pd.DataFrame) -> None:
    """SQL check (plan §4.6): party receipts via SQLite equal pandas."""
    with_totals = candidates[candidates["has_totals"]]
    pandas_totals = with_totals.groupby("party")["receipts"].sum()
    conn = sqlite3.connect(":memory:")
    with_totals.to_sql("candidates", conn, index=False)
    rows = conn.execute(
        "SELECT party, SUM(receipts) FROM candidates "
        "WHERE party IS NOT NULL GROUP BY party"
    ).fetchall()
    conn.close()
    sql_totals = dict(rows)
    assert set(sql_totals) == set(pandas_totals.index)
    for party, value in pandas_totals.items():
        assert sql_totals[party] == pytest.approx(value, rel=1e-9)
    top_sql = max(sql_totals, key=lambda p: sql_totals[p])
    top_pandas = str(pandas_totals.idxmax())
    assert top_sql == top_pandas


def test_no_committed_file_over_1mb_and_data_under_5mb() -> None:
    committed: list[Path] = list((RAW).glob("*.zip")) + list(PROC.glob("*.csv"))
    committed.append(PROC / "data_source.json")
    total = 0
    for path in committed:
        size = path.stat().st_size
        assert size < 1_000_000, f"{path.name} is {size} bytes"
        total += size
    assert total < 5_000_000, f"committed data/ is {total} bytes"


def test_gitignore_rules() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw/*.txt" in gitignore
    assert "data/raw/api_pages/" in gitignore
    assert "data/raw/*_synthetic" in gitignore
    # The four zips must NOT be ignored: no line ignores data/raw/*.zip.
    assert "data/raw/*.zip" not in gitignore
    assert not (RAW / "cn24.zip").exists() is False


def test_synthetic_never_overwrites_live() -> None:
    assert not list(RAW.glob("*_synthetic*"))
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw/*_synthetic" in gitignore


def test_offline_run_does_not_clobber_data_source() -> None:
    """Day 5/6 lesson: an offline run must not touch data_source.json."""
    source_path = PROC / "data_source.json"
    before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    result = subprocess.run(
        [sys.executable, "-m", "src.data_pipeline", "--offline"],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert before == after


def test_offline_reproduction_within_tolerance() -> None:
    """Day 9 CI lesson: compare regenerated floats with tolerance,
    never byte-exact."""
    from src.data_pipeline import derive_tables

    candidates = pd.read_csv(PROC / "candidates.csv")
    committees = pd.read_csv(PROC / "committees.csv")
    derived = derive_tables(candidates, committees)
    for name, frame in derived.items():
        committed = pd.read_csv(PROC / f"{name}.csv")
        assert list(frame.columns) == list(committed.columns), name
        assert len(frame) == len(committed), name
        for col in frame.columns:
            if pd.api.types.is_numeric_dtype(frame[col]):
                assert np.allclose(
                    frame[col].fillna(0).to_numpy(dtype=float),
                    committed[col].fillna(0).to_numpy(dtype=float),
                    rtol=1e-6,
                    atol=0.01,
                ), f"{name}.{col}"
            else:
                # fillna("") first: None (live frame) and NaN (CSV
                # round-trip) are both "missing" and must compare equal.
                assert (
                    frame[col].fillna("").astype(str)
                    == committed[col].fillna("").astype(str)
                ).all(), f"{name}.{col}"


# --- Builder tests on fixtures (coverage for data_pipeline/make_charts) --


def _totals_fixture() -> pd.DataFrame:
    """Minimal API-list totals: A overstated (in webl), B list-only,
    E with no cn row (2023-election-year case)."""
    return pd.DataFrame(
        {
            "candidate_id": [
                "H1XX00001",
                "H1XX00001",
                "S1YY00002",
                "P1EE00005",
                "P1WW00004",
            ],
            "name": [
                "ALPHA, ANN",
                "ALPHA, ANN",
                "BETA, BOB",
                "EPSILON, EVE",
                "DELTA, DAN",
            ],
            "party": ["DEM", "DEM", "REP", "IND", "IND"],
            "office": ["H", "H", "S", "P", "P"],
            "office_state": ["CA", "CA", "TX", None, "NY"],
            "state": ["CA", "CA", "TX", "VT", "NY"],
            "district": ["01", "01", None, None, None],
            "receipts": [100000.0, 100000.0, 50000.0, 7000.0, 35000.0],
            "disbursements": [90000.0, 90000.0, 40000.0, 6000.0, 30000.0],
            "cash_on_hand_end_period": [10000.0, 10000.0, 10000.0, 1000.0, 5000.0],
            "debts_owed_by_committee": [0.0, 0.0, 0.0, 0.0, 0.0],
            "individual_contributions": [60000.0, 60000.0, np.nan, np.nan, 20000.0],
            "individual_itemized_contributions": [
                40000.0,
                40000.0,
                np.nan,
                np.nan,
                25000.0,
            ],
            "individual_unitemized_contributions": [np.nan] * 5,
            "contributions": [60000.0, 60000.0, np.nan, np.nan, 20000.0],
        }
    )


def _cn_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": [
                "H1XX00001",
                "S1YY00002",
                "H1ZZ00003",
                "P1WW00004",
                "H1FF00006",
            ],
            "candidate_name": [
                "ALPHA, ANN",
                "BETA, BOB",
                "GAMMA, GAIL",
                "DELTA, DAN",
                "FREDDY, FRANK",
            ],
            "party": ["DEM", "REP", "DEM", "IND", "DEM"],
            "office": ["H", "S", "H", "P", "H"],
            "office_state": ["CA", "TX", "NY", "NY", "FL"],
            "district": ["01", "00", "02", "00", "03"],
            "principal_committee_id": [
                "C00000001",
                "C00000002",
                "",
                "C00000004",
                "C00000006",
            ],
            "state": ["CA", "TX", "NY", "NY", "FL"],
        }
    )


def _webl_fixture() -> pd.DataFrame:
    """A: filed totals below the list values (override case).
    D: in both sources, itemized exceeds individual (invalid split).
    F: webl-only (filed totals, absent from the API list)."""
    return pd.DataFrame(
        {
            "candidate_id": ["H1XX00001", "P1WW00004", "H1FF00006"],
            "candidate_name": ["ALPHA, ANN", "DELTA, DAN", "FREDDY, FRANK"],
            "party": ["DEM", "IND", "DEM"],
            "office_state": ["CA", "NY", "FL"],
            "district": ["01", "00", "03"],
            "state": ["CA", "NY", "FL"],
            "receipts": [80000.0, 30000.0, 15000.0],
            "trans_from_other": [0.0, 0.0, 0.0],
            "disbursements": [70000.0, 25000.0, 12000.0],
            "indiv_contrib": [60000.0, 20000.0, 10000.0],
            "cash_bop": [0.0, 0.0, 0.0],
            "cash_cop": [10000.0, 5000.0, 3000.0],
            "debts_owed_by": [0.0, 0.0, 0.0],
        }
    )


def test_build_candidate_table_webl_override() -> None:
    """Plan §11 item 17 on fixtures: webl wins where present, the list
    values survive otherwise, splits are valid only where they can be."""
    from src.data_pipeline import build_candidate_table

    table, counts = build_candidate_table(
        _totals_fixture(), _cn_fixture(), _webl_fixture()
    )
    assert counts["duplicate_candidate_id"] == 1
    assert counts["filed_no_totals"] == 1
    assert counts["webl_only_candidates"] == 1
    assert counts["totals_without_master_match"] == 1
    row_a = table[table["candidate_id"] == "H1XX00001"].iloc[0]
    assert row_a["receipts_source"] == "webl"
    assert row_a["receipts"] == pytest.approx(80000.0)
    assert row_a["disbursements"] == pytest.approx(70000.0)
    assert row_a["individual_unitemized_contributions"] == pytest.approx(20000.0)
    row_b = table[table["candidate_id"] == "S1YY00002"].iloc[0]
    assert row_b["receipts_source"] == "api_list"
    assert row_b["receipts"] == pytest.approx(50000.0)
    assert pd.isna(row_b["individual_unitemized_contributions"])
    row_d = table[table["candidate_id"] == "P1WW00004"].iloc[0]
    assert row_d["has_totals"]
    assert row_d["receipts"] == pytest.approx(30000.0)
    # API itemized ($25,000) exceeds webl individual ($20,000): no split.
    assert pd.isna(row_d["individual_unitemized_contributions"])
    row_f = table[table["candidate_id"] == "H1FF00006"].iloc[0]
    assert row_f["has_totals"]
    assert row_f["receipts_source"] == "webl"
    assert row_f["receipts"] == pytest.approx(15000.0)
    row_c = table[table["candidate_id"] == "H1ZZ00003"].iloc[0]
    assert not row_c["has_totals"]
    assert pd.isna(row_c["receipts"])
    # 2023-election-year fallback: name and state from the API totals.
    row_e = table[table["candidate_id"] == "P1EE00005"].iloc[0]
    assert row_e["candidate_name"] == "EPSILON, EVE"
    assert row_e["state"] == "VT"
    assert not row_e["has_master"]
    ov: dict[str, object] = cast("dict[str, object]", counts["receipts_override"])
    assert ov["n_webl_override"] == 3
    assert ov["n_api_list_only"] == 2
    assert ov["n_split_valid"] == 1
    assert ov["n_split_invalid_itemized_exceeds_individual"] == 1
    assert ov["post_override_max_receipts_diff_usd"] == pytest.approx(0.0)
    cross_check: dict[str, object] = cast(
        "dict[str, object]", counts["cross_check_list_vs_webl"]
    )
    max_diff: dict[str, object] = cast(
        "dict[str, object]", cross_check["max_abs_diff_usd"]
    )
    assert max_diff["receipts"] == pytest.approx(20000.0)


def test_build_committee_table_excludes_principals() -> None:
    from src.data_pipeline import build_committee_table

    webk = pd.DataFrame(
        {
            "committee_id": ["C00000001", "C00000009", "C00000010"],
            "committee_name": ["ALPHA COMMITTEE", "SOME PAC", "SUPER PAC"],
            "committee_type": ["Q", "N", "O"],
            "designation": ["P", "U", "U"],
            "receipts": [1000.0, 2000.0, 3000.0],
            "disbursements": [900.0, 1800.0, 2700.0],
            "cash_cop": [100.0, 200.0, 300.0],
            "debts_owed_by": [0.0, 0.0, 0.0],
        }
    )
    table, counts = build_committee_table(webk, {"C00000001"})
    assert counts["committee_table_rows"] == 2
    assert "C00000001" not in set(table["committee_id"])
    assert "committee_type_full" not in table.columns
    assert set(table["committee_type"]) == {"N", "O"}


def test_derive_tables_fixture() -> None:
    from src.data_pipeline import derive_tables

    candidates = pd.read_csv(PROC / "candidates.csv").head(50)
    committees = pd.read_csv(PROC / "committees.csv").head(50)
    derived = derive_tables(candidates, committees)
    assert set(derived) == {
        "party_office",
        "state_totals",
        "top_candidates",
        "top_committees",
    }
    assert len(derived["top_candidates"]) == 10
    assert len(derived["top_committees"]) == 10
    assert "committee_type_full" in derived["top_committees"].columns


def test_cross_check_webl_fixture() -> None:
    from src.data_pipeline import cross_check_webl

    candidates = pd.DataFrame(
        {
            "candidate_id": ["H1XX00001", "S1YY00002"],
            "receipts": [100000.0, 50000.0],
            "disbursements": [90000.0, 40000.0],
            "cash_on_hand_end_period": [10000.0, 10000.0],
            "debts_owed_by_committee": [0.0, 0.0],
            "has_totals": [True, True],
        }
    )
    webl = pd.DataFrame(
        {
            "candidate_id": ["H1XX00001"],
            "receipts": [80000.0],
            "trans_from_other": [0.0],
            "disbursements": [70000.0],
            "cash_bop": [0.0],
            "cash_cop": [10000.0],
            "debts_owed_by": [0.0],
            "indiv_contrib": [60000.0],
        }
    )
    check = cross_check_webl(candidates, webl)
    assert check["candidates_in_both"] == 1
    check_max_diff: dict[str, object] = cast(
        "dict[str, object]", check["max_abs_diff_usd"]
    )
    assert check_max_diff["receipts"] == pytest.approx(20000.0)
    assert check["top_candidate_id"] == "H1XX00001"


def test_charts_render_from_committed_tables(tmp_path: Path) -> None:
    """make_charts coverage: all four chart functions run on the
    committed tables and write non-empty PNGs."""
    from src.make_charts import (
        chart_01_receipts_by_office_party,
        chart_02_top_candidates,
        chart_03_funding_mix,
        chart_04_state_totals,
    )

    party_office = pd.read_csv(PROC / "party_office.csv")
    top_candidates = pd.read_csv(PROC / "top_candidates.csv")
    state_totals = pd.read_csv(PROC / "state_totals.csv")
    outs = {
        "01": tmp_path / "01.png",
        "02": tmp_path / "02.png",
        "03": tmp_path / "03.png",
        "04": tmp_path / "04.png",
    }
    chart_01_receipts_by_office_party(party_office, outs["01"])
    chart_02_top_candidates(top_candidates, outs["02"])
    chart_03_funding_mix(party_office, outs["03"])
    chart_04_state_totals(state_totals, outs["04"])
    for path in outs.values():
        assert path.exists()
        assert path.stat().st_size > 1000
