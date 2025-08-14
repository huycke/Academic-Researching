# 1_ingestion/config.py

import os
from pathlib import Path

# --- Base Paths ---
# Use pathlib for robust path handling
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Source Document Paths ---
# Raw PDFs are expected to be placed here
PDF_SOURCE_DIR = BASE_DIR / "1_ingestion/source_documents/pdfs"
# Intermediate directory for cleaned Markdown files
MD_CLEANED_DIR = BASE_DIR / "1_ingestion/source_documents/cleaned_md"
# Directory for PDFs that fail processing
QUARANTINED_DIR = BASE_DIR / "1_ingestion/source_documents/quarantined"
# Final processed JSON files for the database
PROCESSED_DATA_DIR = BASE_DIR / "1_ingestion/processed_data"
# Temporary directory for GROBID's raw XML output
XML_OUTPUT_DIR = BASE_DIR / "1_ingestion/source_documents/xml_output"

# --- Create Directories if they don't exist ---
PDF_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
MD_CLEANED_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINED_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
XML_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- GROBID Configuration ---
GROBID_SERVER_URL = "http://localhost:8070"
# Timeout in seconds for the GROBID API request
GROBID_TIMEOUT = 120
# Set to True to re-process a PDF even if its cleaned Markdown file already exists
FORCE_REPROCESS_PDF = False


# --- Logging Configuration ---
LOG_FILE = BASE_DIR / "logs/ingestion.log"
# Create logs directory if it doesn't exist
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
