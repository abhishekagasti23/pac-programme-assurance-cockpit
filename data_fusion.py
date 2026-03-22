"""
PAC — Programme Assurance Cockpit
Data Fusion Engine: Medallion Architecture (Bronze → Silver → Gold)

Bronze: raw ingested data — any format, any quality, timestamped on arrival
Silver: cleaned, standardised, quality-flagged, common schema across all sources
Gold:   computed metrics — SPI, CPI, risk scores, composite health, trend

This is what "data fusion" actually means in infra consulting:
taking P6 XER, Excel cost trackers, risk registers, and governance logs
from 20 different project teams who all do things differently,
and producing ONE reliable, auditable programme health view.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

# ─── DATA FRESHNESS THRESHOLDS ────────────────────────────────────────────────
FRESHNESS_THRESHOLDS = {
    "schedule":   14,   # days: P6 export should refresh every 2 weeks
    "cost":       30,   # days: ERP extract monthly is standard
    "risk":       30,   # days: risk register reviewed monthly
    "governance": 14,   # days: action log should refresh weekly
}

FRESHNESS_LABELS = {
    "fresh":   "Current",
    "stale":   "Stale",
    "missing": "Missing",
}

# ─── BRONZE LAYER — raw ingestion record ─────────────────────────────────────

def create_bronze_record(
    project_id: str,
    project_name: str,
    source_data: dict,
    ingestion_time: datetime = None,
) -> dict:
    """
    Bronze: stamp everything with arrival time and source.
    Never transform — just receive and record.
    """
    return {
        "bronze_id": f"BRZ-{project_id}-{(ingestion_time or datetime.now()).strftime('%Y%m%d%H%M')}",
        "project_id": project_id,
        "project_name": project_name,
        "ingested_at": ingestion_time or datetime.now(),
        "source_system": source_data.get("source_system", "UNKNOWN"),
        "raw_payload": source_data,
    }


# ─── SILVER LAYER — cleaned, standardised ────────────────────────────────────

SILVER_SCHEMA = {
    # Identity
    "project_id":             str,
    "project_name":           str,
    "sector":                 str,   # Transport | Energy | Urban
    "programme":              str,   # parent programme name
    "contractor":             str,
    "contract_type":          str,
    "contract_value":         float, # £/$ original contract value
    "data_date":              object,# datetime

    # Schedule health inputs
    "planned_start":          object,
    "planned_finish":         object,
    "forecast_finish":        object,
    "spi":                    float, # Schedule Performance Index
    "total_float_days":       float,
    "schedule_updated_at":    object,# when P6 was last exported

    # Cost health inputs
    "budget":                 float,
    "acwp":                   float, # Actual Cost of Work Performed
    "bcwp":                   float, # Budgeted Cost of Work Performed (EV)
    "eac":                    float, # Estimate at Completion
    "cpi":                    float, # Cost Performance Index
    "cost_updated_at":        object,

    # Risk health inputs
    "risk_score":             float, # 0–10 composite from risk register
    "top_risk_description":   str,
    "risks_materialised_30d": int,   # risks that materialised in last 30 days
    "risk_updated_at":        object,

    # Governance health inputs
    "overdue_actions":        int,   # actions past due date
    "outstanding_approvals":  int,   # decisions awaiting approval
    "audit_findings_open":    int,   # open audit findings
    "days_since_board_review": int,
    "governance_updated_at":  object,

    # Gate readiness
    "next_gate":              str,   # name of next decision gate
    "next_gate_date":         object,
    "gate_deliverables_total":int,
    "gate_deliverables_complete": int,

    # Metadata
    "pct_complete":           float,
    "phase":                  str,
}

def ingest_to_silver(raw_projects: pd.DataFrame, data_date: datetime = None) -> pd.DataFrame:
    """
    Silver layer: map any input DataFrame to the standard schema.
    Missing fields get sensible defaults. Types enforced.
    Data quality flags added.
    """
    data_date = data_date or datetime.now()
    silver = pd.DataFrame()

    for col, dtype in SILVER_SCHEMA.items():
        if col in raw_projects.columns:
            if dtype == float:
                silver[col] = pd.to_numeric(raw_projects[col], errors="coerce").fillna(0.0)
            elif dtype == int:
                silver[col] = pd.to_numeric(raw_projects[col], errors="coerce").fillna(0).astype(int)
            elif dtype == str:
                silver[col] = raw_projects[col].astype(str).str.strip()
            elif dtype == object:  # datetime
                silver[col] = pd.to_datetime(raw_projects[col], errors="coerce")
            else:
                silver[col] = raw_projects[col]
        else:
            # Sensible defaults
            if dtype == float: silver[col] = 0.0
            elif dtype == int:  silver[col] = 0
            elif dtype == str:  silver[col] = ""
            else:               silver[col] = pd.NaT

    # Derive CPI if not supplied but ACWP/BCWP are
    mask_no_cpi = (silver["cpi"] == 0.0) & (silver["acwp"] > 0)
    silver.loc[mask_no_cpi, "cpi"] = (
        silver.loc[mask_no_cpi, "bcwp"] / silver.loc[mask_no_cpi, "acwp"]
    ).clip(0.5, 1.5)

    # Derive SPI if not supplied
    mask_no_spi = (silver["spi"] == 0.0) & (silver["pct_complete"] > 0)
    if "planned_start" in silver.columns and "planned_finish" in silver.columns:
        elapsed_frac = np.where(
            silver["planned_finish"].notna() & silver["planned_start"].notna(),
            ((data_date - silver["planned_start"]).dt.days /
             (silver["planned_finish"] - silver["planned_start"]).dt.days.clip(lower=1)),
            0.5
        )
        silver.loc[mask_no_spi, "spi"] = np.clip(
            (silver.loc[mask_no_spi, "pct_complete"] / 100) /
            np.clip(elapsed_frac[mask_no_spi], 0.01, 1.0),
            0.3, 1.3
        )
    silver["spi"] = silver["spi"].clip(0.3, 1.3)

    # Data freshness flags
    for source in ["schedule", "cost", "risk", "governance"]:
        updated_col = f"{source}_updated_at"
        freshness_col = f"{source}_freshness"
        threshold = FRESHNESS_THRESHOLDS[source]

        if updated_col in silver.columns and silver[updated_col].notna().any():
            days_stale = (data_date - silver[updated_col]).dt.days
            silver[freshness_col] = np.where(
                silver[updated_col].isna(), "missing",
                np.where(days_stale > threshold, "stale", "fresh")
            )
        else:
            silver[freshness_col] = "missing"

    silver["data_date"] = data_date
    return silver


# ─── GOLD LAYER — computed metrics ───────────────────────────────────────────

def compute_gold(silver: pd.DataFrame, data_date: datetime = None) -> pd.DataFrame:
    """
    Gold layer: all derived metrics.
    Health scores, RAG status, trend, confidence, gate readiness.
    """
    data_date = data_date or datetime.now()
    gold = silver.copy()

    # ── Schedule health score (0–100) ─────────────────────────────────────────
    # SPI: 1.0=perfect, <0.85=concerning, <0.7=critical
    spi_score = np.clip((gold["spi"] - 0.5) / 0.5 * 100, 0, 100)
    # Float: >20d=good, <5d=critical
    float_score = np.clip(gold["total_float_days"] / 20 * 100, 0, 100)
    # Schedule variance from forecast vs planned finish
    if gold["forecast_finish"].notna().any() and gold["planned_finish"].notna().any():
        sv_days = (gold["planned_finish"] - gold["forecast_finish"]).dt.days.fillna(0)
        sv_score = np.clip((sv_days + 60) / 120 * 100, 0, 100)  # +60d = 0, 0 = 50, -60d = 100(bad)
        sv_score = 100 - sv_score  # invert: negative variance = bad score
    else:
        sv_score = 50.0

    gold["schedule_health"] = np.clip(
        spi_score * 0.50 + float_score * 0.25 + sv_score * 0.25, 0, 100
    ).round(1)

    # ── Cost health score (0–100) ─────────────────────────────────────────────
    cpi_score = np.clip((gold["cpi"] - 0.6) / 0.4 * 100, 0, 100)
    if "eac" in gold.columns and "budget" in gold.columns:
        vac_pct = np.where(
            gold["budget"] > 0,
            (gold["budget"] - gold["eac"]) / gold["budget"] * 100,
            0
        )
        vac_score = np.clip((vac_pct + 30) / 60 * 100, 0, 100)
    else:
        vac_score = 50.0

    gold["cost_health"] = np.clip(cpi_score * 0.60 + vac_score * 0.40, 0, 100).round(1)

    # ── Risk health score (0–100) ─────────────────────────────────────────────
    risk_score_raw = np.clip((10 - gold["risk_score"]) / 10 * 100, 0, 100)
    materialised_penalty = np.clip(gold["risks_materialised_30d"] * 15, 0, 50)
    gold["risk_health"] = np.clip(risk_score_raw - materialised_penalty, 0, 100).round(1)

    # ── Governance health score (0–100) ───────────────────────────────────────
    overdue_penalty = np.clip(gold["overdue_actions"] * 8, 0, 40)
    approval_penalty = np.clip(gold["outstanding_approvals"] * 6, 0, 30)
    audit_penalty = np.clip(gold["audit_findings_open"] * 10, 0, 30)
    board_penalty = np.clip((gold["days_since_board_review"] - 30) / 30 * 20, 0, 20)
    gold["governance_health"] = np.clip(
        100 - overdue_penalty - approval_penalty - audit_penalty - board_penalty, 0, 100
    ).round(1)

    # ── Composite score (weighted) ─────────────────────────────────────────────
    gold["composite_score"] = np.clip(
        gold["schedule_health"]   * 0.30 +
        gold["cost_health"]       * 0.30 +
        gold["risk_health"]       * 0.25 +
        gold["governance_health"] * 0.15,
        0, 100
    ).round(1)

    # ── Confidence weighting ──────────────────────────────────────────────────
    freshness_weights = {
        "fresh":   1.0,
        "stale":   0.70,
        "missing": 0.40,
    }
    confidence_components = []
    for source in ["schedule", "cost", "risk", "governance"]:
        col = f"{source}_freshness"
        if col in gold.columns:
            confidence_components.append(
                gold[col].map(freshness_weights).fillna(0.40)
            )

    if confidence_components:
        gold["data_confidence"] = pd.concat(confidence_components, axis=1).mean(axis=1).round(2)
    else:
        gold["data_confidence"] = 0.70

    # Confidence-adjusted score
    gold["adjusted_score"] = (
        gold["composite_score"] * gold["data_confidence"]
        + 50 * (1 - gold["data_confidence"])  # pull toward 50 (uncertain) when stale
    ).round(1)

    # ── RAG status ───────────────────────────────────────────────────────────
    def rag(score: float, confidence: float) -> str:
        if confidence < 0.5:
            return "GREY"     # insufficient data confidence
        if score >= 70:
            return "GREEN"
        elif score >= 45:
            return "AMBER"
        else:
            return "RED"

    gold["rag_status"] = [
        rag(s, c) for s, c in zip(gold["adjusted_score"], gold["data_confidence"])
    ]

    # ── Trend (vs last period) ────────────────────────────────────────────────
    # In a live system this would compare to last week's gold record.
    # Here we synthesise a trend from the score distribution
    if "prev_composite_score" in gold.columns:
        delta = gold["composite_score"] - gold["prev_composite_score"]
        gold["trend"] = np.where(delta > 3, "↑", np.where(delta < -3, "↓", "→"))
        gold["trend_delta"] = delta.round(1)
    else:
        # Synthesise trend for demo — derived from score headroom
        gold["trend"] = np.where(
            gold["composite_score"] < 40, "↓",
            np.where(gold["composite_score"] > 75, "↑", "→")
        )
        gold["trend_delta"] = 0.0

    # ── Gate readiness ─────────────────────────────────────────────────────────
    gold["gate_readiness_pct"] = np.where(
        gold["gate_deliverables_total"] > 0,
        (gold["gate_deliverables_complete"] / gold["gate_deliverables_total"] * 100).clip(0, 100),
        np.nan
    ).round(0)

    if gold["next_gate_date"].notna().any():
        days_to_gate = (gold["next_gate_date"] - data_date).dt.days
        gold["days_to_gate"] = days_to_gate
        # Gate risk: low readiness + imminent gate = RED flag
        gold["gate_flag"] = (
            (gold["gate_readiness_pct"].fillna(0) < 60) &
            (days_to_gate.fillna(999) < 60)
        )
    else:
        gold["days_to_gate"] = np.nan
        gold["gate_flag"] = False

    # ── Confidence label ─────────────────────────────────────────────────────
    gold["confidence_label"] = pd.cut(
        gold["data_confidence"],
        bins=[0, 0.5, 0.75, 1.01],
        labels=["Low confidence", "Medium confidence", "High confidence"],
    )

    return gold


def run_medallion(raw_projects: pd.DataFrame, data_date: datetime = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Full Bronze → Silver → Gold pipeline.
    Returns (bronze_summary, silver_df, gold_df).
    """
    data_date = data_date or datetime.now()

    # Bronze: just a log
    bronze_log = pd.DataFrame([{
        "project_id": row.get("project_id", f"P{i:02d}"),
        "ingested_at": data_date,
        "row_count": len(raw_projects),
        "source": row.get("source_system", "UPLOAD"),
    } for i, row in raw_projects.head(1).iterrows()])

    silver = ingest_to_silver(raw_projects, data_date)
    gold = compute_gold(silver, data_date)

    return bronze_log, silver, gold
