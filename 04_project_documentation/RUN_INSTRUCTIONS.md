# UrbanPulse Project Run Instructions

## Environment

Use Python 3.10 or newer. From the project root:

```text
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Use the finalized database

The packaged database is:

`02_final_outputs/urbanpulse_rdbms.sqlite`

It can be opened with SQLite, DB Browser for SQLite, or queried from Python.

## Run a packaged script

Scripts resolve their input, output, and database paths relative to the project folder. Run them from the scripts directory:

```text
cd 03_reproducibility_scripts
python run_step5_compact_dashboard.py
```

The script writes its result to `02_final_outputs/`.

## Run the interactive dashboard

After installing the requirements, from the project root run:

```text
streamlit run 05_dashboard/urbanpulse_app.py
```

The dashboard opens in a browser and reads the SQLite database in read-only mode. Use the sidebar controls to filter the descriptive views.

## Rebuild caution

The analysis scripts write to the packaged database and output files. Preserve a copy of the finalized package before rebuilding. The temperature benchmark scripts also require network access to retrieve external source data.

The source workbook is intentionally preserved in `01_source_materials/`. The raw database layer must not be edited manually.

## Stage 2 raw-to-canonical refresh

Run the portable Stage 2 layer refresh against a disposable database copy first:

```text
python 03_reproducibility_scripts/refresh_stage2_layers.py \
  --input 02_final_outputs/urbanpulse_phase4_working.xlsx \
  --db /path/to/disposable.sqlite \
  --output-dir /path/to/refresh_reports
```

The script rebuilds only the raw and canonical layer tables, flags, change log, coverage summaries, and Stage 2 report. It does not impute values or rerun later analysis. After any new source refresh, rerun the sensitivity, modeling, provenance, and fitness stages before publishing a new package.

## Stage 3 observed and sensitivity layers

The promoted Stage 3 sensitivity workflow is:

`03_reproducibility_scripts/run_step5a_imputation_sensitivity.py`

Run it only after preserving the finalized database or against a disposable copy. It rebuilds the separately labeled imputation tables and sensitivity-only imputation flags. It does not overwrite raw values or canonical cleaned values. The primary view remains observed-only. Rows with unknown zones may remain in that view for analyses that do not require zone; zone-based analyses must filter to non-null observed zones.

## Zone-complete primary analyses

Use `v_primary_zone_complete` for every primary analysis requiring zone. It contains 1,462 observed-only rows with known zones. The underlying raw and canonical rows remain preserved.

The policy can be recreated with:

`python 03_reproducibility_scripts/apply_zone_complete_primary_policy.py`

## Recommended presentation path

For the college demonstration, use the existing database and dashboard first. Rebuilding the full analysis is optional and should be done only after reviewing the data contract and the open issues register.
