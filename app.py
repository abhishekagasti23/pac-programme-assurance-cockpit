"""
PAC — Programme Assurance Cockpit
Streamlit Application — Project 3 of 3 for KPMG Associate Consultant Demo
Sector: All (Transport, Energy, Urban Infra) | UK Government / Combined Authority
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from data_fusion import run_medallion, SILVER_SCHEMA
from health_engine import (GateReadinessModel, portfolio_summary,
                            RAG_COLORS, RAG_BG, RAG_EMOJI, TREND_COLORS,
                            SECTOR_ICONS, get_missing_deliverables)
from narrative_engine import generate_exception_report, generate_exception_paragraph
from demo_data import generate_demo_portfolio, to_excel

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PAC — Programme Assurance Cockpit",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS — light editorial institutional aesthetic ────────────────────────────
# Dark theme — consistent with Projects 1 & 2
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #0d1117;
    color: #e6edf3;
}
.stApp > header { display: none; }
.stApp { background: #0d1117; }

/* Header */
.pac-header {
    background: #161b22;
    border-bottom: 3px solid #b8960c;
    padding: 1.2rem 2rem 1rem;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: flex-end; gap: 2rem;
}
.pac-logo {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem; font-weight: 700;
    color: #f5f0e8; letter-spacing: 0.02em; line-height: 1;
}
.pac-subtitle {
    font-size: 0.72rem; color: #8b949e;
    letter-spacing: 0.12em; text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}
.pac-date {
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem; color: #8b949e;
    text-align: right; line-height: 1.6;
}

/* KPI strip */
.kpi-strip {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 0.6rem; margin-bottom: 1.5rem;
}
.kpi-card {
    background: #161b22; border: 1px solid #30363d;
    border-top: 3px solid #b8960c;
    border-radius: 4px; padding: 0.75rem 0.9rem;
}
.kpi-card.red-top   { border-top-color: #dc2626; }
.kpi-card.amber-top { border-top-color: #d97706; }
.kpi-card.green-top { border-top-color: #16a34a; }
.kpi-card.grey-top  { border-top-color: #6b7280; }
.kpi-card.blue-top  { border-top-color: #2563eb; }
.kpi-label { font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:#8b949e; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.3rem; }
.kpi-value { font-family:'Playfair Display',serif; font-size:1.7rem; font-weight:600; color:#f0f6fc; line-height:1; }
.kpi-delta { font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:#8b949e; margin-top:0.2rem; }

/* Section label */
.section-label {
    font-family:'JetBrains Mono',monospace; font-size:0.62rem;
    letter-spacing:0.14em; text-transform:uppercase; color:#b8960c;
    border-bottom:1px solid #30363d; padding-bottom:0.35rem; margin:1.2rem 0 0.8rem;
}

/* RAG badge */
.rag-badge {
    display:inline-flex; align-items:center; gap:5px;
    padding:3px 10px; border-radius:3px; font-size:0.72rem;
    font-family:'JetBrains Mono',monospace; font-weight:500;
    border:1px solid;
}

/* Project card */
.proj-card {
    background:#161b22; border:1px solid #30363d; border-radius:6px;
    padding:1rem 1.1rem; margin-bottom:0.55rem; position:relative;
    transition: border-color 0.15s;
}
.proj-card:hover { border-color: #b8960c; }
.proj-card::before {
    content:''; position:absolute; left:0; top:0; bottom:0;
    width:4px; border-radius:6px 0 0 6px;
}
.proj-card.RED::before   { background:#dc2626; }
.proj-card.AMBER::before { background:#d97706; }
.proj-card.GREEN::before { background:#16a34a; }
.proj-card.GREY::before  { background:#6b7280; }
.proj-name { font-family:'Playfair Display',serif; font-size:0.95rem; font-weight:600; color:#f0f6fc; margin-bottom:0.2rem; }
.proj-meta { font-family:'JetBrains Mono',monospace; font-size:0.62rem; color:#8b949e; }
.proj-score { font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:500; }
.score-bar-wrap { height:4px; background:#21262d; border-radius:2px; margin:4px 0 2px; }
.score-bar { height:4px; border-radius:2px; }

/* Stale badge */
.stale-badge { display:inline-block; background:#2d2a00; color:#fde047; border:1px solid #854d0e; padding:1px 7px; border-radius:3px; font-size:0.62rem; font-family:'JetBrains Mono',monospace; }
.missing-badge { display:inline-block; background:#2d0000; color:#fca5a5; border:1px solid #991b1b; padding:1px 7px; border-radius:3px; font-size:0.62rem; font-family:'JetBrains Mono',monospace; }

/* Exception report */
.exception-block {
    background:#161b22; border:1px solid #30363d; border-left:4px solid #dc2626;
    border-radius:5px; padding:1rem 1.2rem; margin-bottom:0.8rem;
}
.exception-block.amber { border-left-color:#d97706; }
.exception-heading { font-family:'Playfair Display',serif; font-size:1rem; font-weight:600; margin-bottom:0.5rem; color:#f0f6fc; }
.exception-text { font-size:0.88rem; line-height:1.75; color:#c9d1d9; }

/* Gate card */
.gate-card {
    background:#161b22; border:1px solid #30363d; border-radius:5px;
    padding:0.8rem 1rem; margin-bottom:0.5rem;
}
.gate-card.flag { border-color:#dc2626; background:#1a0000; }

/* Medallion layers */
.medallion-layer {
    background:#161b22; border:1px solid #30363d; border-radius:6px;
    padding:0.8rem 1rem; margin-bottom:0.5rem;
}
.layer-label { font-family:'JetBrains Mono',monospace; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.1em; font-weight:500; }

/* Sidebar */
section[data-testid="stSidebar"] { background:#161b22; }
section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
section[data-testid="stSidebar"] .section-label { color:#b8960c !important; border-bottom-color:#30363d !important; }

/* Streamlit native elements dark overrides */
.stDataFrame { background:#161b22; }
div[data-testid="stMetricValue"] { color:#f0f6fc !important; }
div[data-testid="stMetricLabel"] { color:#8b949e !important; }
div[data-testid="stMetricDelta"] svg { display:none; }
.stTabs [data-baseweb="tab"] { color:#8b949e; }
.stTabs [aria-selected="true"] { color:#f0f6fc !important; border-bottom-color:#b8960c !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pac-header">
  <div>
    <div class="pac-logo">🏛 Programme Assurance Cockpit</div>
    <div class="pac-subtitle" style="margin-top:0.3rem;">Integrated Intelligence · All Sectors · Multi-Source Fusion</div>
  </div>
  <div class="pac-date">WMCA Capital Programme<br>Reporting Period: 15 January 2025</div>
</div>
""", unsafe_allow_html=True)

