# 2_database/config.py

from pathlib import Path

# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Source Data Path ---
# Path to the JSON files produced by the ingestion pipeline
PROCESSED_DATA_DIR = BASE_DIR / "1_ingestion/processed_data"
LOG_FILE = BASE_DIR / "logs/database_build.log"

# --- Create Directories if they don't exist ---
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
