"""
PAC — Programme Assurance Cockpit
Narrative Engine: auto-generates exception report paragraphs for Red/Amber projects.

Architecture: rule-based template engine (production default).
Saves 2–3 hours of report writing per PMO reporting cycle.
Optional: Claude API integration hook for richer prose (disabled by default).
"""

import pandas as pd
import numpy as np
from typing import Optional

# ─── RULE-BASED NARRATIVE GENERATOR ──────────────────────────────────────────
# This is the production-safe default. No API dependency, deterministic, auditable.
# The narrative follows a standard structure used in IPA/OGP exception reports.

def _format_money(val: float, currency: str = "£") -> str:
    if abs(val) >= 1e9:
        return f"{currency}{val/1e9:.2f}bn"
    elif abs(val) >= 1e6:
        return f"{currency}{val/1e6:.1f}m"
    else:
        return f"{currency}{val/1e3:.0f}k"


def _trend_phrase(trend: str, delta: float) -> str:
    if trend == "↓":
        return f"deteriorating (−{abs(delta):.1f} pts this period)"
    elif trend == "↑":
        return f"improving (+{delta:.1f} pts this period)"
    return "stable"


def _rag_phrase(rag: str) -> str:
    return {"RED": "RED — requires urgent intervention",
            "AMBER": "AMBER — under close monitoring",
            "GREEN": "GREEN — performing to programme",
            "GREY": "GREY — insufficient data to assess"}.get(rag, rag)


def generate_exception_paragraph(row: pd.Series, currency: str = "£") -> str:
    """
    Generate a board-ready exception paragraph for one project.
    Format mirrors IPA Project Assessment Review / OGP programme assurance style.
    """
    name     = str(row.get("project_name", "Project"))
    rag      = str(row.get("rag_status", "AMBER"))
    score    = float(row.get("composite_score", 50))
    conf     = float(row.get("data_confidence", 0.7))
    trend    = str(row.get("trend", "→"))
    delta    = float(row.get("trend_delta", 0))
    spi      = float(row.get("spi", 1.0))
    cpi      = float(row.get("cpi", 1.0))
    budget   = float(row.get("budget", 0))
    eac      = float(row.get("eac", 0))
    s_health = float(row.get("schedule_health", 50))
    c_health = float(row.get("cost_health", 50))
    r_health = float(row.get("risk_health", 50))
    g_health = float(row.get("governance_health", 50))
    overdue  = int(row.get("overdue_actions", 0))
    approvals= int(row.get("outstanding_approvals", 0))
    risk_desc= str(row.get("top_risk_description", ""))
    gate     = str(row.get("next_gate", ""))
    days_gate= row.get("days_to_gate", None)
    gate_rdy = row.get("gate_readiness_pct", None)
    phase    = str(row.get("phase", "construction"))
    sector   = str(row.get("sector", "Infrastructure"))
    pct_done = float(row.get("pct_complete", 0))

    lines = []

    # ── Opening line: status + score + trend ──────────────────────────────────
    conf_note = "" if conf >= 0.75 else f" [Note: data confidence {conf*100:.0f}% — last update may be stale]"
    lines.append(
        f"**{name}** is rated {_rag_phrase(rag)}, with a composite assurance score of "
        f"{score:.0f}/100 and is {_trend_phrase(trend, delta)}.{conf_note}"
    )

    # ── Schedule narrative ────────────────────────────────────────────────────
    if s_health < 50:
        if spi < 0.75:
            lines.append(
                f"Schedule performance is critically below plan (SPI {spi:.2f}), indicating "
                f"the project is delivering {(1-spi)*100:.0f}% less progress per pound spent on "
                f"planned activities. Immediate programme recovery action is required."
            )
        elif spi < 0.90:
            lines.append(
                f"Schedule performance is below plan (SPI {spi:.2f}). The project is currently "
                f"{pct_done:.0f}% complete and behind its baseline programme. "
                f"Recovery options should be presented to the PMO within 2 weeks."
            )
    elif s_health >= 75:
        lines.append(f"Schedule performance is satisfactory (SPI {spi:.2f}), with the project "
                     f"{pct_done:.0f}% complete against baseline.")

    # ── Cost narrative ────────────────────────────────────────────────────────
    if c_health < 50 and budget > 0:
        overrun_val = eac - budget
        overrun_pct = overrun_val / budget * 100
        if overrun_val > 0:
            lines.append(
                f"The Estimate at Completion of {_format_money(eac, currency)} represents a "
                f"{overrun_pct:.1f}% overrun against the approved budget of "
                f"{_format_money(budget, currency)} (CPI {cpi:.2f}). "
                f"A cost recovery plan with specific mitigations should be presented to "
                f"the Client Board at the next review."
            )
        else:
            lines.append(
                f"Cost performance is within budget (CPI {cpi:.2f}). "
                f"EAC of {_format_money(eac, currency)} is below the approved budget of "
                f"{_format_money(budget, currency)}."
            )
    elif c_health >= 70 and budget > 0:
        lines.append(
            f"Cost is tracking within budget (CPI {cpi:.2f}, EAC {_format_money(eac, currency)} "
            f"vs approved {_format_money(budget, currency)})."
        )

    # ── Risk narrative ────────────────────────────────────────────────────────
    if r_health < 50:
        mat = int(row.get("risks_materialised_30d", 0))
        if mat > 0:
            lines.append(
                f"{mat} risk{'s' if mat > 1 else ''} materialised in the last 30 days. "
                + (f"The top residual risk is: {risk_desc}." if risk_desc else "")
                + " Risk register requires immediate review and updated mitigation plans."
            )
        else:
            lines.append(
                f"The risk profile is elevated. "
                + (f"Principal concern: {risk_desc}." if risk_desc else "Risk register review overdue.")
            )

    # ── Governance narrative ──────────────────────────────────────────────────
    gov_issues = []
    if overdue > 0:
        gov_issues.append(f"{overdue} overdue action{'s' if overdue > 1 else ''}")
    if approvals > 0:
        gov_issues.append(f"{approvals} decision{'s' if approvals > 1 else ''} awaiting approval")
    audit_open = int(row.get("audit_findings_open", 0))
    if audit_open > 0:
        gov_issues.append(f"{audit_open} open audit finding{'s' if audit_open > 1 else ''}")

    if gov_issues:
        lines.append(
            f"Governance concerns: {'; '.join(gov_issues)}. "
            f"These must be resolved before the next stage gate."
        )

    # ── Gate readiness ────────────────────────────────────────────────────────
    if gate and days_gate is not None and not pd.isna(days_gate):
        days_gate = int(days_gate)
        rdy_str = f"{gate_rdy:.0f}%" if gate_rdy is not None and not pd.isna(gate_rdy) else "unknown"
        if days_gate < 0:
            lines.append(
                f"⚠ Gate **{gate}** was due {abs(days_gate)} days ago and has not been passed. "
                f"Gate readiness: {rdy_str}. Escalation to programme board required immediately."
            )
        elif days_gate < 60:
            flag = "⚠ " if (gate_rdy is not None and not pd.isna(gate_rdy) and gate_rdy < 60) else ""
            lines.append(
                f"{flag}Next gate: **{gate}** in {days_gate} days. "
                f"Gate readiness is {rdy_str}. "
                + ("Deliverable completion plan should be confirmed with project team this week." if days_gate < 30 else "")
            )

    # ── Decision required ─────────────────────────────────────────────────────
    if rag == "RED":
        lines.append(
            f"**Decision required:** {name} requires immediate board-level intervention. "
            f"The SRO should convene a recovery review within 5 working days."
        )
    elif rag == "AMBER" and (overdue > 2 or s_health < 40 or c_health < 40):
        lines.append(
            f"**Recommended action:** Programme Director to schedule a recovery review with "
            f"the project team within 2 weeks and report back to the PMO."
        )

    return " ".join(lines)


