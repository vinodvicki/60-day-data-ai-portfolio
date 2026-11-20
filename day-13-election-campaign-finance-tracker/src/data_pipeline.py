"""Data pipeline for Day 13 — Election Campaign Finance Tracker.

Four FEC bulk files (candidate master, committee summary, candidate-
committee linkage, candidate summary — all headerless pipe-delimited
text, column layouts verified in plan §3.1b) plus the openFEC API
candidate totals (the funding-mix source: the legacy bulk layouts carry
no itemized/unitemized split). Candidate money is the FEC candidate
totals (plan §2.0, amended); committee money is the webk bulk file.
Offline mode regenerates the derived tables from the committed CSVs and
never clobbers a live data_source.json.
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from src.finance import (
        CASH_IDENTITY_TOLERANCE_USD,
        burn_rate,
        check_cash_identity,
        principal_committees,
        small_dollar_share,
        summarise_party_office,
        summarise_states,
        top_n,
    )
except ImportError:  # running as a script from inside src/
    from finance import (  # type: ignore[no-redef]
        CASH_IDENTITY_TOLERANCE_USD,
        burn_rate,
        check_cash_identity,
        principal_committees,
        small_dollar_share,
        summarise_party_office,
        summarise_states,
        top_n,
    )

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
BULK_BASE = "https://www.fec.gov/files/bulk-downloads/2024/"
API_BASE = "https://api.open.fec.gov/v1"
API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
CYCLE = 2024
PAGE_SIZE = 100
API_SLEEP_SECONDS = 7.0
API_MAX_ATTEMPTS = 3
CROSS_CHECK_SAMPLE_N = 20
CROSS_CHECK_SEED = 42
#: Minimum cash-identity hold rate that confirms the column layout
#: (plan §11 item 14 — the identity is an aggregate layout check).
MIN_CASH_IDENTITY_HOLD_RATE = 0.80

BULK_FILES = {
    "cn24.zip": "cn.txt",
    "webk24.zip": "webk24.txt",
    "ccl24.zip": "ccl.txt",
    "webl24.zip": "webl24.txt",
}

CN_COLUMNS = [
    "candidate_id",
    "candidate_name",
    "party",
    "election_year",
    "office_state",
    "office",
    "district",
    "ici",
    "status",
    "principal_committee_id",
    "st1",
    "st2",
    "city",
    "state",
    "zip",
]

WEBK_COLUMNS = [
    "committee_id",
    "committee_name",
    "committee_type",
    "designation",
    "filing_freq",
    "receipts",
    "trans_from_aff",
    "indiv_contrib",
    "oth_cmte_contrib",
    "cand_contrib",
    "cand_loans",
    "ttl_loans_received",
    "disbursements",
    "transf_to_aff",
    "indiv_refunds",
    "oth_cmte_refunds",
    "cand_loan_repay",
    "loan_repay",
    "cash_bop",
    "cash_cop",
    "debts_owed_by",
    "nonfed_trans_received",
    "contrib_to_other_cmte",
    "ind_exp",
    "pty_coord_exp",
    "nonfed_share",
    "coverage_end",
]

CCL_COLUMNS = [
    "candidate_id",
    "election_year",
    "fec_election_tp",
    "committee_id",
    "committee_type",
    "designation",
    "linkage_id",
]

# Legacy candidate-summary layout (plan §3.1b). Columns marked col_* are
# undecoded and unused; only the verified money/date columns are read.
WEBL_COLUMNS = [
    "candidate_id",
    "candidate_name",
    "ici",
    "col_04",
    "party",
    "receipts",
    "trans_from_other",
    "disbursements",
    "col_09",
    "cash_bop",
    "cash_cop",
    "col_12",
    "col_13",
    "col_14",
    "col_15",
    "col_16",
    "debts_owed_by",
    "indiv_contrib",
    "office_state",
    "district",
    "st1",
    "st2",
    "city",
    "state",
    "zip",
    "col_26",
    "col_27",
    "coverage_end",
    "col_29",
    "col_30",
]

#: Committee type codes, per the FEC committee-type code descriptions
#: (https://www.fec.gov/campaign-finance-data/committee-type-code-descriptions).
COMMITTEE_TYPES = {
    "C": "Communication cost",
    "D": "Delegate committee",
    "E": "Electioneering communication",
    "H": "House",
    "I": "Independent expenditor (person or group)",
    "N": "PAC - nonqualified",
    "O": "Independent expenditure-only (Super PACs)",
    "P": "Presidential",
    "Q": "PAC - qualified",
    "S": "Senate",
    "U": "Single-candidate independent expenditure",
    "V": "Hybrid PAC (with Non-Contribution Account) - Nonqualified",
    "W": "Hybrid PAC (with Non-Contribution Account) - Qualified",
    "X": "Party - nonqualified",
    "Y": "Party - qualified",
    "Z": "National party nonfederal account",
}

ATTRIBUTION = (
    "Source: U.S. Federal Election Commission, 2024 cycle bulk data "
    "(https://www.fec.gov/data/browse-data/?tab=bulk-data) and openFEC API "
    "(https://api.open.fec.gov/v1). Retrieved 2026-11-19. Public domain."
)

MONEY_COLUMNS_WEBK = [
    "receipts",
    "trans_from_aff",
    "indiv_contrib",
    "oth_cmte_contrib",
    "cand_contrib",
    "cand_loans",
    "ttl_loans_received",
    "disbursements",
    "transf_to_aff",
    "indiv_refunds",
    "oth_cmte_refunds",
    "cand_loan_repay",
    "loan_repay",
    "cash_bop",
    "cash_cop",
    "debts_owed_by",
    "nonfed_trans_received",
    "contrib_to_other_cmte",
    "ind_exp",
    "pty_coord_exp",
    "nonfed_share",
]

MONEY_COLUMNS_WEBL = [
    "receipts",
    "trans_from_other",
    "disbursements",
    "cash_bop",
    "cash_cop",
    "indiv_contrib",
]


def download_bulk(filename: str, dest: Path) -> Path:
    """Download one bulk zip (one retry after 60 s on 429/5xx)."""
    url = BULK_BASE + filename
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "60-day-portfolio/1.0"}
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                dest.write_bytes(resp.read())
            return dest
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            if attempt == 0:
                time.sleep(60)
                continue
            raise RuntimeError(f"download failed for {url}: {exc}") from exc
    raise RuntimeError(f"download failed for {url}")


def unpack_bulk(zip_path: Path, dest_dir: Path) -> Path:
    """Unzip a bulk file; returns the extracted .txt path."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if len(names) != 1:
            raise RuntimeError(
                f"{zip_path.name} holds {len(names)} members, expected 1"
            )
        zf.extract(names[0], dest_dir)
    return dest_dir / names[0]


