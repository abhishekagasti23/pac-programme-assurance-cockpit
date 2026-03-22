# PAC — Programme Assurance Cockpit
## Project 3 of 3 | KPMG Infrastructure Advisory Portfolio

---

### What This Is
A senior-level programme assurance intelligence system for UK/US government capital programmes.
Takes fragmented multi-source data (P6, MSP, Excel, ERP) from multiple project teams
and produces a single, reliable, confidence-weighted programme health view.

Output:
- **Confidence-weighted RAG** per project (not just Red/Amber/Green — but "Amber, high confidence" vs "Amber, stale data — treat with caution")
- **Composite health score** — schedule (30%), cost (30%), risk (25%), governance (15%)
- **Trend arrows** — is each project improving or deteriorating this period?
- **Gate readiness predictor** — XGBoost model, probability of passing next decision gate
- **Auto-generated exception report** — board-ready paragraphs with specific numbers, decisions required, recommended actions
- **Medallion data pipeline** — Bronze → Silver → Gold with data quality flags

---

### Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

### The Medallion Architecture

**Why Medallion and not just "a script"?**

In a real KPMG engagement, 20 project teams all deliver data differently:
- Team A exports their P6 schedule on Monday
- Team B uses an Excel tracker with different column names
- Team C's risk register hasn't been updated in 6 weeks
- Team D uses SAP, Team E uses Oracle

The Medallion pattern handles this:

**Bronze layer** — receives data exactly as it arrives. Never transforms. Timestamps everything. This is the audit trail.

**Silver layer** — standardises everything to one schema. 30 fields. Fuzzy column matching. Derives CPI from ACWP/BCWP if not supplied. Adds data freshness flags (fresh/stale/missing per source per project).

**Gold layer** — computes all derived metrics: schedule health score (SPI + float + schedule variance), cost health (CPI + VAC), risk health (register score + materialisations), governance health (overdue actions + approvals + audit findings). Combines into weighted composite. Assigns RAG. Adds confidence weighting. Predicts gate readiness.

**The confidence weighting is the key innovation**: a project with stale 3-week-old data gets pulled toward 50/Uncertain rather than confidently scored. The board sees the data quality issue surfaced, not hidden.

---

### Composite Scoring Model

| Dimension | Weight | Key inputs |
|-----------|--------|-----------|
| Schedule health | 30% | SPI, total float, schedule variance (forecast vs baseline) |
| Cost health | 30% | CPI, variance at completion (EAC vs budget) |
| Risk health | 25% | Risk register score (0-10), risks materialised in last 30 days |
| Governance health | 15% | Overdue actions, outstanding approvals, open audit findings, days since board review |

Score ≥ 70 = GREEN | 45–69 = AMBER | < 45 = RED | Confidence < 50% = GREY

---

### Project Context (Interview Use)

**Sector anchor:** UK Combined Authority / Homes England style portfolio.
West Midlands Combined Authority manages ~£2.5bn capital programme across
transport (Metro, highways, rail), energy (BESS, heat networks), urban regeneration,
and affordable housing. KPMG advises on programme assurance for exactly this type of client.

**The problem:** The programme director gets a different spreadsheet from every
project team every month. It takes 3 analysts 2 weeks to consolidate it into a
programme-level view. By the time it reaches the board, it's 3 weeks old and
already out of date. This system does it in under 1 hour, every week.

**What the board actually cares about:**
1. Which projects need a decision from me today? (Exception report)
2. Which projects are heading toward a problem I don't know about yet? (Trend + gate readiness)
3. Can I trust the numbers I'm looking at? (Confidence weighting + freshness flags)

---

### File Structure

```
pac/
├── app.py              — Streamlit dashboard (Programme Cockpit)
├── data_fusion.py      — Medallion architecture (Bronze/Silver/Gold)
├── health_engine.py    — Composite scoring, gate readiness model, RAG logic
├── narrative_engine.py — Auto exception report generator (+ optional Claude API hook)
├── demo_data.py        — Synthetic WMCA 18-project portfolio
├── requirements.txt
└── README.md
```

---

### Interview Talking Points

**"What's the Medallion architecture and why does it matter here?"**
It means the data pipeline has three layers with different responsibilities. Bronze just receives and timestamps — it never loses anything. Silver standardises — so a P6 export and an Excel tracker end up in the same 30-field schema. Gold computes — so the RAG score comes from a documented, repeatable formula, not an analyst's judgement. In a KPMG engagement, the Gold layer is the thing you can defend in an IPA review.

**"Why confidence-weighted RAG and not standard RAG?"**
Standard RAG hides data quality. A project team that stops updating their P6 export looks Green by default — because no one has bad data to score them on. Confidence weighting means stale data pulls the score toward uncertain (50/Grey), forcing the PMO to chase the update. It changes the incentive: teams are rewarded for submitting data, not for submitting good-looking data.

**"How do you get the narratives?"**
Rule-based template engine. It reads the computed values (SPI, CPI, VAC, overdue actions, days to gate) and fills in a structured narrative template. The output is "SPI 0.61 — the project is delivering 39% less progress per pound spent on planned activities. EAC of £415m represents a 22% overrun." That takes a PMO analyst 20 minutes per project to write manually. This produces it for all 18 projects in under 2 seconds.

**"What decisions does this help the Programme Director make?"**
Three: which projects need me to intervene personally this week (RED list), which projects are drifting toward red and need a recovery conversation (AMBER trend-down), and which upcoming gates are at risk of not passing (gate readiness < 60% with < 60 days to gate). Everything else is Green — the programme director doesn't need to look at it.

**"How is this different from a Power BI dashboard?"**
Power BI shows historical data beautifully. This is a decision engine: it tells you what to do next. The exception report is the deliverable, not the dashboard. The board doesn't read dashboards — they read exception reports. This generates the exception report automatically, with specific numbers and recommended actions, every Monday morning before the programme board meeting.