def generate_exception_report(gold_df: pd.DataFrame,
                               currency: str = "£",
                               report_date: str = None) -> dict:
    """
    Generate the full programme exception report.
    Returns dict with summary, red_projects, amber_projects, narrative_blocks.
    """
    red    = gold_df[gold_df["rag_status"] == "RED"]
    amber  = gold_df[gold_df["rag_status"] == "AMBER"]
    green  = gold_df[gold_df["rag_status"] == "GREEN"]
    grey   = gold_df[gold_df["rag_status"] == "GREY"]

    narratives = {}
    for _, row in pd.concat([red, amber]).iterrows():
        narratives[row["project_id"]] = generate_exception_paragraph(row, currency)

    # Programme summary sentence
    total_budget = gold_df["budget"].sum() if "budget" in gold_df.columns else 0
    total_eac    = gold_df["eac"].sum()    if "eac"    in gold_df.columns else 0
    overrun_pct  = (total_eac - total_budget) / max(1, total_budget) * 100

    trend_down = (gold_df["trend"] == "↓").sum() if "trend" in gold_df.columns else 0
    stale = (gold_df["data_confidence"] < 0.65).sum()

    summary = (
        f"As at {report_date or 'this reporting period'}, the programme comprises "
        f"{len(gold_df)} active projects with a total approved budget of "
        f"{_format_money(total_budget, currency)} and a current EAC of "
        f"{_format_money(total_eac, currency)} ({'+' if overrun_pct >= 0 else ''}{overrun_pct:.1f}% vs budget). "
        f"Overall programme health: {len(red)} RED, {len(amber)} AMBER, {len(green)} GREEN, {len(grey)} GREY. "
        + (f"{trend_down} project{'s' if trend_down != 1 else ''} showing deteriorating trend. " if trend_down else "")
        + (f"Note: {stale} project{'s' if stale != 1 else ''} have stale data — confidence is reduced." if stale else "")
    )

    return {
        "summary": summary,
        "red_projects":   red,
        "amber_projects": amber,
        "green_projects": green,
        "narratives":     narratives,
        "report_date":    report_date,
    }


# ─── OPTIONAL CLAUDE API HOOK ────────────────────────────────────────────────
# Uncomment and add API key to use enhanced LLM-powered narratives.
# In a live KPMG engagement this would be behind a feature flag.

def generate_narrative_with_llm(row: pd.Series, currency: str = "£") -> Optional[str]:
    """
    Optional: use Claude API to generate richer narrative.
    Falls back to rule-based if API unavailable.
    """
    try:
        import requests, json, os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        rule_based = generate_exception_paragraph(row, currency)
        prompt = f"""You are a senior programme assurance consultant writing an exception report 
paragraph for a UK government infrastructure programme board. 

Project data:
{row.to_dict()}

A rule-based system produced this draft:
{rule_based}

Rewrite this in clear, concise board-level language (3–4 sentences maximum). 
Be specific about numbers. End with one clear recommended action.
Do not use bullet points. Write in third person."""

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
    except Exception:
        pass
    return None