def load_bulk_txt(path: Path, columns: list[str]) -> pd.DataFrame:
    """Read a headerless pipe-delimited bulk file with fixed column names."""
    df = pd.read_csv(
        path,
        sep="|",
        header=None,
        names=columns,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
    )
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    return df


def to_money(series: pd.Series) -> pd.Series:
    """Parse an FEC money column (plain numbers, no $/commas)."""
    return pd.to_numeric(series, errors="coerce")


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse FEC dates, verified MM/DD/YYYY (plan §3.1b)."""
    return pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")


def clean_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean the candidate master (plan §3.2 rules 3-4)."""
    counts: dict[str, int] = {"raw_rows": len(df)}
    df = df.copy()
    df["election_year_num"] = pd.to_numeric(df["election_year"], errors="coerce")
    counts["non_2024_election_year"] = int((df["election_year_num"] != CYCLE).sum())
    df = df[df["election_year_num"] == CYCLE]
    counts["duplicate_candidate_id"] = int(df["candidate_id"].duplicated().sum())
    df = df.drop_duplicates(subset=["candidate_id"], keep="first")
    counts["missing_principal_committee"] = int(
        (df["principal_committee_id"] == "").sum()
    )
    counts["clean_rows"] = len(df)
    return df, counts


def clean_committees(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean the committee summary (plan §3.2 rules 3, 5)."""
    counts: dict[str, int] = {"raw_rows": len(df)}
    df = df.copy()
    for col in MONEY_COLUMNS_WEBK:
        df[col] = to_money(df[col])
    df["coverage_end_dt"] = parse_dates(df["coverage_end"])
    counts["no_financial_summary"] = int(df["coverage_end_dt"].isna().sum())
    df = df[df["coverage_end_dt"].notna()]
    window_start = pd.Timestamp("2023-01-01")
    window_end = pd.Timestamp("2024-12-31")
    outside = (df["coverage_end_dt"] < window_start) | (
        df["coverage_end_dt"] > window_end
    )
    counts["coverage_end_outside_window"] = int(outside.sum())
    df = df[~outside]
    counts["duplicate_committee_id"] = int(df["committee_id"].duplicated().sum())
    df = df.sort_values("coverage_end_dt").drop_duplicates(
        subset=["committee_id"], keep="last"
    )
    counts["negative_receipts"] = int((df["receipts"] < 0).sum())
    df = df[df["receipts"] >= 0]
    counts["clean_rows"] = len(df)
    return df, counts


def cash_identity_report(df: pd.DataFrame) -> dict[str, float]:
    """Aggregate cash-identity check (plan §11 item 14).

    The identity holds for most rows; the rest are a data feature
    (amended filings, non-federal accounts), not a layout error.
    A hold rate below MIN_CASH_IDENTITY_HOLD_RATE fails the build.
    """
    numeric = df.dropna(subset=["cash_bop", "receipts", "disbursements", "cash_cop"])
    failing = check_cash_identity(numeric)
    n = len(numeric)
    hold_rate = (n - len(failing)) / n if n else 0.0
    diffs = (
        (numeric["cash_bop"] + numeric["receipts"] - numeric["disbursements"])
        - numeric["cash_cop"]
    ).abs()
    report = {
        "numeric_rows": n,
        "failing_rows": len(failing),
        "hold_rate": hold_rate,
        "median_abs_diff_usd": float(diffs.median()) if n else 0.0,
        "max_abs_diff_usd": float(diffs.max()) if n else 0.0,
    }
    if hold_rate < MIN_CASH_IDENTITY_HOLD_RATE:
        raise RuntimeError(
            "cash-identity hold rate "
            f"{hold_rate:.3f} < {MIN_CASH_IDENTITY_HOLD_RATE} — column layout wrong"
        )
    return report


def api_get(url: str) -> dict[str, Any]:
    """One openFEC GET with retries (60 s backoff on 429/5xx)."""
    last_exc: Exception | None = None
    for attempt in range(API_MAX_ATTEMPTS):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "60-day-portfolio/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload: dict[str, Any] = json.loads(resp.read())
                return payload
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 500, 502, 503, 504) and attempt < API_MAX_ATTEMPTS - 1:
                time.sleep(60)
                continue
            raise RuntimeError(f"openFEC GET failed ({exc.code}): {url}") from exc
        except urllib.error.URLError as exc:
            last_exc = exc
            if attempt < API_MAX_ATTEMPTS - 1:
                time.sleep(60)
                continue
            raise RuntimeError(f"openFEC GET failed: {url}: {exc}") from exc
    raise RuntimeError(f"openFEC GET failed: {url}: {last_exc}")


def fetch_candidate_totals(
    raw_dir: Path, use_cache: bool
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Paginate /candidates/totals/ (plan §3.3, amended).

    Each page's JSON is cached under data/raw/api_pages/ as it arrives,
    so a re-run resumes instead of re-fetching. Fails loudly if the
    fetch cannot complete — no partial candidate table is ever written.
    """
    pages_dir = raw_dir / "api_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    first_url = (
        f"{API_BASE}/candidates/totals/?api_key={API_KEY}&cycle={CYCLE}"
        f"&per_page={PAGE_SIZE}&sort=-receipts&page=1"
    )
    first = api_get(first_url)
    pagination = first["pagination"]
    total_count = int(pagination["count"])
    n_pages = math.ceil(total_count / PAGE_SIZE)
    frames: list[pd.DataFrame] = []
    pages_fetched = 0
    pages_from_cache = 0
    for page in range(1, n_pages + 1):
        cache_path = pages_dir / f"page_{page:03d}.json"
        if use_cache and cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            pages_from_cache += 1
        else:
            if page == 1:
                payload = first
            else:
                url = (
                    f"{API_BASE}/candidates/totals/?api_key={API_KEY}&cycle={CYCLE}"
                    f"&per_page={PAGE_SIZE}&sort=-receipts&page={page}"
                )
                time.sleep(API_SLEEP_SECONDS)
                payload = api_get(url)
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
        results = payload["results"]
        frames.append(pd.DataFrame(results))
        pages_fetched += 1
    if pages_fetched != n_pages:
        raise RuntimeError(
            f"candidate totals fetch incomplete: {pages_fetched}/{n_pages} pages"
        )
    totals = pd.concat(frames, ignore_index=True)
    if "receipts" not in totals.columns:
        raise RuntimeError(
            "openFEC totals rows carry no 'receipts' field; keys seen: "
            + ", ".join(sorted(totals.columns))
        )
    stats = {
        "api_total_count": total_count,
        "api_pages": n_pages,
        "pages_fetched": pages_fetched,
        "pages_from_cache": pages_from_cache,
        "rows_fetched": len(totals),
    }
    return totals, stats


