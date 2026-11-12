"""Day 8 — Hospital Readmission Risk Model: offline pytest suite.

Covers the "?"-as-missing rule (incl. the "None"-is-a-category trap),
discharge exclusions with the label-governs guard, ICD-9 grouping,
the patient-grouped split (zero overlap), the pure metric functions
with hand-checked fixtures, the offline path never clobbering the live
record (Day 5/6 lesson), the synthetic fallback staying labelled and
never overwriting live files, the data-size rule, and the SQL-vs-pandas
check. Runs from the repo root and from inside the day folder.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline as pipeline
from src.metrics import (
    brier_score,
    calibration_in_the_large,
    calibration_slope_intercept,
    confusion_metrics,
    decile_table,
    prevalence_brier,
)
from src.model import patient_group_split

PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


def _record() -> dict:
    return json.loads((PROCESSED / "data_source.json").read_text())


def _sample() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "sample_encounters.csv")


# --- Loading / missing-value rules ----------------------------------------

RAW_FIXTURE = (
    "encounter_id,patient_nbr,race,weight,max_glu_serum,A1Cresult,readmitted\n"
    "1,101,Caucasian,?,None,None,NO\n"
    "2,102,?,80,>200,>8,<30\n"
    "3,103,Asian,?,Norm,Norm,>30\n"
)


def test_question_mark_is_missing(tmp_path):
    path = tmp_path / "mini.csv"
    path.write_text(RAW_FIXTURE, encoding="utf-8")
    df = pipeline.load_raw(path)
    assert df["weight"].isna().sum() == 2
    assert df["race"].isna().sum() == 1
    # "None" is a real category (not measured) — it must NOT become NaN.
    assert df["max_glu_serum"].tolist() == ["None", ">200", "Norm"]
    assert df["A1Cresult"].tolist() == ["None", ">8", "Norm"]


def test_weight_missing_rate_about_97_percent():
    record = _record()
    rate = record["weight_missing_rate"]
    assert 0.95 < rate < 0.99, f"weight missing rate {rate} is not ≈97%"


def test_high_missing_categoricals_reported():
    rates = _record()["missing_rates"]
    assert 0.45 < rates["medical_specialty"] < 0.55
    assert 0.35 < rates["payer_code"] < 0.45


def test_target_distribution_matches_brief():
    record = _record()
    assert record["expected_target"] == {"<30": 11357, ">30": 35545, "NO": 54864}
    assert record["target_distribution_raw"] == {
        "<30": 11357,
        ">30": 35545,
        "NO": 54864,
    }
    assert record["n_raw"] == 101_766


# --- Exclusions -------------------------------------------------------------


def test_exclusion_labels_are_expired_or_hospice():
    info = _record()["exclusions"]
    assert info["excluded_ids"] == [11, 19, 20, 21]
    assert info["deviation"] is None
    for code, label in info["excluded_labels"].items():
        assert (
            "expired" in label.lower() or "hospice" in label.lower()
        ), f"id {code} label {label!r} is not Expired/Hospice"
    assert sum(info["excluded_counts_per_id"].values()) == info["n_excluded"]
    assert info["n_excluded"] == 1652
    assert info["excluded_counts_per_id"] == {"11": 1642, "19": 8, "20": 2, "21": 0}


def _exclusion_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "discharge_disposition_id": [1, 11, 19, 20, 21, 2, 13],
            "readmitted": ["NO", "NO", "NO", "NO", "NO", "<30", "NO"],
        }
    )


def test_apply_exclusions_fixture():
    mapping = {
        "discharge_disposition_id": {
            1: "Discharged to home",
            11: "Expired",
            19: "Expired at home. Medicaid only, hospice.",
            20: "Expired in a medical facility. Medicaid only, hospice.",
            21: "Expired, place unknown. Medicaid only, hospice.",
            2: "Discharged/transferred to another short term hospital",
            13: "Hospice / home",
        }
    }
    kept, info = pipeline.apply_exclusions(_exclusion_frame(), mapping)
    # Frozen list {11, 19, 20, 21} only — id 13 (Hospice / home) is kept.
    assert sorted(kept["discharge_disposition_id"]) == [1, 2, 13]
    assert info["n_excluded"] == 4


def test_label_rule_governs_when_ids_disagree():
    mapping = {
        "discharge_disposition_id": {
            1: "Discharged to home",
            11: "Discharged to home",  # label disagrees with the frozen id
            99: "Hospice / home",
        }
    }
    df = pd.DataFrame(
        {"discharge_disposition_id": [1, 11, 99], "readmitted": ["NO"] * 3}
    )
    kept, info = pipeline.apply_exclusions(df, mapping)
    assert info["deviation"] is not None
    assert info["excluded_ids"] == [99]
    assert sorted(kept["discharge_disposition_id"]) == [1, 11]


def test_load_id_mapping_sections(tmp_path):
    path = tmp_path / "IDS_mapping.csv"
    path.write_text(
        "admission_type_id,description\n1,Emergency\n2,Urgent\n,\n"
        'discharge_disposition_id,description\n11,Expired\n19,"Expired at '
        'home. Medicaid only, hospice."\n',
        encoding="utf-8",
    )
    mapping = pipeline.load_id_mapping(path)
    assert mapping["admission_type_id"] == {1: "Emergency", 2: "Urgent"}
    assert mapping["discharge_disposition_id"][19] == (
        "Expired at home. Medicaid only, hospice."
    )


# --- ICD-9 grouping + target -----------------------------------------------


@pytest.mark.parametrize(
    "code,expected",
    [
        ("250.13", "Diabetes"),
        ("250", "Diabetes"),
        ("428", "Circulatory"),
        ("786.05", "Respiratory"),
        ("460", "Respiratory"),
        ("520", "Digestive"),
        ("580", "Genitourinary"),
        ("710", "Musculoskeletal"),
        ("140", "Neoplasms"),
        ("800", "Injury & poisoning"),
        ("999", "Injury & poisoning"),
        ("V57", "Other"),
        ("E880", "Other"),
        ("001", "Other"),
        ("?", "Missing"),
        (None, "Missing"),
        (float("nan"), "Missing"),
    ],
)
def test_group_icd9_fixtures(code, expected):
    assert pipeline.group_icd9(code) == expected


def test_make_binary_target():
    s = pd.Series(["<30", ">30", "NO", "<30"])
    assert pipeline.make_binary_target(s).tolist() == [1, 0, 0, 1]


# --- Split ------------------------------------------------------------------


def test_patient_group_split_no_overlap_and_share():
    sample = _sample()
    train_idx, test_idx = patient_group_split(sample)
    train_patients = set(sample.loc[train_idx, "patient_nbr"])
    test_patients = set(sample.loc[test_idx, "patient_nbr"])
    assert not train_patients & test_patients
    share = len(test_idx) / len(sample)
    assert 0.18 <= share <= 0.22, f"test share {share:.3f} outside 18–22%"
    record = _record()
    assert record["split"]["patient_overlap"] == 0
    assert record["split"]["train_rows"] == 80_090
    assert record["split"]["test_rows"] == 20_024


def test_sample_target_rate_close_to_prevalence():
    sample = _sample()
    assert len(sample) == 1_000
    rate = sample["target"].mean()
    assert abs(rate - 0.1116) < 0.03, f"sample target rate {rate:.4f}"


# --- Pure metrics, hand-checked ----------------------------------------------


def test_brier_score_hand_check():
    # (0.1-0)^2 = 0.01 and (0.9-1)^2 = 0.01 -> mean 0.01.
    assert brier_score([0, 1], [0.1, 0.9]) == pytest.approx(0.01)


def test_prevalence_brier_hand_check():
    # 0.1116 * (1 - 0.1116) = 0.09914...
    assert prevalence_brier(0.1116) == pytest.approx(0.0991, abs=0.0001)
    assert prevalence_brier(0.5) == pytest.approx(0.25)


def test_calibration_slope_intercept_hand_check():
    y = [0, 0, 0, 1, 1, 1]
    p = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    slope, intercept = calibration_slope_intercept(y, p)
    assert slope > 0
    assert abs(intercept) < 1.0
    mean_pred, observed = calibration_in_the_large(y, p)
    assert mean_pred == pytest.approx(0.5)
    assert observed == pytest.approx(0.5)


def test_decile_table_hand_check():
    y = [0] * 9 + [1]
    p = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
    table = decile_table(y, p)
    assert len(table) == 10
    assert table["n"].sum() == 10
    assert table.iloc[9]["observed_rate"] == pytest.approx(1.0)
    assert table.iloc[0]["observed_rate"] == pytest.approx(0.0)
    assert table["mean_predicted"].is_monotonic_increasing


def test_confusion_metrics_hand_check():
    result = confusion_metrics([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9], threshold=0.5)
    assert (result["tp"], result["tn"], result["fp"], result["fn"]) == (1, 1, 1, 1)
    assert result["sensitivity"] == pytest.approx(0.5)
    assert result["specificity"] == pytest.approx(0.5)
    assert result["precision"] == pytest.approx(0.5)
    assert result["npv"] == pytest.approx(0.5)
    assert result["f1"] == pytest.approx(0.5)


# --- Committed outputs -------------------------------------------------------


def test_model_metrics_sanity():
    metrics = pd.read_csv(PROCESSED / "model_metrics.csv")
    assert set(metrics["model"]) == {"logistic", "histgb"}
    for _, row in metrics.iterrows():
        assert row["roc_auc"] > 0.5
        assert row["pr_auc"] > 0.1116
        assert row["brier"] < row["brier_baseline"]
        assert row["cv_roc_auc_mean"] > 0.5
    # data_source.json must carry the same numbers as model_metrics.csv.
    record = _record()
    for row in record["metrics"]:
        csv_row = metrics[metrics["model"] == row["model"]].iloc[0]
        assert row["roc_auc"] == pytest.approx(csv_row["roc_auc"], abs=1e-9)
        assert row["pr_auc"] == pytest.approx(csv_row["pr_auc"], abs=1e-9)


def test_subgroup_small_n_flag_logic():
    sub = pd.read_csv(PROCESSED / "subgroup_metrics.csv")
    expected_flag = (sub["n"] < 500) | (sub["positives"] < 50)
    assert expected_flag.eq(sub["small_n"]).all()
    assert sub["n"].sum() > 0
    # Every model x subgroup-type group sums to the test size.
    for model in ("logistic", "histgb"):
        age_n = sub[(sub["model"] == model) & (sub["subgroup_type"] == "age_band")][
            "n"
        ].sum()
        assert age_n == 20_024


def test_calibration_deciles_shape():
    deciles = pd.read_csv(PROCESSED / "calibration_deciles.csv")
    assert len(deciles) == 20  # 2 models x 10 deciles
    for model in ("logistic", "histgb"):
        d = deciles[deciles["model"] == model]
        assert d["n"].sum() == 20_024
        assert d["mean_predicted"].is_monotonic_increasing


# --- Offline / synthetic guards ----------------------------------------------


def test_offline_does_not_clobber_data_source():
    path = PROCESSED / "data_source.json"
    before = path.read_bytes()
    assert pipeline.main(["--offline"]) == 0
    assert path.read_bytes() == before
    assert json.loads(before)["source"] == "live"


def test_synthetic_frame_is_labelled_and_never_overwrites_live():
    frame = pipeline.build_synthetic_frame()
    assert len(frame) == 20_000
    assert abs(frame["target"].mean() - 0.112) < 0.02
    assert pipeline.SYNTHETIC_CSV_NAME != pipeline.RAW_CSV_NAME
    assert pipeline.SYNTHETIC_CSV_NAME.endswith("_synthetic.csv")
    # Same generator + seed reproduces the same frame.
    again = pipeline.build_synthetic_frame()
    pd.testing.assert_frame_equal(frame, again)
    # The live record in the tree is not synthetic.
    assert _record().get("synthetic") is False


# --- Data-size rule -----------------------------------------------------------


def test_no_committed_file_over_1mb_and_data_under_5mb():
    ignored = {"diabetic_data.csv"}
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        if path.name in ignored or path.suffix == ".zip":
            continue  # git-ignored raw data, not committed
        assert (
            path.stat().st_size <= 1_000_000
        ), f"{path} is {path.stat().st_size:,} bytes (> 1 MB)"
        total += path.stat().st_size
    assert total < 5_000_000, f"committed data/ is {total:,} bytes (>= 5 MB)"


# --- Chart honesty rules (plan §7; tester defects D-1/D-2, fixed 2026-11-12) ---


def test_chart_04b_y_axis_starts_at_zero():
    src = (ROOT / "src" / "make_charts.py").read_text()
    assert "set_ylim(0, 0.9)" in src
    assert "set_ylim(0.5, 0.85)" not in src


def test_chart_03_footnote_matches_legend_brier_baseline():
    src = (ROOT / "src" / "make_charts.py").read_text()
    # Legend renders the committed brier_baseline 0.1006 as "(baseline 0.101)";
    # the footnote must quote the same 0.1006 as the test-set baseline and
    # label 0.0991 explicitly as the raw-prevalence baseline.
    assert "0.1006 at the" in src and "test-set prevalence" in src
    assert "0.0991 at the raw prevalence" in src
    metrics = pd.read_csv(PROCESSED / "model_metrics.csv")
    assert all(abs(v - 0.1006) < 1e-9 for v in metrics["brier_baseline"])


# --- SQL check (plan §4.7) ----------------------------------------------------


def test_sql_vs_pandas_agreement():
    sample = _sample()
    with sqlite3.connect(":memory:") as conn:
        sample.to_sql("encounters", conn, index=False)
        sql = conn.execute(
            "SELECT age, AVG(target) AS rate, COUNT(*) AS n "
            "FROM encounters GROUP BY age ORDER BY age"
        ).fetchall()
    pandas = (
        sample.groupby("age")["target"]
        .agg(["mean", "size"])
        .reset_index()
        .sort_values("age")
    )
    assert len(sql) == len(pandas)
    for (age, rate, n), (_, row) in zip(sql, pandas.iterrows()):
        assert age == row["age"]
        assert rate == pytest.approx(row["mean"], abs=1e-9)
        assert n == row["size"]
