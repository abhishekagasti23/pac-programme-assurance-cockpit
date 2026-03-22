"""
PAC — Programme Assurance Cockpit
Health Engine: composite scoring, gate readiness prediction, trend analysis.
"""

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

RAG_COLORS = {
    "RED":   "#dc2626",
    "AMBER": "#d97706",
    "GREEN": "#16a34a",
    "GREY":  "#6b7280",
}

RAG_BG = {
    "RED":   "#450a0a",
    "AMBER": "#451a03",
    "GREEN": "#052e16",
    "GREY":  "#111827",
}

RAG_EMOJI = {
    "RED":   "🔴",
    "AMBER": "🟡",
    "GREEN": "🟢",
    "GREY":  "⚪",
}

TREND_COLORS = {
    "↑": "#16a34a",
    "→": "#6b7280",
    "↓": "#dc2626",
}

SECTOR_ICONS = {
    "Transport":        "🚆",
    "Energy":           "⚡",
    "Urban Infra":      "🏙",
    "Water/Utilities":  "💧",
    "Digital":          "📡",
}

# ─── GATE READINESS PREDICTOR ─────────────────────────────────────────────────

GATE_FEATURES = [
    "composite_score",
    "schedule_health",
    "cost_health",
    "risk_health",
    "governance_health",
    "gate_readiness_pct",
    "days_to_gate",
    "data_confidence",
    "overdue_actions",
    "outstanding_approvals",
    "audit_findings_open",
    "spi",
    "cpi",
]

def _generate_gate_training(n: int = 1500, seed: int = 42) -> pd.DataFrame:
    """Synthetic gate pass/fail training data."""
    rng = np.random.default_rng(seed)

    rows = []
    for _ in range(n):
        composite = rng.uniform(20, 95)
        sched = composite + rng.normal(0, 10)
        cost  = composite + rng.normal(0, 12)
        risk  = composite + rng.normal(0, 8)
        gov   = composite + rng.normal(0, 15)
        grd   = rng.uniform(20, 100)
        days  = int(rng.integers(-30, 180))
        conf  = rng.uniform(0.4, 1.0)
        over  = int(rng.poisson(2))
        appr  = int(rng.poisson(1))
        audit = int(rng.poisson(1))
        spi   = rng.uniform(0.5, 1.2)
        cpi   = rng.uniform(0.6, 1.2)

        # Gate pass probability
        p_pass = (
            composite / 100 * 0.35 +
            grd / 100 * 0.30 +
            max(0, 1 - max(0, -days) / 60) * 0.15 +
            conf * 0.10 +
            max(0, 1 - over * 0.1) * 0.10
        )
        p_pass = float(np.clip(p_pass + rng.normal(0, 0.08), 0, 1))
        passed = int(rng.random() < p_pass)

        rows.append({
            "composite_score": np.clip(composite, 0, 100),
            "schedule_health": np.clip(sched, 0, 100),
            "cost_health":     np.clip(cost, 0, 100),
            "risk_health":     np.clip(risk, 0, 100),
            "governance_health": np.clip(gov, 0, 100),
            "gate_readiness_pct": grd,
            "days_to_gate":    days,
            "data_confidence": conf,
            "overdue_actions": over,
            "outstanding_approvals": appr,
            "audit_findings_open": audit,
            "spi": spi,
            "cpi": cpi,
            "gate_passed": passed,
        })
    return pd.DataFrame(rows)


