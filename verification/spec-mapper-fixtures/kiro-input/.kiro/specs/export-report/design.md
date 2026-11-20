# Design Document

## Overview

A new handler `export_csv` in `reports/api.py` builds the rows with the existing `monthly_sales` query and writes them with the standard `csv` module. No new dependency.

## Components

- `reports/api.py`: the handler and the audit record.
- `reports/export.py`: row formatting.
