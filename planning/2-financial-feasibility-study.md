# Financial Feasibility Study

**Project:** Disease Prediction Management System
**Currency:** South Korean won (KRW)
**Date:** 2026-11-26

> All hours below are the team's **planning estimates**, not measured time sheets. The labour value uses the legal minimum wage as a simple, public reference rate: **10,320 KRW per hour in 2026** ([WageIndicator](https://wageindicator.org/work/minimum-wage/updates/2026/minimum-wage-updated-in-south-korea-from-01-january-2026-january-01-2026/)). Students are not actually paid; the figure shows what the effort would cost.

## 1. Technical feasibility

Feasible. The system uses well-known free tools (Python, Flask, SQLite) that the team already knows. A working version exists and passes 23 automated tests (see `../analysis/RTM.pdf`). The only technical risk is that the model learns from synthetic data, which limits its accuracy for real patients; this is accepted because the system is only a classroom prototype.

## 2. Economic feasibility

### 2.1 Development costs

| Item | Detail | Cost (KRW) |
| --- | --- | --- |
| Labour: Hasan MD Rakibul | 100 hours x 10,320 | 1,032,000 |
| Labour: Hosen Aiyub | 30 hours x 10,320 | 309,600 |
| Labour: Islam MD Din | 30 hours x 10,320 | 309,600 |
| Software | Python, Flask, SQLite, VS Code, GitHub: free and open source | 0 |
| Hardware | The team's own laptops, already owned | 0 |
| Hosting | Not needed; the demo runs on a laptop | 0 |
| Internet and electricity | Already paid for personal use; not charged to the project | 0 |
| **Total development cost** | | **1,651,200** |

Only labour has a value; the cash the team must spend is 0 KRW.

### 2.2 Operating costs

| Item | Cost per year (KRW) |
| --- | --- |
| Hosting, licences, domain | 0 |
| Maintenance | 0 in cash (done by the team as part of the course) |
| **Total** | **0** |

### 2.3 Benefits

| Benefit | Type | Value |
| --- | --- | --- |
| Working prototype and complete document set for the course grade | Intangible | Not priced |
| Practice with the full software lifecycle: planning, analysis, design, implementation, testing | Intangible | Not priced |
| Reusable code on GitHub for future projects or the team's thesis work | Intangible | Not priced |
| Quick first-level symptom information for users | Intangible | Not priced; only if later published and medically reviewed |

### 2.4 Conclusion

The project needs **no cash investment** and its value is educational, so a money return (ROI) is not calculated. The cash cost is 0 KRW, and the labour value of 1,651,200 KRW is the cost of the team's time. The project is economically feasible for a course.

## 3. Operational feasibility

Feasible. Anyone with Python 3.9 or newer can start the system with one command (`python app.py`) and use it in a browser. The README gives the steps. No training is needed for users because the pages have one purpose each.

## 4. Schedule feasibility

Feasible. The 160 planned hours fit the course term (see `3-staffing-plan.md` for the phase schedule).

## 5. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Synthetic data gives unrealistic accuracy | Users may over-trust the result | Disclaimer on every result; score capped at 95%; accuracy stated as "on sample data" |
| Team member unavailable | Delay | Tasks shared in the RACI matrix; documents in GitHub |
| Windows blocks unsigned libraries | System does not start | Model written in pure Python; only Flask is installed |
| Real hospital data not available | Cannot train on real cases | Listed as future work; the Kaggle disease-symptom dataset can be used |

## 6. Overall conclusion

The project is **technically, economically, operationally and schedule feasible**, and is recommended for approval as a student prototype.
