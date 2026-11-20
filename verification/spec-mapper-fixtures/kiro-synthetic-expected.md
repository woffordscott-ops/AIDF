# Task Contract (DRAFT, not approved)

Drafted by `spec_mapper` with the mapping `kiro-synthetic`. A draft is not an approval, a classification or evidence: a person fills each TODO, chooses the class and has it approved before any implementation.
Every line copied from a planning file sits in a quotation under its source file; nothing else in this draft comes from the sources.

- **Change id:** `export-report` (the name of the folder that holds `.kiro/specs/export-report/requirements.md`)
- **Files read:** `.kiro/specs/export-report/design.md`, `.kiro/specs/export-report/requirements.md`, `.kiro/specs/export-report/tasks.md`
- **Parts copied from the source:** 4 of 17. **Parts left as TODO:** 13.

## Approver's opening

- **Read this first:** TODO(author)
- **Problem:** TODO(author)
- **Why it matters:** TODO(author)
- **The change:** TODO(author)
- **Technical details:** TODO(author)
- **What you need to decide:** TODO(author)

## Part A: Minimal

- **Intended outcome:**
  - Source: `.kiro/specs/export-report/requirements.md` (section)
    > ## Introduction
    >
    > Users want to export the monthly sales report as a CSV file so that finance can open it in a spreadsheet.
- **Acceptance criteria:**
  - Source: `.kiro/specs/export-report/requirements.md` (blocks)
    > # Requirements Document
    >
    > > Synthetic example written for the mapper's tests from public descriptions of Kiro's layout; it is not output of Kiro.
    >
    > ## Introduction
    >
    > Users want to export the monthly sales report as a CSV file so that finance can open it in a spreadsheet.
    >
    > ## Requirements
    >
    > ### Requirement 1
    >
    > **User Story:** As a finance analyst, I want to download the monthly report as CSV, so that I can sort and filter it.
    >
    > #### Acceptance Criteria
    >
    > 1. WHEN the analyst chooses "Export CSV" THEN the system SHALL return one row per sale with the columns date, region and amount.
    > 2. WHEN the month has no sales THEN the system SHALL return only the header row.
    >
    > ### Requirement 2
    >
    > **User Story:** As an administrator, I want exports to be logged, so that I can see who exported what.
    >
    > #### Acceptance Criteria
    >
    > 1. WHEN an export is produced THEN the system SHALL record the user, the month and the time.
- **Declared scope:**
  - Source: `.kiro/specs/export-report/tasks.md` (checklist)
    > - [ ] 1. Add `reports/export.py` with the row formatter
    > - [ ] 2. Add the `export_csv` handler to `reports/api.py`
    > - [x] 3. Record each export in the audit log in `reports/audit.py`
- **Outcome records:** TODO(AIDF)

## Part B: Plan

- **Approach:**
  - Source: `.kiro/specs/export-report/design.md` (file)
    > # Design Document
    >
    > ## Overview
    >
    > A new handler `export_csv` in `reports/api.py` builds the rows with the existing `monthly_sales` query and writes them with the standard `csv` module. No new dependency.
    >
    > ## Components
    >
    > - `reports/api.py`: the handler and the audit record.
    > - `reports/export.py`: row formatting.
- **Invariants touched:** TODO(AIDF)
- **Evidence strategy:** TODO(AIDF)
- **Protected files touched:** TODO(AIDF)
- **Recovery / reversal approach:** TODO(AIDF)
- **Review budget:** TODO(AIDF)
- **Dependency changes:** TODO(AIDF)

## Status

- **State:** Established
- **Established by (author):** TODO(author)
- **Approved by (human, T2/T3 only, role: Architect):** none
- **Date:** TODO(author)
- **Class:** TODO(AIDF)
- **Spec Confidence at intake:** TODO(AIDF)
- **Re-evaluated to Clear by:** TODO(AIDF)
