"""
PAC Demo Data — UK Combined Authority Programme Portfolio
18 projects across Transport, Energy, Urban Infrastructure.
Modelled on West Midlands Combined Authority / Levelling Up Fund capital programme.
Includes realistic data quality issues: stale data, missing fields, varying formats.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

PORTFOLIO = [
    # (id, name, sector, programme, contractor, ctype, budget_m, phase, complexity)
    ("P01", "Tram Extension — City Centre to Airport",        "Transport",       "LCR Connectivity",      "Bam Nuttall",        "target_cost", 340.0, "construction",     9),
    ("P02", "Levelling Up: Town Centre Regeneration — Dudley","Urban Infra",     "LUF Round 2",           "Wates Group",        "lump_sum",     28.0, "early_works",      5),
    ("P03", "A38 Motorway Junction Upgrade",                  "Transport",       "RIS2 Regional",         "Costain",            "lump_sum",     95.0, "construction",     7),
    ("P04", "Battery Energy Storage — 150MWh Grid Balancing", "Energy",          "BESS Programme",        "AECOM/Ameresco",     "design_build",118.0, "commissioning",    8),
    ("P05", "HS2 Station Enabling Works — Birmingham Curzon",  "Transport",       "HS2 Ltd",               "Laing O'Rourke",     "target_cost", 620.0, "construction",    10),
    ("P06", "Smart Motorway Removal — M6 J8-J10A",           "Transport",       "National Highways",     "Costain",            "remeasure",   145.0, "pre_construction", 6),
    ("P07", "District Heating Network — City Hospital Campus","Energy",          "WMCA Heat",             "Vital Energi",       "target_cost",  22.0, "construction",     6),
    ("P08", "Active Travel — Cycling & Walking Infrastructure","Urban Infra",     "ATF3",                  "Kier Highways",      "lump_sum",     18.0, "construction",     4),
    ("P09", "Strategic Rail Freight Interchange",             "Transport",       "Midlands Connect",      "DB Symmetry",        "lump_sum",    210.0, "pre_construction", 8),
    ("P10", "Solar Farm — 100MW with Grid Connection",        "Energy",          "Net Zero Fund",         "Orsted / Kier",      "design_build",  88.0, "construction",     7),
    ("P11", "Affordable Housing — 500 Units Phase 1",         "Urban Infra",     "Homes England",         "Keepmoat",           "fixed_price",  65.0, "construction",     5),
    ("P12", "Bus Rapid Transit — Sprint Route Expansion",     "Transport",       "WMCA Sprint",           "Colas Rail",         "remeasure",    47.0, "early_works",      6),
    ("P13", "Digital Connectivity — Full Fibre Roll-out",     "Digital",         "BDUK Project Gigabit",  "Openreach",          "lump_sum",     34.0, "construction",     5),
    ("P14", "Flood Alleviation — River Tame Scheme",          "Water/Utilities", "EA Capital",            "VBA JV",             "target_cost",  78.0, "construction",     8),
    ("P15", "Underground Utilities Upgrade — City Core",      "Urban Infra",     "WM Water & Gas",        "Amey",               "remeasure",    42.0, "construction",     7),
    ("P16", "Innovation Campus — Knowledge Quarter",          "Urban Infra",     "WMCA Innovation",       "ISG",                "design_build",  55.0, "early_works",      6),
    ("P17", "Electrification — Local Rail Line Wiring",       "Transport",       "Network Rail CP7",      "Alstom/Network Rail","target_cost", 185.0, "construction",     9),
    ("P18", "Net Zero Retrofit — 2,000 Social Homes",         "Energy",          "SHDF Wave 3",           "United Living",      "lump_sum",     48.0, "construction",     5),
]

GATES = {
    "pre_construction": "Full Business Case",
    "early_works":      "Construction Start",
    "construction":     "Practical Completion",
    "commissioning":    "Handover",
}

TOP_RISKS = {
    "Transport": [
        "CPO delay impacting land availability for construction start",
        "Statutory undertaker diversion not complete on programme",
        "Planning condition discharge delayed by local authority",
        "Labour shortage for specialist rail / tram works",
    ],
    "Energy": [
        "Grid connection date slipping due to DNO constraints",
        "Long lead equipment (transformers) delayed 16+ weeks",
        "Planning permission for battery storage facility at risk",
        "Fire safety certification for BESS facility — new regulatory requirement",
    ],
    "Urban Infra": [
        "Contaminated land discovered during enabling works",
        "Stakeholder opposition to design changes",
        "Material cost inflation eroding contingency",
        "Supply chain capacity constraints for specialist trades",
    ],
    "Water/Utilities": [
        "EA permit conditions more onerous than anticipated",
        "Third-party landowner access disputes delaying works",
        "Unforeseen ground conditions in riverbank works",
    ],
    "Digital": [
        "Wayleave negotiations with private landowners stalling",
        "Supply chain bottleneck for fibre cable at scale",
    ],
}


def generate_demo_portfolio(seed: int = 42) -> pd.DataFrame:
    """
    Generate a realistic 18-project UK infrastructure portfolio.
    Includes deliberate data quality issues for realism:
    - Some projects have stale schedule data (>14 days old)
    - Some have missing risk register updates
    - One project has no data at all (Grey RAG)
    """
    rng = np.random.default_rng(seed)
    data_date = datetime(2025, 1, 15)
    programme_start = datetime(2022, 4, 1)

    rows = []

    # Health archetypes to create realistic portfolio spread
    ARCHETYPES = [
        # (schedule_perf, cost_perf, risk_level, gov_quality, data_staleness)
        ("critical",    "overrun",   "high",   "poor",   "fresh"),   # P01 RED
        ("ok",          "ok",        "medium", "ok",     "fresh"),   # P02 GREEN
        ("slipping",    "ok",        "medium", "ok",     "stale"),   # P03 AMBER (stale)
        ("ok",          "ok",        "low",    "good",   "fresh"),   # P04 GREEN
        ("critical",    "overrun",   "high",   "poor",   "fresh"),   # P05 RED
        ("ok",          "ok",        "low",    "good",   "missing"), # P06 GREY
        ("ok",          "slipping",  "medium", "ok",     "fresh"),   # P07 AMBER
        ("good",        "ok",        "low",    "good",   "fresh"),   # P08 GREEN
        ("slipping",    "overrun",   "high",   "poor",   "stale"),   # P09 AMBER
        ("ok",          "ok",        "medium", "ok",     "fresh"),   # P10 GREEN
        ("slipping",    "ok",        "medium", "ok",     "fresh"),   # P11 AMBER
        ("ok",          "ok",        "low",    "good",   "fresh"),   # P12 GREEN
        ("good",        "ok",        "low",    "good",   "fresh"),   # P13 GREEN
        ("critical",    "overrun",   "high",   "poor",   "fresh"),   # P14 RED
        ("ok",          "ok",        "medium", "ok",     "stale"),   # P15 AMBER (stale)
        ("ok",          "ok",        "low",    "ok",     "fresh"),   # P16 GREEN
        ("slipping",    "overrun",   "high",   "poor",   "fresh"),   # P17 RED
        ("ok",          "ok",        "low",    "good",   "fresh"),   # P18 GREEN
    ]

    for i, (pid, name, sector, programme, contractor, ctype, budget_m, phase, complexity) in enumerate(PORTFOLIO):
        arch = ARCHETYPES[i] if i < len(ARCHETYPES) else ("ok","ok","medium","ok","fresh")
        sched_arch, cost_arch, risk_arch, gov_arch, data_stale = arch

        budget = budget_m * 1e6
        duration_months = int(rng.integers(18, 60))
        proj_start = programme_start + timedelta(days=int(rng.integers(0, 400)))
        planned_finish = proj_start + timedelta(days=int(duration_months * 30.5))

        # SPI by archetype
        spi_map = {"critical": rng.uniform(0.52, 0.72), "slipping": rng.uniform(0.73, 0.88),
                   "ok": rng.uniform(0.88, 1.02), "good": rng.uniform(1.0, 1.08)}
        spi = spi_map.get(sched_arch, 0.90)

        # Forecast finish
        if sched_arch == "critical":
            forecast_finish = planned_finish + timedelta(days=int(rng.integers(60, 180)))
        elif sched_arch == "slipping":
            forecast_finish = planned_finish + timedelta(days=int(rng.integers(14, 60)))
        else:
            forecast_finish = planned_finish + timedelta(days=int(rng.integers(-10, 14)))

        # Float
        float_map = {"critical": rng.integers(-10, 5), "slipping": rng.integers(2, 15),
                     "ok": rng.integers(10, 35), "good": rng.integers(25, 60)}
        total_float = int(float_map.get(sched_arch, 20))

        # CPI / cost
        cpi_map = {"overrun": rng.uniform(0.72, 0.88), "slipping": rng.uniform(0.88, 0.96),
                   "ok": rng.uniform(0.95, 1.05), "good": rng.uniform(1.0, 1.08)}
        cpi = cpi_map.get(cost_arch, 0.95)

        elapsed_months = max(1, min(duration_months, int((data_date - proj_start).days / 30.5)))
        pct_complete = min(95, max(2, (elapsed_months / duration_months) * 100 * spi * rng.uniform(0.92, 1.0)))

        acwp = budget * (elapsed_months / duration_months) * cpi * rng.uniform(0.97, 1.03)
        bcwp = acwp * cpi
        eac_overrun = {"overrun": rng.uniform(1.12, 1.35), "slipping": rng.uniform(1.05, 1.15),
                       "ok": rng.uniform(0.98, 1.07), "good": rng.uniform(0.95, 1.02)}
        eac = budget * eac_overrun.get(cost_arch, 1.08)

        # Risk
        risk_score_map = {"high": rng.uniform(6.5, 9.5), "medium": rng.uniform(4.0, 6.5),
                          "low": rng.uniform(1.5, 4.0)}
        risk_score = risk_score_map.get(risk_arch, 5.0)
        risks_mat = int(rng.poisson(2)) if risk_arch == "high" else int(rng.poisson(0.3))
        top_risk = rng.choice(TOP_RISKS.get(sector, TOP_RISKS["Transport"]))

        # Governance
        gov_map = {"poor": (rng.integers(5, 12), rng.integers(3, 7), rng.integers(2, 5)),
                   "ok":   (rng.integers(1, 4),  rng.integers(1, 3), rng.integers(0, 2)),
                   "good": (0, 0, 0)}
        overdue, approvals, audit = gov_map.get(gov_arch, (2, 1, 1))

        days_board = int(rng.integers(7, 75) if gov_arch != "good" else rng.integers(7, 25))

        # Gate
        gate_name = GATES.get(phase, "Practical Completion")
        if phase in ("construction", "early_works"):
            gate_date = planned_finish - timedelta(days=int(rng.integers(-30, 120)))
        else:
            gate_date = planned_finish + timedelta(days=int(rng.integers(0, 60)))

        days_to_gate = (gate_date - data_date).days
        gate_total = 6
        gate_complete = int(min(gate_total, max(0,
            gate_total * pct_complete / 100 * (0.7 if sched_arch in ("critical","slipping") else 0.95))))

        # Data freshness (deliberate staleness for some)
        def update_date(staleness, threshold_days):
            if staleness == "fresh":
                return data_date - timedelta(days=int(rng.integers(1, threshold_days - 2)))
            elif staleness == "stale":
                return data_date - timedelta(days=int(rng.integers(threshold_days + 2, threshold_days * 3)))
            else:  # missing
                return None

        rows.append({
            "project_id":               pid,
            "project_name":             name,
            "sector":                   sector,
            "programme":                programme,
            "contractor":               contractor,
            "contract_type":            ctype,
            "phase":                    phase,
            "budget":                   round(budget, 0),
            "budget_m":                 budget_m,
            "acwp":                     round(acwp, 0),
            "bcwp":                     round(bcwp, 0),
            "eac":                      round(eac, 0),
            "cpi":                      round(cpi, 3),
            "spi":                      round(spi, 3),
            "total_float_days":         total_float,
            "pct_complete":             round(pct_complete, 1),
            "planned_start":            proj_start,
            "planned_finish":           planned_finish,
            "forecast_finish":          forecast_finish,
            "risk_score":               round(risk_score, 1),
            "top_risk_description":     top_risk,
            "risks_materialised_30d":   risks_mat,
            "overdue_actions":          int(overdue),
            "outstanding_approvals":    int(approvals),
            "audit_findings_open":      int(audit),
            "days_since_board_review":  days_board,
            "next_gate":                gate_name,
            "next_gate_date":           gate_date,
            "gate_deliverables_total":  gate_total,
            "gate_deliverables_complete": gate_complete,
            "schedule_updated_at":      update_date(data_stale, 14),
            "cost_updated_at":          update_date(data_stale, 30),
            "risk_updated_at":          update_date(data_stale, 30),
            "governance_updated_at":    update_date(data_stale, 14),
            "source_system":            rng.choice(["Primavera P6", "MS Project", "Excel", "Oracle ERP"]),
            "contract_value":           round(budget, 0),
        })

    return pd.DataFrame(rows)


def to_excel(df: pd.DataFrame) -> bytes:
    """Export portfolio to Excel for upload testing."""
    buf = io.BytesIO()
    export = df.copy()
    # Format dates
    for c in ["planned_start","planned_finish","forecast_finish","next_gate_date",
              "schedule_updated_at","cost_updated_at","risk_updated_at","governance_updated_at"]:
        if c in export.columns:
            export[c] = pd.to_datetime(export[c]).dt.strftime("%d/%m/%Y").fillna("")
    for c in ["budget","acwp","bcwp","eac","contract_value"]:
        if c in export.columns:
            export[c] = (export[c] / 1e6).round(2)
            export.rename(columns={c: c.replace("_","_") + "_m"}, inplace=True)

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export.to_excel(writer, sheet_name="Programme Portfolio", index=False)
        meta = pd.DataFrame({
            "Field": ["Programme","Reporting Date","Currency","Projects","Total Budget"],
            "Value": ["WMCA Capital Programme","15 Jan 2025","GBP (£)",str(len(df)),
                      f"£{df['budget'].sum()/1e9:.2f}bn"],
        })
        meta.to_excel(writer, sheet_name="Programme Info", index=False)
    return buf.getvalue()