def build_candidate_table(
    totals: pd.DataFrame, cn: pd.DataFrame, webl: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Join API candidate totals to the candidate master, then override
    money with the filed candidate summary (webl) where present
    (plan §11 item 17).

    The /candidates/totals/ LIST endpoint overstates receipts,
    disbursements and itemized contributions for 95 multi-committee
    candidates (verified: it sums across committees without netting;
    the single-candidate endpoint and the webl bulk file agree exactly
    for all 5 candidates checked). The webl values are therefore
    authoritative where present; the list values are used only where
    the candidate is absent from webl, and flagged as such.
    """
    counts: dict[str, object] = {"api_totals_rows": len(totals)}
    totals = totals.copy()
    counts["duplicate_candidate_id"] = int(totals["candidate_id"].duplicated().sum())
    totals = totals.drop_duplicates(subset=["candidate_id"], keep="first")
    cn_attrs = cn[
        [
            "candidate_id",
            "candidate_name",
            "party",
            "office",
            "office_state",
            "district",
            "principal_committee_id",
            "state",
        ]
    ].copy()
    # cn "state" is the mailing-address state (CAND_ST); rename so it does
    # not collide with the API totals' "state" column in the merge.
    cn_attrs = cn_attrs.rename(columns={"state": "mailing_state"})
    merged = totals.merge(cn_attrs, on="candidate_id", how="left", suffixes=("", "_cn"))
    # has_master tracks the cn match, not the API row: the cn-side
    # columns carry the _cn suffix (the API side keeps the bare names),
    # and office is always present in cn. Using the API party here
    # wrongly marked 2023-election-year candidates as matched.
    counts["totals_without_master_match"] = int(merged["office_cn"].isna().sum())
    # Candidates filed in 2024 with no API totals row, and candidates in
    # the webl bulk file but not in the API totals (they have filed
    # totals, so they belong in the table with has_totals=True).
    with_totals = set(totals["candidate_id"])
    webl_ids = set(webl["candidate_id"])
    no_totals = cn[
        ~cn["candidate_id"].isin(with_totals) & ~cn["candidate_id"].isin(webl_ids)
    ].copy()
    counts["filed_no_totals"] = len(no_totals)
    counts["webl_only_candidates"] = len(webl_ids - with_totals)
    for col in [
        "receipts",
        "disbursements",
        "cash_on_hand_end_period",
        "debts_owed_by_committee",
        "individual_contributions",
        "individual_itemized_contributions",
        "individual_unitemized_contributions",
        "contributions",
    ]:
        if col not in merged.columns:
            merged[col] = np.nan
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged["has_totals"] = True
    merged["has_master"] = merged["office_cn"].notna()
    no_totals_rows = pd.DataFrame(
        {
            "candidate_id": no_totals["candidate_id"],
            "candidate_name": no_totals["candidate_name"],
            "party": no_totals["party"],
            "office": no_totals["office"],
            "office_state": no_totals["office_state"],
            "district": no_totals["district"],
            "principal_committee_id": no_totals["principal_committee_id"],
            "mailing_state": no_totals["state"],
            "receipts": np.nan,
            "disbursements": np.nan,
            "cash_on_hand_end_period": np.nan,
            "debts_owed_by_committee": np.nan,
            "individual_contributions": np.nan,
            "individual_itemized_contributions": np.nan,
            "individual_unitemized_contributions": np.nan,
            "contributions": np.nan,
            "has_totals": False,
            "has_master": True,
        }
    )
    webl_only = webl[~webl["candidate_id"].isin(with_totals)].copy()
    webl_only_attrs = webl_only.merge(
        cn_attrs, on="candidate_id", how="left", suffixes=("", "_cn")
    )
    counts["webl_only_with_master_match"] = int(webl_only_attrs["office"].notna().sum())
    webl_only_rows = pd.DataFrame(
        {
            "candidate_id": webl_only_attrs["candidate_id"],
            "candidate_name": webl_only_attrs["candidate_name"],
            "party": webl_only_attrs["party"].fillna(webl_only_attrs["party_cn"]),
            "office": webl_only_attrs["office"].fillna(
                webl_only_attrs["candidate_id"].str[0]
            ),
            "office_state": webl_only_attrs["office_state_cn"].fillna(
                webl_only_attrs["office_state"]
            ),
            "district": webl_only_attrs["district_cn"].fillna(
                webl_only_attrs["district"]
            ),
            "principal_committee_id": webl_only_attrs["principal_committee_id"].fillna(
                ""
            ),
            "mailing_state": webl_only_attrs["mailing_state"].fillna(
                webl_only_attrs["state"]
            ),
            "receipts": np.nan,
            "disbursements": np.nan,
            "cash_on_hand_end_period": np.nan,
            "debts_owed_by_committee": np.nan,
            "individual_contributions": np.nan,
            "individual_itemized_contributions": np.nan,
            "individual_unitemized_contributions": np.nan,
            "contributions": np.nan,
            "has_totals": True,
            "has_master": webl_only_attrs["office"].notna(),
        }
    )
    candidates = pd.concat([merged, webl_only_rows, no_totals_rows], ignore_index=True)
    # Candidates whose master row is not a 2024 election-year record
    # (e.g. 2023 special-election candidates with 2024-cycle totals, 79
    # rows) have no cn attributes: the API totals carry their name and
    # state, so those are the fallbacks — never a blank.
    candidates["candidate_name"] = candidates["candidate_name"].fillna(
        candidates["name"]
    )
    # State = mailing-address state as filed (CAND_ST, plan §4.4), falling
    # back to the office state, then to the API totals' state. Presidential
    # campaigns report their HQ address (e.g. PA for Biden/Harris), which
    # the README discloses.
    candidates = candidates.rename(columns={"state": "state_api"})
    candidates["mailing_state"] = candidates["mailing_state"].replace("", np.nan)
    candidates["state"] = (
        candidates["mailing_state"]
        .fillna(candidates["office_state"])
        .fillna(candidates["state_api"])
    )
    # Cross-check the API LIST values against webl BEFORE the override
    # (after it, the values are webl's by construction and the comparison
    # would be vacuous).
    counts["cross_check_list_vs_webl"] = cross_check_webl(candidates, webl)
    # --- webl override (plan §11 item 17) -------------------------------
    # webl money columns (verified to equal the single-candidate endpoint
    # for all 5 candidates checked: H2AK01158, H2AK01083, P80000722,
    # S4VT00033, S2TX00312).
    webl_money = webl[
        [
            "candidate_id",
            "receipts",
            "disbursements",
            "indiv_contrib",
            "cash_cop",
            "debts_owed_by",
        ]
    ].copy()
    for col in [
        "receipts",
        "disbursements",
        "indiv_contrib",
        "cash_cop",
        "debts_owed_by",
    ]:
        webl_money[col] = to_money(webl_money[col])
    webl_money = webl_money.rename(
        columns={
            "receipts": "receipts_webl",
            "disbursements": "disbursements_webl",
            "indiv_contrib": "individual_contributions_webl",
            "cash_cop": "cash_on_hand_webl",
            "debts_owed_by": "debts_owed_webl",
        }
    )
    candidates = candidates.merge(webl_money, on="candidate_id", how="left")
    n_webl = int(candidates["receipts_webl"].notna().sum())
    # Dollars changed counts only rows that had an API value to override
    # (webl-only rows had no API value, so their webl money is not a
    # "change").
    changed_mask = candidates["receipts"].notna() & candidates["receipts_webl"].notna()
    dollars_changed = float(
        (
            candidates.loc[changed_mask, "receipts_webl"]
            - candidates.loc[changed_mask, "receipts"]
        )
        .abs()
        .sum()
    )
    candidates["receipts_source"] = np.where(
        candidates["receipts_webl"].notna(), "webl", "api_list"
    )
    candidates["receipts"] = candidates["receipts_webl"].fillna(candidates["receipts"])
    candidates["disbursements"] = candidates["disbursements_webl"].fillna(
        candidates["disbursements"]
    )
    candidates["cash_on_hand_end_period"] = candidates[
        "cash_on_hand_end_period"
    ].fillna(candidates["cash_on_hand_webl"])
    candidates["debts_owed_by_committee"] = candidates[
        "debts_owed_by_committee"
    ].fillna(candidates["debts_owed_webl"])
    candidates["individual_contributions"] = candidates["individual_contributions_webl"]
    # Unitemized = individual total - itemized, only where the split is
    # valid (individual >= itemized). The 37 candidates where the list
    # endpoint's itemized exceeds webl's individual total get no split.
    candidates["individual_unitemized_contributions"] = np.where(
        candidates["individual_contributions"].notna()
        & candidates["individual_itemized_contributions"].notna()
        & (
            candidates["individual_contributions"]
            >= candidates["individual_itemized_contributions"]
        ),
        candidates["individual_contributions"]
        - candidates["individual_itemized_contributions"],
        np.nan,
    )
    n_split_valid = int(candidates["individual_unitemized_contributions"].notna().sum())
    n_split_invalid = int(
        (
            candidates["individual_contributions"].notna()
            & candidates["individual_itemized_contributions"].notna()
            & (
                candidates["individual_contributions"]
                < candidates["individual_itemized_contributions"]
            )
        ).sum()
    )
    # Post-override verification: common candidates must now match webl
    # exactly on receipts/disbursements (by construction).
    common = candidates[candidates["receipts_webl"].notna()]
    post_diff = float((common["receipts"] - common["receipts_webl"]).abs().max())
    if post_diff > CASH_IDENTITY_TOLERANCE_USD:
        raise RuntimeError(f"webl override failed: max diff {post_diff}")
    override_stats: dict[str, object] = {
        "n_webl_override": n_webl,
        "n_api_list_only": int(
            (
                (candidates["receipts_source"] == "api_list") & candidates["has_totals"]
            ).sum()
        ),
        "receipts_dollars_changed_by_override": dollars_changed,
        "n_split_valid": n_split_valid,
        "n_split_invalid_itemized_exceeds_individual": n_split_invalid,
        "n_no_split": int(candidates["has_totals"].sum()) - n_split_valid,
        "post_override_max_receipts_diff_usd": post_diff,
    }
    candidates["other_receipts"] = candidates.apply(
        lambda r: (
            float(r["receipts"] - r["individual_contributions"])
            if pd.notna(r["receipts"]) and pd.notna(r["individual_contributions"])
            else float("nan")
        ),
        axis=1,
    )
    candidates["small_dollar_share"] = candidates.apply(
        lambda r: (
            small_dollar_share(
                float(r["individual_itemized_contributions"]),
                float(r["individual_unitemized_contributions"]),
            )
            if pd.notna(r["individual_itemized_contributions"])
            and pd.notna(r["individual_unitemized_contributions"])
            else None
        ),
        axis=1,
    )
    candidates["burn_rate"] = candidates.apply(
        lambda r: (
            burn_rate(float(r["receipts"]), float(r["disbursements"]))
            if pd.notna(r["receipts"]) and pd.notna(r["disbursements"])
            else None
        ),
        axis=1,
    )
    candidates = candidates.rename(
        columns={
            "cash_on_hand_end_period": "cash_on_hand",
            "debts_owed_by_committee": "debts_owed",
        }
    )
    cols = [
        "candidate_id",
        "candidate_name",
        "party",
        "office",
        "state",
        "district",
        "principal_committee_id",
        "has_totals",
        "has_master",
        "receipts_source",
        "receipts",
        "disbursements",
        "cash_on_hand",
        "debts_owed",
        "individual_contributions",
        "individual_itemized_contributions",
        "individual_unitemized_contributions",
        "other_receipts",
        "small_dollar_share",
        "burn_rate",
    ]
    candidates = (
        candidates[cols]
        .sort_values(["receipts", "candidate_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    counts["candidate_table_rows"] = len(candidates)
    counts["candidate_table_with_totals"] = int(candidates["has_totals"].sum())
    counts["receipts_override"] = override_stats
    return candidates, counts


def build_committee_table(
    webk: pd.DataFrame, principals: set[str]
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Non-principal committees from the webk bulk file (plan §2.0)."""
    counts: dict[str, int] = {"webk_clean_rows": len(webk)}
    committees = webk.copy()
    committees["is_principal"] = committees["committee_id"].isin(principals)
    counts["principal_committees_in_webk"] = int(committees["is_principal"].sum())
    committees = committees[~committees["is_principal"]].copy()
    committees["committee_type_full"] = committees["committee_type"].map(
        COMMITTEE_TYPES
    )
    counts["unmapped_committee_types"] = int(
        committees["committee_type_full"].isna().sum()
    )
    committees = committees[
        [
            "committee_id",
            "committee_name",
            "committee_type",
            "designation",
            "receipts",
            "disbursements",
            "cash_cop",
            "debts_owed_by",
        ]
    ].rename(columns={"cash_cop": "cash_on_hand", "debts_owed_by": "debts_owed"})
    # committee_type_full is NOT written to committees.csv: the long
    # label repeats on every row and pushes the file over the 1 MB/file
    # rule (plan §11 item 21). The full mapping lives in
    # data_source.json (committee_type_full_mapping) and the label is
    # re-derived in derive_tables for top_committees.csv.
    committees = committees.sort_values(
        ["receipts", "committee_id"], ascending=[False, True]
    ).reset_index(drop=True)
    counts["committee_table_rows"] = len(committees)
    return committees, counts


def cross_check_webl(candidates: pd.DataFrame, webl: pd.DataFrame) -> dict[str, object]:
    """Compare webl bulk figures against the API totals (plan §3.3).

    Top candidate + a deterministic 20-candidate sample; records the max
    absolute difference per field. The known P80000722 disbursement
    discrepancy is recorded, not hidden.
    """
    webl = webl.copy()
    for col in MONEY_COLUMNS_WEBL:
        webl[col] = to_money(webl[col])
    api = candidates[candidates["has_totals"]].set_index("candidate_id")
    # "In both" means the API list actually has a totals value for the
    # candidate (webl-only rows sit in the frame with NaN API values).
    common = [
        cid
        for cid in webl["candidate_id"]
        if cid in api.index and pd.notna(api.loc[cid, "receipts"])
    ]
    rng = np.random.default_rng(CROSS_CHECK_SEED)
    sample = (
        list(
            rng.choice(
                common, size=min(CROSS_CHECK_SAMPLE_N, len(common)), replace=False
            )
        )
        if common
        else []
    )
    top_id = ""
    if len(api):
        top_id = str(api["receipts"].idxmax())
    check_ids = ([top_id] if top_id in common else []) + [
        c for c in sample if c != top_id
    ]
    # API list field -> webl field. The API list's cash/debts columns are
    # named cash_on_hand_end_period / debts_owed_by_committee here (the
    # pipeline renames them only after the override).
    api_fields = {
        "receipts": "receipts",
        "disbursements": "disbursements",
        "cash_on_hand": "cash_on_hand_end_period",
        "debts_owed": "debts_owed_by_committee",
    }
    webl_fields = {
        "receipts": "receipts",
        "disbursements": "disbursements",
        "cash_on_hand": "cash_cop",
        "debts_owed": "debts_owed_by",
    }
    max_diff: dict[str, float] = {f: 0.0 for f in api_fields}
    n_compared = 0
    top_discrepancy: dict[str, float] = {}
    webl_idx = webl.set_index("candidate_id")
    for cid in check_ids:
        a = api.loc[cid]
        w = webl_idx.loc[cid]
        for label, api_field in api_fields.items():
            av = a[api_field]
            wv = w[webl_fields[label]]
            if pd.notna(av) and pd.notna(wv):
                diff = abs(float(av) - float(wv))
                max_diff[label] = max(max_diff[label], diff)
                if cid == top_id:
                    top_discrepancy[label] = diff
        n_compared += 1
    return {
        "candidates_in_both": len(common),
        "sample_n": n_compared,
        "top_candidate_id": top_id,
        "max_abs_diff_usd": max_diff,
        "top_candidate_diff_usd": top_discrepancy,
    }


def derive_tables(
    candidates: pd.DataFrame, committees: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """Derived tables from the two base tables (plan §3.5)."""
    # committees.csv no longer carries committee_type_full (plan §11
    # item 21), so re-derive it from the type code here: top_committees
    # keeps the label, and the offline path (which reads committees.csv)
    # reproduces the committed top_committees.csv exactly.
    if "committee_type_full" not in committees.columns:
        committees = committees.assign(
            committee_type_full=committees["committee_type"].map(COMMITTEE_TYPES)
        )
    party_office = summarise_party_office(candidates)
    state_totals = summarise_states(candidates)
    with_totals = candidates[candidates["has_totals"]].copy()
    top_candidates = top_n(with_totals, "receipts", 10)
    total_candidate_receipts = float(with_totals["receipts"].fillna(0).sum())
    top_candidates = top_candidates.assign(
        receipts_share=top_candidates["receipts"] / total_candidate_receipts
    )
    top_candidates = top_candidates[
        [
            "rank",
            "candidate_id",
            "candidate_name",
            "party",
            "office",
            "state",
            "receipts",
            "receipts_share",
            "disbursements",
            "burn_rate",
            "cash_on_hand",
        ]
    ]
    total_committee_receipts = float(committees["receipts"].fillna(0).sum())
    top_committees = top_n(committees, "receipts", 10)
    top_committees = top_committees.assign(
        receipts_share=top_committees["receipts"] / total_committee_receipts
    )
    top_committees = top_committees[
        [
            "rank",
            "committee_id",
            "committee_name",
            "committee_type",
            "committee_type_full",
            "receipts",
            "receipts_share",
            "disbursements",
            "cash_on_hand",
        ]
    ]
    return {
        "party_office": party_office,
        "state_totals": state_totals,
        "top_candidates": top_candidates,
        "top_committees": top_committees,
    }


def write_tables(tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Write the processed CSVs (base + derived)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)


def write_data_source(path: Path, record: dict[str, object]) -> None:
    """Write data_source.json (live fields only; offline never calls this
    when a live record already exists — plan §3.5)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")


def synthetic_tables() -> dict[str, pd.DataFrame]:
    """Labelled-synthetic fallback (brief §4, seed 42).

    Only used if every live source fails. Same schema as the live build
    so the identical code path runs downstream.
    """
    rng = np.random.default_rng(42)
    n_cand = 5321
    parties = rng.choice(
        ["DEM", "REP", "LIB", "GRN", "IND", "OTH"],
        size=n_cand,
        p=[0.35, 0.35, 0.05, 0.02, 0.15, 0.08],
    )
    offices = rng.choice(["H", "S", "P"], size=n_cand, p=[0.75, 0.10, 0.15])
    states = rng.choice(
        ["CA", "TX", "FL", "NY", "PA", "OH", "IL", "GA", "NC", "MI"], size=n_cand
    )
    receipts = np.exp(rng.normal(10.5, 2.5, size=n_cand))
    receipts[rng.random(n_cand) < 0.05] = 0.0
    itemized_share = rng.uniform(0.4, 0.9, size=n_cand)
    indiv = receipts * rng.uniform(0.5, 0.95, size=n_cand)
    candidates = pd.DataFrame(
        {
            "candidate_id": [f"S{i:07d}" for i in range(n_cand)],
            "candidate_name": [f"CANDIDATE, SYNTHETIC {i}" for i in range(n_cand)],
            "party": parties,
            "office": offices,
            "state": states,
            "district": ["00"] * n_cand,
            "principal_committee_id": [f"C{i:08d}" for i in range(n_cand)],
            "has_totals": True,
            "has_master": True,
            "receipts": receipts,
            "disbursements": receipts * rng.uniform(0.5, 1.1, size=n_cand),
            "cash_on_hand": receipts * rng.uniform(0.0, 0.3, size=n_cand),
            "debts_owed": np.zeros(n_cand),
            "individual_contributions": indiv,
            "individual_itemized_contributions": indiv * itemized_share,
            "individual_unitemized_contributions": indiv * (1 - itemized_share),
            "other_receipts": receipts - indiv,
            "small_dollar_share": 1 - itemized_share,
            "burn_rate": None,
        }
    )
    candidates["burn_rate"] = candidates.apply(
        lambda r: burn_rate(float(r["receipts"]), float(r["disbursements"])),
        axis=1,
    )
    n_cmte = 12000
    committees = pd.DataFrame(
        {
            "committee_id": [f"C9{i:08d}" for i in range(n_cmte)],
            "committee_name": [f"SYNTHETIC COMMITTEE {i}" for i in range(n_cmte)],
            "committee_type": rng.choice(["N", "Q", "O", "Y", "X"], size=n_cmte),
            "committee_type_full": "",
            "designation": ["U"] * n_cmte,
            "receipts": np.exp(rng.normal(11.0, 2.0, size=n_cmte)),
            "disbursements": np.exp(rng.normal(11.0, 2.0, size=n_cmte)),
            "cash_on_hand": np.exp(rng.normal(9.0, 2.0, size=n_cmte)),
            "debts_owed": np.zeros(n_cmte),
        }
    )
    committees["committee_type_full"] = committees["committee_type"].map(
        COMMITTEE_TYPES
    )
    tables = derive_tables(candidates, committees)
    tables["candidates"] = candidates
    tables["committees"] = committees
    return tables


def build_live(use_cache: bool) -> dict[str, object]:
    """Full live build: download, clean, fetch API, build, cross-check."""
    record: dict[str, object] = {
        "source": "live",
        "attribution": ATTRIBUTION,
        "cycle": CYCLE,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthetic": False,
        "bulk_base_url": BULK_BASE,
        "api_base_url": API_BASE,
    }
    # 1. Bulk downloads.
    zip_sizes: dict[str, int] = {}
    for filename in BULK_FILES:
        dest = RAW / filename
        if use_cache and dest.exists():
            zip_sizes[filename] = dest.stat().st_size
        else:
            download_bulk(filename, dest)
            zip_sizes[filename] = dest.stat().st_size
    record["zip_sizes_bytes"] = zip_sizes
    # 2. Unpack + load.
    txt_paths = {fn: unpack_bulk(RAW / fn, RAW) for fn in BULK_FILES}
    unpacked_sizes = {fn: txt_paths[fn].stat().st_size for fn in BULK_FILES}
    record["unpacked_sizes_bytes"] = unpacked_sizes
    cn_raw = load_bulk_txt(txt_paths["cn24.zip"], CN_COLUMNS)
    webk_raw = load_bulk_txt(txt_paths["webk24.zip"], WEBK_COLUMNS)
    ccl_raw = load_bulk_txt(txt_paths["ccl24.zip"], CCL_COLUMNS)
    webl_raw = load_bulk_txt(txt_paths["webl24.zip"], WEBL_COLUMNS)
    record["raw_rows"] = {
        "cn": len(cn_raw),
        "webk": len(webk_raw),
        "ccl": len(ccl_raw),
        "webl": len(webl_raw),
    }
    record["layout"] = {
        "header_row": False,
        "date_format": "MM/DD/YYYY",
        "money_format": "plain numbers, no $/commas",
        "verified_by": "API match to the cent (H2AK01158, H2AK01083) + cash identity",
        "undecoded_webl_columns": [
            "col_04",
            "col_09",
            "col_12",
            "col_13",
            "col_14",
            "col_15",
            "col_16",
            "col_26",
            "col_27",
            "col_29",
            "col_30",
        ],
        "webl_debts_column_note": (
            "webl f17 decoded as debts_owed_by: it equals the API's "
            "debts_owed_by_committee (934179.58) for P80000722 and "
            "P00009423; the cross-check verifies it across the sample."
        ),
    }
    # 3. Clean.
    cn, cn_counts = clean_candidates(cn_raw)
    webk, webk_counts = clean_committees(webk_raw)
    record["cleaning"] = {"cn": cn_counts, "webk": webk_counts}
    record["ccl_rows"] = len(ccl_raw)
    record["ccl_duplicate_candidate_committee"] = int(
        ccl_raw.duplicated(subset=["candidate_id", "committee_id"]).sum()
    )
    # 4. Cash-identity layout checks (aggregate, plan §11 item 14).
    webk_identity = cash_identity_report(
        webk_raw.assign(
            receipts=to_money(webk_raw["receipts"]),
            disbursements=to_money(webk_raw["disbursements"]),
            cash_bop=to_money(webk_raw["cash_bop"]),
            cash_cop=to_money(webk_raw["cash_cop"]),
        )
    )
    webl_identity = cash_identity_report(
        webl_raw.assign(
            receipts=to_money(webl_raw["receipts"]),
            disbursements=to_money(webl_raw["disbursements"]),
            cash_bop=to_money(webl_raw["cash_bop"]),
            cash_cop=to_money(webl_raw["cash_cop"]),
        )
    )
    record["cash_identity"] = {"webk": webk_identity, "webl": webl_identity}
    # 5. API candidate totals.
    totals, api_stats = fetch_candidate_totals(RAW, use_cache)
    record["api_fetch"] = api_stats
    # 6. Build tables.
    candidates, cand_counts = build_candidate_table(totals, cn, webl_raw)
    record["candidate_table"] = cand_counts
    # Principal committees from the linkage file (plan §11 item 22):
    # candidates whose master row is not a 2024 record (79 rows, §11
    # item 22) have no principal committee in cn, but ccl names their
    # principal committee (designation P). Fill those in before the
    # principal set is computed; committees not in webk are unaffected.
    pcc_map = (
        ccl_raw[ccl_raw["designation"] == "P"]
        .drop_duplicates(subset=["candidate_id"], keep="first")
        .set_index("candidate_id")["committee_id"]
    )
    blank_pcc = candidates["principal_committee_id"].replace("", np.nan).isna()
    filled_pcc = candidates["candidate_id"].map(pcc_map)
    n_filled = int((blank_pcc & filled_pcc.notna()).sum())
    candidates["principal_committee_id"] = (
        candidates["principal_committee_id"]
        .replace("", np.nan)
        .fillna(filled_pcc)
        .fillna("")
    )
    cand_counts["principal_committee_filled_from_ccl"] = n_filled
    principals = principal_committees(candidates)
    record["principal_committees_distinct"] = len(principals)
    record["principal_committees_in_webk"] = len(principals & set(webk["committee_id"]))
    committees, cmte_counts = build_committee_table(webk, principals)
    record["committee_table"] = cmte_counts
    record["committee_types"] = {
        str(k): int(v) for k, v in webk["committee_type"].value_counts().items()
    }
    record["committee_type_full_mapping"] = COMMITTEE_TYPES
    tables = derive_tables(candidates, committees)
    tables["candidates"] = candidates
    tables["committees"] = committees
    # 7. Cross-check result (computed inside build_candidate_table, before
    # the webl override — see §11 item 17).
    record["cross_check_webl_vs_api"] = cand_counts["cross_check_list_vs_webl"]
    write_tables(tables, PROC)
    # 8. Cycle totals per universe (plan §4.2, amended). Committee totals
    # use the committee TABLE (non-principal committees only, matching
    # committees.csv exactly) — the 12 principal committees present in
    # webk are excluded here because their money is already inside the
    # candidate totals; their dollars are recorded separately below so
    # the two universes still reconcile to the all-webk total.
    with_totals = candidates[candidates["has_totals"]]
    principal_receipts = float(webk["receipts"].fillna(0).sum()) - float(
        committees["receipts"].fillna(0).sum()
    )
    all_webk_receipts = float(webk["receipts"].fillna(0).sum())
    n_principals = int(webk["committee_id"].nunique()) - int(
        committees["committee_id"].nunique()
    )
    record["cycle_totals"] = {
        "candidate_receipts_usd": float(with_totals["receipts"].fillna(0).sum()),
        "candidate_disbursements_usd": float(
            with_totals["disbursements"].fillna(0).sum()
        ),
        "candidate_cash_on_hand_usd": float(
            with_totals["cash_on_hand"].fillna(0).sum()
        ),
        "committee_receipts_usd": float(committees["receipts"].fillna(0).sum()),
        "committee_disbursements_usd": float(
            committees["disbursements"].fillna(0).sum()
        ),
        "committee_cash_on_hand_usd": float(committees["cash_on_hand"].fillna(0).sum()),
        "n_candidates_with_totals": int(with_totals["candidate_id"].nunique()),
        "n_committees_with_summary": int(committees["committee_id"].nunique()),
        "principal_committees_in_webk": n_principals,
        "principal_committees_receipts_usd": principal_receipts,
        "transfer_disclosure": (
            "Candidate and committee figures are sums of filings in two "
            "separate universes; a combined figure would double-count "
            "dollars transferred between committees. The committee total "
            f"excludes the {n_principals} principal committees present in "
            "webk (their "
            f"${principal_receipts / 1e6:,.1f}M of receipts is "
            "already inside the candidate totals); the all-webk committee "
            f"total was ${all_webk_receipts / 1e6:,.1f}M."
        ),
    }
    # 9. State-table exclusions and single-filing concentration (plan §11
    # items 18–19). Values are reported as filed and never altered.
    excluded_states = candidates[
        candidates["state"].isin(["00", "US"]) & candidates["has_totals"]
    ]
    record["state_table"] = {
        "n_excluded_non_state_codes": len(excluded_states),
        "excluded_receipts_usd": float(excluded_states["receipts"].fillna(0).sum()),
        "excluded_disbursements_usd": float(
            excluded_states["disbursements"].fillna(0).sum()
        ),
        "note": (
            "Candidates whose state code is '00' or 'US' (no usable state "
            "on file, mostly presidential) are excluded from "
            "state_totals.csv; their money is still in the candidate totals."
        ),
    }
    cash_total = float(with_totals["cash_on_hand"].fillna(0).sum())
    top_cash = with_totals.sort_values(
        ["cash_on_hand", "candidate_id"], ascending=[False, True]
    ).iloc[0]
    zero_receipt = with_totals[with_totals["receipts"].fillna(0) == 0]
    top_zero = (
        zero_receipt.sort_values(
            ["disbursements", "candidate_id"], ascending=[False, True]
        ).iloc[0]
        if len(zero_receipt)
        else None
    )
    record["cash_concentration"] = {
        "top_cash_candidate_id": str(top_cash["candidate_id"]),
        "top_cash_candidate_name": str(top_cash["candidate_name"]),
        "top_cash_usd": float(top_cash["cash_on_hand"]),
        "top_cash_share_of_total": (
            float(top_cash["cash_on_hand"]) / cash_total if cash_total else 0.0
        ),
        "cash_total_excluding_top_usd": cash_total - float(top_cash["cash_on_hand"]),
        "zero_receipt_disbursements_usd": float(
            zero_receipt["disbursements"].fillna(0).sum()
        ),
        "zero_receipt_top_candidate_id": (
            str(top_zero["candidate_id"]) if top_zero is not None else ""
        ),
        "zero_receipt_top_disbursements_usd": (
            float(top_zero["disbursements"]) if top_zero is not None else 0.0
        ),
        "note": (
            "One candidate's filed cash on hand is more than half the "
            "cycle total and its filing fails the cash-identity check; "
            "see README. Values are reported as filed, never altered."
        ),
    }
    write_data_source(PROC / "data_source.json", record)
    return record


def build_offline() -> dict[str, object]:
    """Regenerate derived tables from the committed CSVs (no network).

    Never touches data_source.json when a live record exists (plan §3.5).
    """
    source_path = PROC / "data_source.json"
    record: dict[str, object] = {}
    if source_path.exists():
        record = json.loads(source_path.read_text(encoding="utf-8"))
        if record.get("source") == "live" and not record.get("synthetic"):
            # Live record exists: regenerate derived tables only.
            candidates = pd.read_csv(PROC / "candidates.csv")
            committees = pd.read_csv(PROC / "committees.csv")
            tables = derive_tables(candidates, committees)
            write_tables(tables, PROC)
            return {"mode": "offline", "data_source": "live record preserved"}
    # No live record (e.g. synthetic build): rebuild from whatever is there.
    candidates = pd.read_csv(PROC / "candidates.csv")
    committees = pd.read_csv(PROC / "committees.csv")
    tables = derive_tables(candidates, committees)
    write_tables(tables, PROC)
    return {"mode": "offline", "data_source": "no live record to preserve"}


def build_synthetic() -> dict[str, object]:
    """Labelled-synthetic fallback (brief §4, seed 42)."""
    tables = synthetic_tables()
    write_tables(tables, PROC)
    record: dict[str, object] = {
        "source": "synthetic",
        "attribution": ATTRIBUTION,
        "cycle": CYCLE,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthetic": True,
        "seed": 42,
        "note": "SYNTHETIC — NOT REAL DATA. Live sources unreachable.",
    }
    write_data_source(PROC / "data_source.json", record)
    return record


def main(argv: list[str] | None = None) -> int:
    """CLI: --live | --offline | --use-cache | --synthetic."""
    parser = argparse.ArgumentParser(description="Day 13 FEC data pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true", help="download + API + build")
    group.add_argument(
        "--offline", action="store_true", help="rebuild derived tables, no network"
    )
    group.add_argument(
        "--use-cache", action="store_true", help="live build from cached downloads"
    )
    group.add_argument("--synthetic", action="store_true", help="synthetic fallback")
    args = parser.parse_args(argv)
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    if args.live:
        record = build_live(use_cache=False)
    elif args.use_cache:
        record = build_live(use_cache=True)
    elif args.offline:
        record = build_offline()
    else:
        record = build_synthetic()
    print(json.dumps(record, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