# ─── MODELS ───────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initialising assurance engine...")
def load_gate_model():
    gm = GateReadinessModel()
    gm.train()
    return gm

gate_model = load_gate_model()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label" style="color:#b8960c;border-color:#c9d1d9;">DATA SOURCE</div>', unsafe_allow_html=True)
    source = st.radio("Source", ["🔬 Demo: WMCA Portfolio (18 projects)",
                                  "📁 Upload portfolio Excel"],
                      label_visibility="collapsed")

    uploaded = None
    if "Upload" in source:
        uploaded = st.file_uploader("Upload Excel", type=["xlsx","xls","csv"])

    st.markdown('<div class="section-label" style="color:#b8960c;border-color:#c9d1d9;">FILTERS</div>', unsafe_allow_html=True)
    sectors_all = ["Transport","Energy","Urban Infra","Water/Utilities","Digital"]
    show_sectors = st.multiselect("Sectors", sectors_all, default=sectors_all)
    show_rag = st.multiselect("RAG status", ["RED","AMBER","GREEN","GREY"],
                               default=["RED","AMBER","GREEN","GREY"])
    min_budget = st.slider("Min budget (£m)", 0, 200, 0, step=10)

    st.markdown('<div class="section-label" style="color:#b8960c;border-color:#c9d1d9;">ARCHITECTURE</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.68rem; color:#7a7060; line-height:1.8; font-family:JetBrains Mono,monospace;">
    🥉 Bronze: raw ingestion<br>
    🥈 Silver: standardised schema<br>
    🥇 Gold: computed metrics<br>
    <br>
    Weights:<br>
    Schedule · 30%<br>
    Cost · 30%<br>
    Risk · 25%<br>
    Governance · 15%
    </div>
    """, unsafe_allow_html=True)

    run_btn = st.button("▶ RUN ASSURANCE", type="primary", use_container_width=True)

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading portfolio data...")
def get_demo():
    return generate_demo_portfolio()

if "gold" not in st.session_state or run_btn:
    with st.spinner("Running Medallion pipeline..."):
        if "Upload" in source and uploaded:
            try:
                raw = pd.read_excel(uploaded, sheet_name=0)
            except Exception as e:
                st.error(f"Upload error: {e}"); st.stop()
        else:
            raw = get_demo()

        dd = datetime(2025, 1, 15)
        _, silver, gold = run_medallion(raw, data_date=dd)
        gold["gate_pass_probability"] = gate_model.predict(gold)
        st.session_state.gold = gold
        st.session_state.silver = silver
        st.session_state.raw = raw

gold   = st.session_state.gold.copy()
silver = st.session_state.silver
raw    = st.session_state.raw

# Apply filters
mask = (
    gold["sector"].isin(show_sectors) &
    gold["rag_status"].isin(show_rag) &
    (gold["budget"] >= min_budget * 1e6)
)
gold_f = gold[mask].copy()

# ─── KPI STRIP ────────────────────────────────────────────────────────────────
ps = portfolio_summary(gold_f)
tb = ps["total_budget_bn"]
te = ps["total_eac_bn"]
ov = ps["portfolio_overrun_pct"]
stale = ps["stale_data_count"]

st.markdown(f"""
<div class="kpi-strip">
  <div class="kpi-card">
    <div class="kpi-label">Budget</div>
    <div class="kpi-value">£{tb:.2f}bn</div>
    <div class="kpi-delta">{ps['total_projects']} active projects</div>
  </div>
  <div class="kpi-card {'red-top' if ov>15 else 'amber-top' if ov>5 else 'green-top'}">
    <div class="kpi-label">EAC</div>
    <div class="kpi-value">£{te:.2f}bn</div>
    <div class="kpi-delta">+{ov:.1f}% vs budget</div>
  </div>
  <div class="kpi-card red-top">
    <div class="kpi-label">RED</div>
    <div class="kpi-value">{ps['red_count']}</div>
    <div class="kpi-delta">urgent action required</div>
  </div>
  <div class="kpi-card amber-top">
    <div class="kpi-label">AMBER</div>
    <div class="kpi-value">{ps['amber_count']}</div>
    <div class="kpi-delta">under monitoring</div>
  </div>
  <div class="kpi-card green-top">
    <div class="kpi-label">GREEN</div>
    <div class="kpi-value">{ps['green_count']}</div>
    <div class="kpi-delta">on track</div>
  </div>
  <div class="kpi-card {'red-top' if ps['trend_down_count']>3 else 'amber-top'}">
    <div class="kpi-label">Deteriorating ↓</div>
    <div class="kpi-value">{ps['trend_down_count']}</div>
    <div class="kpi-delta">projects this period</div>
  </div>
  <div class="kpi-card {'amber-top' if stale>2 else 'grey-top'}">
    <div class="kpi-label">Stale Data</div>
    <div class="kpi-value">{stale}</div>
    <div class="kpi-delta">projects, confidence reduced</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺 Programme Cockpit",
    "📋 Exception Report",
    "🚪 Gate Readiness",
    "📊 Health Analytics",
    "🥇 Data Pipeline",
    "📤 Export",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PROGRAMME COCKPIT — the board view
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_list, col_detail = st.columns([1, 1])

    with col_list:
        st.markdown('<div class="section-label">PROJECT STATUS — ALL PROJECTS</div>', unsafe_allow_html=True)

        # Sort: RED first, then AMBER, then GREEN
        rag_order = {"RED": 0, "AMBER": 1, "GREEN": 2, "GREY": 3}
        gold_sorted = gold_f.copy()
        gold_sorted["_rag_order"] = gold_sorted["rag_status"].map(rag_order)
        gold_sorted = gold_sorted.sort_values(["_rag_order", "composite_score"]).reset_index(drop=True)

        # Project card list
        selected_proj = st.session_state.get("selected_proj", gold_sorted.iloc[0]["project_id"])

        for _, row in gold_sorted.iterrows():
            rag    = row["rag_status"]
            score  = row["composite_score"]
            trend  = row["trend"]
            conf   = row["data_confidence"]
            sector = row.get("sector", "")
            icon   = SECTOR_ICONS.get(sector, "🏗")
            budget_m = row.get("budget", 0) / 1e6
            color  = RAG_COLORS.get(rag, "#6b7280")
            pct    = min(100, max(0, score))

            stale_tags = ""
            for src in ["schedule","cost","risk","governance"]:
                fc = f"{src}_freshness"
                if fc in row.index:
                    if row[fc] == "stale":
                        stale_tags += f'<span class="stale-badge">{src} stale</span> '
                    elif row[fc] == "missing":
                        stale_tags += f'<span class="missing-badge">{src} missing</span> '

            is_sel = (row["project_id"] == selected_proj)
            border = "border:2px solid #b8960c;" if is_sel else ""

            st.markdown(f"""
            <div class="proj-card {rag}" style="{border}">
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1; min-width:0; padding-right:8px;">
                  <div class="proj-name">{icon} {row['project_name']}</div>
                  <div class="proj-meta">{row.get('programme','—')} · £{budget_m:.0f}m · {row.get('phase','').replace('_',' ').title()}</div>
                  <div style="margin-top:4px;">{stale_tags}</div>
                </div>
                <div style="text-align:right; flex-shrink:0;">
                  <div class="proj-score" style="color:{color};">{RAG_EMOJI[rag]} {rag}</div>
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#9a9080; margin-top:2px;">
                    {score:.0f}/100 <span style="color:{TREND_COLORS.get(trend,'#9a9080')}">{trend}</span>
                    &nbsp;·&nbsp; conf {conf*100:.0f}%
                  </div>
                </div>
              </div>
              <div class="score-bar-wrap">
                <div class="score-bar" style="width:{pct}%; background:{color};"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Open {row['project_id']}", key=f"btn_{row['project_id']}",
                         use_container_width=True, type="secondary"):
                st.session_state.selected_proj = row["project_id"]
                st.rerun()

    with col_detail:
        st.markdown('<div class="section-label">PROJECT DETAIL</div>', unsafe_allow_html=True)
        sel_id = st.session_state.get("selected_proj",
                  gold_sorted.iloc[0]["project_id"] if len(gold_sorted) > 0 else None)

        if sel_id and sel_id in gold_f["project_id"].values:
            row = gold_f[gold_f["project_id"] == sel_id].iloc[0]
        elif len(gold_sorted) > 0:
            row = gold_sorted.iloc[0]
        else:
            st.info("Select a project to view detail.")
            st.stop()

        rag = row["rag_status"]
        color = RAG_COLORS[rag]

        # Score breakdown radar
        dims = ["Schedule", "Cost", "Risk", "Governance"]
        scores = [row["schedule_health"], row["cost_health"], row["risk_health"], row["governance_health"]]
        weights = [30, 30, 25, 15]

        def _hex_to_rgba(hex_color, alpha=0.2):
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        fig_radar = go.Figure(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=dims + [dims[0]],
            fill="toself",
            fillcolor=_hex_to_rgba(color),
            line=dict(color=color, width=2),
            hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>",
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9), gridcolor="#30363d"),
                angularaxis=dict(tickfont=dict(size=11, family="JetBrains Mono")),
                bgcolor="#161b22",
            ),
            paper_bgcolor="#0d1117", height=220,
            margin=dict(l=30, r=30, t=20, b=20),
            showlegend=False,
            font_family="IBM Plex Sans",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Metric table
        budget_m = row["budget"] / 1e6
        eac_m    = row["eac"] / 1e6
        overrun  = (eac_m - budget_m) / budget_m * 100 if budget_m > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Composite", f"{row['composite_score']:.0f}/100",
                  delta=f"conf {row['data_confidence']*100:.0f}%")
        c2.metric("SPI", f"{row['spi']:.2f}")
        c3.metric("CPI", f"{row['cpi']:.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Budget", f"£{budget_m:.1f}m")
        c5.metric("EAC", f"£{eac_m:.1f}m", delta=f"{overrun:+.1f}%",
                  delta_color="inverse")
        c6.metric("Float", f"{row['total_float_days']:.0f}d")

        # Health sub-scores as progress bars
        st.markdown('<div class="section-label">HEALTH DIMENSION BREAKDOWN</div>', unsafe_allow_html=True)
        for dim, score, weight in zip(dims, scores, weights):
            bar_color = "#16a34a" if score >= 70 else "#d97706" if score >= 45 else "#dc2626"
            st.markdown(f"""
            <div style="margin-bottom:8px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#6b7280;">{dim} ({weight}%)</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#f0f6fc; font-weight:500;">{score:.0f}</span>
              </div>
              <div style="background:#21262d; height:6px; border-radius:3px;">
                <div style="width:{score}%; background:{bar_color}; height:6px; border-radius:3px;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Data freshness indicators
        st.markdown('<div class="section-label">DATA FRESHNESS</div>', unsafe_allow_html=True)
        freshness_icons = {"fresh": ("🟢", "#052e16"), "stale": ("🟡", "#451a03"), "missing": ("🔴", "#450a0a")}
        row_d = {}
        for src in ["schedule","cost","risk","governance"]:
            fc = f"{src}_freshness"
            row_d[src] = row[fc] if fc in row.index else "missing"

        cols = st.columns(4)
        for i, (src, status) in enumerate(row_d.items()):
            icon, bg = freshness_icons.get(status, ("⚪","#111"))
            cols[i].markdown(f"""
            <div style="background:{bg}; border-radius:5px; padding:6px 8px; text-align:center;">
              <div style="font-size:1rem;">{icon}</div>
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:#c0b8a8; margin-top:2px;">{src.upper()}</div>
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:#a09888;">{status}</div>
            </div>
            """, unsafe_allow_html=True)

        # Key risk
        if row.get("top_risk_description"):
            st.markdown('<div class="section-label">TOP RISK</div>', unsafe_allow_html=True)
            st.warning(f"⚠ {row['top_risk_description']}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: EXCEPTION REPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">PROGRAMME EXCEPTION REPORT — 15 JANUARY 2025</div>', unsafe_allow_html=True)

    report = generate_exception_report(gold_f, currency="£", report_date="15 January 2025")

    # Programme summary box
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #e5e0d5; border-left:4px solid #b8960c;
                border-radius:5px; padding:1rem 1.2rem; margin-bottom:1.2rem; font-size:0.88rem; line-height:1.75;">
      <strong>Programme Summary:</strong> {report['summary']}
    </div>
    """, unsafe_allow_html=True)

    # RED projects
    if len(report["red_projects"]) > 0:
        st.markdown('<div class="section-label">🔴 RED — REQUIRES URGENT INTERVENTION</div>', unsafe_allow_html=True)
        for _, row in report["red_projects"].iterrows():
            narrative = report["narratives"].get(row["project_id"], "")
            budget_m = row["budget"] / 1e6
            st.markdown(f"""
            <div class="exception-block">
              <div class="exception-heading">
                {SECTOR_ICONS.get(row.get('sector',''),'🏗')} {row['project_name']}
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#9a9080; font-weight:400;">
                  &nbsp;·&nbsp; £{budget_m:.0f}m &nbsp;·&nbsp; Score {row['composite_score']:.0f}/100 &nbsp;·&nbsp; {row['trend']}
                </span>
              </div>
              <div class="exception-text">{narrative}</div>
            </div>
            """, unsafe_allow_html=True)

    # AMBER projects
    if len(report["amber_projects"]) > 0:
        st.markdown('<div class="section-label">🟡 AMBER — UNDER CLOSE MONITORING</div>', unsafe_allow_html=True)
        for _, row in report["amber_projects"].iterrows():
            narrative = report["narratives"].get(row["project_id"], "")
            budget_m = row["budget"] / 1e6
            st.markdown(f"""
            <div class="exception-block amber">
              <div class="exception-heading">
                {SECTOR_ICONS.get(row.get('sector',''),'🏗')} {row['project_name']}
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#9a9080; font-weight:400;">
                  &nbsp;·&nbsp; £{budget_m:.0f}m &nbsp;·&nbsp; Score {row['composite_score']:.0f}/100 &nbsp;·&nbsp; {row['trend']}
                </span>
              </div>
              <div class="exception-text">{narrative}</div>
            </div>
            """, unsafe_allow_html=True)

    # Download report as Word-ready text
    report_text = f"PROGRAMME EXCEPTION REPORT\n{report['report_date']}\n\n{report['summary']}\n\n"
    for pid, narr in report["narratives"].items():
        pname = gold_f[gold_f["project_id"]==pid]["project_name"].values
        pname = pname[0] if len(pname) > 0 else pid
        report_text += f"{pname}\n{'─'*60}\n{narr}\n\n"

    st.download_button(
        "⬇ Download Exception Report (.txt)",
        data=report_text.encode("utf-8"),
        file_name=f"PAC_Exception_Report_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: GATE READINESS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">STAGE GATE READINESS TRACKER</div>', unsafe_allow_html=True)
    st.caption(f"Gate Readiness Model: XGBoost classifier · AUC {gate_model.auc:.3f}")

    gate_df = gold_f[gold_f["next_gate"].str.len() > 0].copy()
    gate_df = gate_df.sort_values("days_to_gate").dropna(subset=["days_to_gate"])

    col_g1, col_g2 = st.columns([3, 2])

    with col_g1:
        for _, row in gate_df.iterrows():
            days = int(row.get("days_to_gate", 999))
            rdy_pct = row.get("gate_readiness_pct", 0) or 0
            gate_pass = row.get("gate_pass_probability", 50) or 50
            flag = bool(row.get("gate_flag", False))
            card_class = "gate-card flag" if flag else "gate-card"
            rag = row["rag_status"]
            bar_color = "#16a34a" if rdy_pct >= 80 else "#d97706" if rdy_pct >= 50 else "#dc2626"

            overdue_str = f"⚠ Gate overdue by {abs(days)}d" if days < 0 else f"{days}d to gate"

            st.markdown(f"""
            <div class="{card_class}">
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                  <div style="font-weight:600; font-size:0.9rem; color:#f0f6fc; margin-bottom:2px;">
                    {SECTOR_ICONS.get(row.get('sector',''),'🏗')} {row['project_name'][:45]}
                  </div>
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:#9a9080;">
                    Gate: {row['next_gate']} &nbsp;·&nbsp; {overdue_str}
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; font-weight:500; color:{RAG_COLORS[rag]};">P(pass) {gate_pass:.0f}%</div>
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:#9a9080;">ready {rdy_pct:.0f}%</div>
                </div>
              </div>
              <div style="background:#21262d; height:5px; border-radius:3px; margin-top:6px;">
                <div style="width:{min(100,rdy_pct)}%; background:{bar_color}; height:5px; border-radius:3px;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with col_g2:
        st.markdown('<div class="section-label">GATE PROBABILITY CHART</div>', unsafe_allow_html=True)
        fig_gate = go.Figure(go.Bar(
            x=gate_df["gate_pass_probability"],
            y=gate_df["project_name"].str[:28],
            orientation="h",
            marker_color=gate_df["gate_pass_probability"].apply(
                lambda v: "#16a34a" if v >= 75 else "#d97706" if v >= 50 else "#dc2626"
            ),
            text=gate_df["gate_pass_probability"].apply(lambda v: f"{v:.0f}%"),
            textposition="outside",
        ))
        fig_gate.add_vline(x=70, line_dash="dot", line_color="#6b7280",
                           annotation_text="70% threshold")
        fig_gate.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            height=400, margin=dict(l=10, r=60, t=10, b=10),
            xaxis_title="Gate Pass Probability %",
            font_family="JetBrains Mono", font_size=10,
        )
        st.plotly_chart(fig_gate, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: HEALTH ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">COMPOSITE SCORE BY PROJECT</div>', unsafe_allow_html=True)
        sorted_g = gold_f.sort_values("composite_score")
        fig_scores = go.Figure(go.Bar(
            x=sorted_g["composite_score"],
            y=sorted_g["project_name"].str[:30],
            orientation="h",
            marker_color=sorted_g["rag_status"].map(RAG_COLORS),
            text=sorted_g["composite_score"].apply(lambda v: f"{v:.0f}"),
            textposition="outside",
            customdata=sorted_g[["rag_status","data_confidence"]].values,
            hovertemplate="<b>%{y}</b><br>Score: %{x:.0f}/100<br>RAG: %{customdata[0]}<br>Confidence: %{customdata[1]:.0%}<extra></extra>",
        ))
        fig_scores.add_vline(x=70, line_dash="dot", line_color="#16a34a", annotation_text="Green threshold")
        fig_scores.add_vline(x=45, line_dash="dot", line_color="#dc2626", annotation_text="Red threshold")
        fig_scores.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22", height=420,
            margin=dict(l=10, r=60, t=10, b=10), xaxis_range=[0, 110],
            font_family="JetBrains Mono", font_size=9,
        )
        st.plotly_chart(fig_scores, use_container_width=True)

    with col2:
        st.markdown('<div class="section-label">HEALTH DIMENSION HEATMAP</div>', unsafe_allow_html=True)

        hm_data = gold_f[["project_name","schedule_health","cost_health","risk_health","governance_health"]].copy()
        hm_data["project_name"] = hm_data["project_name"].str[:28]
        hm_data = hm_data.set_index("project_name")

        fig_hm = go.Figure(go.Heatmap(
            z=hm_data.values,
            x=["Schedule", "Cost", "Risk", "Governance"],
            y=hm_data.index,
            colorscale=[[0,"#dc2626"],[0.45,"#d97706"],[0.7,"#fde68a"],[1,"#16a34a"]],
            zmin=0, zmax=100,
            text=hm_data.values.round(0).astype(int),
            texttemplate="%{text}",
            textfont=dict(size=9, family="JetBrains Mono"),
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.0f}/100<extra></extra>",
        ))
        fig_hm.update_layout(
            paper_bgcolor="#0d1117", height=420,
            margin=dict(l=10, r=30, t=10, b=10),
            font_family="JetBrains Mono", font_size=9,
            xaxis=dict(tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<div class="section-label">HEALTH BY SECTOR</div>', unsafe_allow_html=True)
        sector_agg = gold_f.groupby("sector")["composite_score"].agg(["mean","count"]).reset_index()
        sector_agg.columns = ["sector","avg_score","count"]
        sector_agg["color"] = sector_agg["avg_score"].apply(
            lambda v: "#16a34a" if v >= 70 else "#d97706" if v >= 45 else "#dc2626"
        )
        fig_sector = go.Figure(go.Bar(
            x=sector_agg["sector"],
            y=sector_agg["avg_score"],
            marker_color=sector_agg["color"],
            text=sector_agg["avg_score"].apply(lambda v: f"{v:.0f}"),
            textposition="outside",
        ))
        fig_sector.add_hline(y=70, line_dash="dot", line_color="#16a34a")
        fig_sector.add_hline(y=45, line_dash="dot", line_color="#dc2626")
        fig_sector.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22", height=260,
            yaxis_range=[0, 110], margin=dict(l=10, r=10, t=10, b=10),
            font_family="JetBrains Mono", font_size=10,
        )
        st.plotly_chart(fig_sector, use_container_width=True)

    with c4:
        st.markdown('<div class="section-label">DATA CONFIDENCE vs COMPOSITE SCORE</div>', unsafe_allow_html=True)
        fig_conf = go.Figure(go.Scatter(
            x=gold_f["data_confidence"] * 100,
            y=gold_f["composite_score"],
            mode="markers+text",
            marker=dict(
                size=14, color=gold_f["rag_status"].map(RAG_COLORS),
                line=dict(width=1, color="#e5e0d5"),
            ),
            text=gold_f["project_id"],
            textposition="top center",
            textfont=dict(size=8, family="JetBrains Mono"),
            hovertext=gold_f["project_name"],
            hoverinfo="text",
        ))
        fig_conf.add_hline(y=70, line_dash="dot", line_color="#16a34a", line_width=0.8)
        fig_conf.add_hline(y=45, line_dash="dot", line_color="#dc2626", line_width=0.8)
        fig_conf.add_vline(x=65, line_dash="dot", line_color="#6b7280", line_width=0.8,
                           annotation_text="Confidence threshold")
        fig_conf.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22", height=260,
            xaxis_title="Data Confidence %", yaxis_title="Composite Score",
            margin=dict(l=10, r=10, t=10, b=40),
            font_family="JetBrains Mono", font_size=9,
        )
        st.plotly_chart(fig_conf, use_container_width=True)
        st.caption("Points in the lower-right quadrant (high confidence, low score) = genuine underperformance. Lower-left = uncertain — needs data update before action.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: DATA PIPELINE (Medallion Architecture)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-label">MEDALLION ARCHITECTURE — BRONZE → SILVER → GOLD</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="medallion-layer">
          <div class="layer-label" style="color:#cd7f32;">🥉 BRONZE LAYER — Raw Ingestion</div>
          <p style="font-size:0.8rem; margin-top:0.6rem; color:#c9d1d9; line-height:1.7;">
          Receives raw data exactly as provided. Never transforms.
          Stamps every record with: source system, ingestion timestamp, row count.
          Supports Primavera P6 XER, MS Project XML, Excel, Oracle ERP exports, CSV.
          </p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Sources accepted", "P6 · MSP · Excel · ERP · CSV")
        st.metric("Records ingested", f"{len(raw)}")

    with c2:
        st.markdown("""
        <div class="medallion-layer">
          <div class="layer-label" style="color:#a8a9ad;">🥈 SILVER LAYER — Standardised</div>
          <p style="font-size:0.8rem; margin-top:0.6rem; color:#c9d1d9; line-height:1.7;">
          Maps any input to 30-field standard schema. Enforces types.
          Derives CPI/SPI if not supplied. Adds data freshness flags per source.
          Every field traceable to its source.
          </p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Schema fields", f"{len(SILVER_SCHEMA)}")
        st.metric("Quality flags", "4 sources × 3 states")

    with c3:
        st.markdown("""
        <div class="medallion-layer">
          <div class="layer-label" style="color:#b8960c;">🥇 GOLD LAYER — Computed Metrics</div>
          <p style="font-size:0.8rem; margin-top:0.6rem; color:#c9d1d9; line-height:1.7;">
          Computes: schedule health (SPI+float+SV), cost health (CPI+VAC),
          risk health, governance health. Composite score (weighted).
          Confidence-adjusted RAG. Trend direction. Gate readiness.
          </p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Derived metrics", "12 per project")
        st.metric("Weighting", "30/30/25/15")

    st.markdown('<div class="section-label">SILVER LAYER SAMPLE — DATA QUALITY VIEW</div>', unsafe_allow_html=True)

    dq_cols = ["project_id","project_name","schedule_freshness","cost_freshness",
               "risk_freshness","governance_freshness","spi","cpi","data_confidence"]
    avail = [c for c in dq_cols if c in silver.columns]
    dq_tbl = silver[avail].copy()

    def colour_freshness(val):
        if val == "fresh": return "background:#052e16; color:#86efac"
        elif val == "stale": return "background:#451a03; color:#fde68a"
        elif val == "missing": return "background:#450a0a; color:#fca5a5"
        return ""

    styled_dq = dq_tbl.style.applymap(
        colour_freshness,
        subset=[c for c in ["schedule_freshness","cost_freshness","risk_freshness","governance_freshness"] if c in dq_tbl.columns]
    ).format({c: "{:.2f}" for c in ["spi","cpi","data_confidence"] if c in dq_tbl.columns})
    st.dataframe(styled_dq, use_container_width=True)

    st.markdown('<div class="section-label">GOLD LAYER SAMPLE — COMPUTED HEALTH SCORES</div>', unsafe_allow_html=True)
    gold_display = gold_f[["project_id","project_name","schedule_health","cost_health",
                            "risk_health","governance_health","composite_score",
                            "data_confidence","rag_status","trend"]].copy()
    gold_display = gold_display.round(1)
    st.dataframe(gold_display, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-label">EXPORT PROGRAMME ASSURANCE PACK</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        # Full Excel export
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            gold_f.to_excel(w, sheet_name="Gold — Health Scores", index=False)
            silver.to_excel(w, sheet_name="Silver — Standardised", index=False)
        st.download_button(
            "⬇ Full Data Pack (Excel)",
            data=buf.getvalue(),
            file_name=f"PAC_DataPack_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with c2:
        # RAG register CSV
        rag_csv = gold_f[["project_id","project_name","sector","rag_status","composite_score",
                           "trend","data_confidence","schedule_health","cost_health",
                           "risk_health","governance_health"]].to_csv(index=False).encode()
        st.download_button("⬇ RAG Register (CSV)", data=rag_csv,
                           file_name=f"PAC_RAG_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv", use_container_width=True)

    with c3:
        # Exception report text
        report2 = generate_exception_report(gold_f, currency="£", report_date="15 January 2025")
        txt = f"PROGRAMME EXCEPTION REPORT\n{report2['report_date']}\n\n{report2['summary']}\n\n"
        for pid, narr in report2["narratives"].items():
            pname = gold_f[gold_f["project_id"]==pid]["project_name"].values
            pname = pname[0] if len(pname) > 0 else pid
            txt += f"{pname}\n{'─'*60}\n{narr}\n\n"
        st.download_button("⬇ Exception Report (.txt)", data=txt.encode(),
                           file_name=f"PAC_ExceptionReport_{datetime.now().strftime('%Y%m%d')}.txt",
                           mime="text/plain", use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-label">INTERVIEW POSITIONING NOTE</div>', unsafe_allow_html=True)
    st.info("""
**Why this project matters for KPMG:**

This is the most senior-level of the three projects — it's what a Programme Director and client Board actually look at. 
Project 1 answers "will it be late?" Project 2 answers "why is it over budget?" 
Project 3 answers "what is the overall health of our programme, and what decisions do we need to make today?"

**Technical differentiators:**
- Medallion architecture (Bronze→Silver→Gold): industry-standard data platform pattern, not a one-off script — it shows you understand scalable data engineering
- Confidence-weighted RAG: a Green project with 3-week-old data is not the same as a Green project updated yesterday — no existing tool does this cleanly
- Automated exception narratives: saves 2–3 hours of PMO report-writing per cycle, produces board-quality text with specific numbers and recommended actions
- Gate readiness predictor: XGBoost model that surfaces which projects are at risk of failing an imminent gate, with missing deliverable list

**Consulting value delivered:**
- A quarterly programme assurance review that currently takes 15 analyst-days can be generated in under 1 hour
- The board gets a decision-ready exception report, not a 40-tab Excel file
- Data staleness is surfaced — the PMO cannot hide a RED project by simply not updating the data

*"This is what programme assurance actually looks like in practice: not a dashboard that shows what happened, but a decision system that tells the SRO what to do next."*
    """)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:3rem; padding-top:1rem; border-top:1px solid #30363d;
     display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace;
     font-size:0.6rem; color:#9a9080;">
  <span style="color:#8b949e;">PAC v1.0 · Medallion Architecture · XGBoost · Streamlit · Source Serif 4</span>
  <span>Project 3 of 3 · KPMG Infrastructure Advisory · UK Capital Programmes</span>
</div>
""", unsafe_allow_html=True)