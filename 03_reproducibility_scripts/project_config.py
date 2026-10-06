"""Portable paths for the packaged UrbanPulse project."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "01_source_materials"
OUTPUT_DIR = PROJECT_ROOT / "02_final_outputs"
INPUT_XLSX = SOURCE_DIR / "02_SmartCities_UrbanPulse_RAW-2.xlsx"
DB_PATH = OUTPUT_DIR / "urbanpulse_rdbms.sqlite"

