# Requirements Document

> Synthetic example written for the mapper's tests from public descriptions of Kiro's layout; it is not output of Kiro.

## Introduction

Users want to export the monthly sales report as a CSV file so that finance can open it in a spreadsheet.

## Requirements

### Requirement 1

**User Story:** As a finance analyst, I want to download the monthly report as CSV, so that I can sort and filter it.

#### Acceptance Criteria

1. WHEN the analyst chooses "Export CSV" THEN the system SHALL return one row per sale with the columns date, region and amount.
2. WHEN the month has no sales THEN the system SHALL return only the header row.

### Requirement 2

**User Story:** As an administrator, I want exports to be logged, so that I can see who exported what.

#### Acceptance Criteria

1. WHEN an export is produced THEN the system SHALL record the user, the month and the time.
