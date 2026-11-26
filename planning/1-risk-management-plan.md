# Risk Management Plan

**Project:** Disease Prediction Management System
**Course:** Software Design, Dongshin University
**Professor:** Musa Ibrahim
**Prepared by:** Hasan MD Rakibul (2677526), Hosen Aiyub (2677530), Islam MD Din (2677519)
**Date:** 2026-11-26

## 1. Purpose

This plan lists what could go wrong in the project, how likely and how serious each problem is, and what the team will do to prevent it or respond to it. It covers the whole life of the project: planning, analysis, design, implementation, testing and the final demonstration.

## 2. Risk management process

1. **Identify:** the team lists risks during each phase meeting.
2. **Assess:** each risk gets a probability (1 to 5) and an impact (1 to 5). The risk score is probability x impact.
3. **Plan a response:** avoid, reduce, transfer or accept the risk.
4. **Monitor:** the risk owner checks the risk every week and updates the register.

### Scoring scale

| Score | Probability | Impact |
| --- | --- | --- |
| 1 | Very unlikely | Negligible |
| 2 | Unlikely | Minor, easy to fix |
| 3 | Possible | Moderate, costs a few days |
| 4 | Likely | Major, deliverable affected |
| 5 | Almost certain | Severe, project fails or is rejected |

| Risk score | Level | Action |
| --- | --- | --- |
| 1 to 5 | Low | Accept and watch |
| 6 to 12 | Medium | Plan a response |
| 15 to 25 | High | Act immediately, report to professor if needed |

## 3. Risk register

| ID | Category | Risk | P | I | Score | Level | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | Technical | The model gives wrong or misleading predictions because it is trained on a small synthetic dataset | 5 | 4 | 20 | High | Hasan MD Rakibul |
| R02 | Legal and ethical | Users treat the result as a real medical diagnosis and skip seeing a doctor | 4 | 5 | 20 | High | Hasan MD Rakibul |
| R03 | Security | Weak passwords, no CSRF protection, or a default secret key allow account takeover | 3 | 4 | 12 | Medium | Hasan MD Rakibul |
| R04 | Privacy | Health data (symptoms, history) is exposed or misused | 3 | 5 | 15 | High | Hasan MD Rakibul |
| R05 | Schedule | Team members have other courses and assignments, so work is late | 4 | 3 | 12 | Medium | Islam MD Din |
| R06 | Team | A member is unavailable or the work is divided unevenly | 3 | 3 | 9 | Medium | Hasan MD Rakibul |
| R07 | Requirements | The professor adds or changes requirements late (for example new diseases or features) | 4 | 3 | 12 | Medium | Hasan MD Rakibul |
| R08 | Technical | The app fails during the demo (environment, missing package, database error) | 3 | 5 | 15 | High | Hosen Aiyub |
| R09 | Technical | Code changes break existing features (no regression check) | 3 | 3 | 9 | Medium | Hosen Aiyub |
| R10 | Technical | Loss of code or documents (computer failure, deleted files) | 2 | 5 | 10 | Medium | Hasan MD Rakibul |
| R11 | Knowledge | Team members cannot explain the code or design to the professor | 3 | 4 | 12 | Medium | Islam MD Din |
| R12 | Scope | Too many features planned (map, more diseases, treatment advice) for the time available | 3 | 3 | 9 | Medium | Hasan MD Rakibul |
| R13 | Technical | Third-party service for the facility map is unavailable, changes its terms, or needs an API key | 3 | 2 | 6 | Medium | Hosen Aiyub |
| R14 | Quality | Documents (SRS, RTM, diagrams) disagree with the code | 3 | 3 | 9 | Medium | Islam MD Din |
| R15 | Technical | Poor performance or crash when many users register or predict at once | 2 | 2 | 4 | Low | Hosen Aiyub |

## 4. Risk response plan

| ID | Strategy | Preventive action | Contingency (if it happens) |
| --- | --- | --- | --- |
| R01 | Reduce | State clearly that the data is synthetic; keep the model simple and explainable; show only top 3 results with a capped score (95%); plan a real dataset (Kaggle) as future work | Explain the limitation to the professor and show the dataset-generation code |
| R02 | Reduce | Disclaimer in footer and on every result page; always show "consult a doctor" and the specialist type; no drug doses | Add a stronger warning banner and an emergency note |
| R03 | Reduce | Passwords are hashed; set `SECRET_KEY` from the environment; add CSRF tokens and password rules; change the demo admin password | Reset the database, rotate the secret key |
| R04 | Reduce | Store only name, email and symptoms; users can delete their history; no data sold or shared; admin sees statistics only | Delete affected records and tell users |
| R05 | Reduce | Weekly plan with dates; split work by the RACI matrix; finish early deliverables first | Cut optional features, keep the core flow |
| R06 | Reduce | Clear roles in the RACI matrix and staffing plan; short weekly check-in | Reassign tasks; lead takes over the critical ones |
| R07 | Accept and reduce | Keep the design modular (diseases are data in `data.py`); ask the professor to confirm requirements early | Add new diseases or fields in the knowledge base without changing the code structure |
| R08 | Reduce | Test on a clean virtual environment; keep `requirements.txt` up to date; run the demo once before the presentation | Use a second laptop, or screenshots and a screen recording as backup |
| R09 | Reduce | Run the automated test suite (`python -m unittest discover -s tests -v`) after every change | Revert to the last working version in Git |
| R10 | Reduce | Everything in GitHub; commit often; keep a zip backup | Clone or download the last commit |
| R11 | Reduce | Each member reads the SRS, sequence diagram and code walkthrough; practice the demo together | Answer from the README and design documents; ask the teammate who built the part |
| R12 | Avoid | Deliver Dengue and Diabetes first, then add other items one by one | Move unfinished items to "future improvements" |
| R13 | Avoid | Use a free map service without a key (or a simple list of facilities by city) | Show a static facility list with links |
| R14 | Reduce | Update the RTM when code or requirements change; review documents before submission | Fix the document, not the code, unless the requirement changed |
| R15 | Accept | SQLite and a small model are enough for a course demo | Note it as a limitation; move to PostgreSQL for deployment |

## 5. Monitoring and reporting

- The risk register is reviewed at each weekly team check-in.
- A risk whose score rises to 15 or more is reported to Prof. Musa Ibrahim.
- New risks get the next ID (R16, R17, ...) and are added to the register with an owner.
- When a risk is closed, its status and the date are noted in this file.

## 6. Risk matrix (probability x impact)

| P \ I | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| **5** | | | | R01 | |
| **4** | | | R05, R07 | | R02 |
| **3** | | R13 | R06, R09, R12, R14 | R03, R11 | R04, R08 |
| **2** | | R15 | | | R10 |
| **1** | | | | | |

## 7. Approval

| Role | Name | Signature / date |
| --- | --- | --- |
| Project lead | Hasan MD Rakibul (2677526) | |
| Team member | Hosen Aiyub (2677530) | |
| Team member | Islam MD Din (2677519) | |
| Supervisor | Prof. Musa Ibrahim | |