class GateReadinessModel:
    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", random_state=42, verbosity=0,
        )
        self.scaler = StandardScaler()
        self._trained = False
        self.auc = None

    def train(self):
        df = _generate_gate_training()
        X = df[GATE_FEATURES].fillna(0).values
        y = df["gate_passed"].values
        Xs = self.scaler.fit_transform(X)
        cv = cross_val_score(self.model, Xs, y, cv=5, scoring="roc_auc")
        self.auc = round(cv.mean(), 3)
        self.model.fit(Xs, y)
        self._trained = True
        return self.auc

    def predict(self, gold_df: pd.DataFrame) -> pd.Series:
        if not self._trained:
            self.train()
        avail = [f for f in GATE_FEATURES if f in gold_df.columns]
        X = gold_df[avail].fillna(0).copy()
        for f in GATE_FEATURES:
            if f not in X.columns:
                X[f] = 0
        X = X[GATE_FEATURES].values
        Xs = self.scaler.transform(X)
        proba = self.model.predict_proba(Xs)[:, 1]
        return pd.Series(np.round(proba * 100, 1), index=gold_df.index)


# ─── PORTFOLIO SUMMARY STATS ─────────────────────────────────────────────────

def portfolio_summary(gold_df: pd.DataFrame) -> dict:
    rag_counts = gold_df["rag_status"].value_counts().to_dict()
    total = len(gold_df)
    total_budget = gold_df["budget"].sum() if "budget" in gold_df.columns else 0
    total_eac    = gold_df["eac"].sum()    if "eac"    in gold_df.columns else 0

    return {
        "total_projects":   total,
        "red_count":        rag_counts.get("RED", 0),
        "amber_count":      rag_counts.get("AMBER", 0),
        "green_count":      rag_counts.get("GREEN", 0),
        "grey_count":       rag_counts.get("GREY", 0),
        "avg_composite":    round(gold_df["composite_score"].mean(), 1),
        "avg_confidence":   round(gold_df["data_confidence"].mean(), 2),
        "stale_data_count": int((gold_df["data_confidence"] < 0.65).sum()),
        "gate_flag_count":  int(gold_df["gate_flag"].sum()) if "gate_flag" in gold_df.columns else 0,
        "total_budget_bn":  round(total_budget / 1e9, 2),
        "total_eac_bn":     round(total_eac    / 1e9, 2),
        "portfolio_overrun_pct": round((total_eac - total_budget) / max(1, total_budget) * 100, 1),
        "trend_down_count": int((gold_df["trend"] == "↓").sum()) if "trend" in gold_df.columns else 0,
    }


# ─── MISSING DELIVERABLES GENERATOR ─────────────────────────────────────────

DELIVERABLE_TEMPLATES = {
    "pre_construction": [
        "Outline Business Case approved",
        "Planning permission granted",
        "Land / ROW secured",
        "Environmental Impact Assessment signed off",
        "Utility survey complete",
        "Procurement strategy approved",
    ],
    "early_works": [
        "Detailed design (IFC) issued",
        "Main contractor appointed",
        "CDM Principal Designer appointed",
        "Risk register baselined",
        "Programme baseline approved",
        "Cost plan approved (±10%)",
    ],
    "construction": [
        "Monthly progress report submitted",
        "EVM baseline agreed",
        "Health & Safety file current",
        "Environmental compliance confirmed",
        "Change control log current",
        "Quality Surveillance Plan approved",
    ],
    "commissioning": [
        "Test & Commissioning plan approved",
        "O&M manuals drafted",
        "Snag list issued",
        "As-built drawings in progress",
        "Handover certificate drafted",
        "Lessons Learned register complete",
    ],
}

def get_missing_deliverables(project_row: pd.Series) -> list:
    phase = str(project_row.get("phase", "construction")).lower()
    phase_key = next(
        (k for k in DELIVERABLE_TEMPLATES if k in phase.replace(" ", "_").replace("-","_")),
        "construction"
    )
    templates = DELIVERABLE_TEMPLATES[phase_key]
    total = project_row.get("gate_deliverables_total", len(templates))
    complete = project_row.get("gate_deliverables_complete", 0)
    missing_count = max(0, int(total - complete))

    missing = []
    for i, d in enumerate(templates):
        if i >= complete:
            missing.append(d)
    return missing[:missing_count] if missing_count > 0 else []
