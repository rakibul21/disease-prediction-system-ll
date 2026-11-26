# System Request

**Project:** Disease Prediction Management System
**Course:** Software Design, Dongshin University
**Professor:** Musa Ibrahim
**Prepared by:** Hasan MD Rakibul (2677526), Hosen Aiyub (2677530), Islam MD Din (2677519)
**Date:** 2026-11-26

## 1. Project sponsor

Professor Musa Ibrahim (course supervisor). The student team is the project team and the first users.

## 2. Business need

Many people search the internet for the meaning of their symptoms and find long, confusing or frightening pages. A simple tool is needed that lets a person tick the symptoms they have and see, in one page, which common illnesses are most likely, what precautions to take and which kind of doctor to visit.

## 3. Business requirements

The system shall:

- let a person register and log in;
- let a logged-in person select symptoms from a list;
- show the 3 most likely diseases with a match score, precautions and the specialist to consult;
- keep a private history of each person's predictions;
- give an administrator a dashboard with usage statistics;
- always remind the user that the result is not a medical diagnosis.

## 4. Business value

| Type | Value |
| --- | --- |
| Tangible | No cash income is expected. The project replaces no existing paid system. |
| Intangible | Gives general users quick first-level health information; shows the team's skills in requirements, design, programming and testing; produces reusable code and documents for the course. |

## 5. Special issues and constraints

- **Not medical advice.** The system is an educational prototype. Its model learns from a synthetic dataset built from symptom profiles written by the team, not from real patient records.
- **Scope.** 19 diseases and 38 symptoms.
- **Platform.** Runs only on the team's own laptops for the demonstration; it is not published on the internet.
- **Technology.** Python, Flask, SQLite; no paid software and no internet connection needed.
- **Time.** Must be finished within the Software Design course term.

## 6. Approval

| Role | Name | Decision |
| --- | --- | --- |
| Sponsor | Prof. Musa Ibrahim | To be approved |
