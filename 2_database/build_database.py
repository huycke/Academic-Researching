# 2_database/build_database.py

import os
import sys
import json
import logging
from pathlib import Path
from txtai import Embeddings

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuration Imports ---
from config import main_config
import config as db_config

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO if main_config.VERBOSE_LOGGING else logging.WARNING,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler(db_config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Path Definitions ---
PROCESSED_DATA_DIR = db_config.PROCESSED_DATA_DIR
DATABASE_PATH = Path(main_config.DATABASE_PATH)

# Ensure the parent directory for the database exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_or_initialize_embeddings() -> tuple[Embeddings, set]:
    """
    Loads an existing txtai Embeddings index or initializes a new one.
    Also returns the set of already indexed source filenames.

    Returns:
        tuple[Embeddings, set]: A tuple containing the Embeddings object
                                and a set of processed source filenames.
    """
    embeddings = Embeddings()
    indexed_files = set()

    if DATABASE_PATH.exists():
        logger.info(f"Loading existing database from: {DATABASE_PATH}")
        try:
            embeddings.load(str(DATABASE_PATH))
            # Query the loaded index to find out which files are already in it
            results = embeddings.search("SELECT DISTINCT source_filename FROM txtai", limit=10000)
            indexed_files = {r['source_filename'] for r in results}
            logger.info(f"Found {len(indexed_files)} already indexed files.")
        except Exception as e:
            logger.error(f"Failed to load existing database. A new one will be created. Error: {e}")
            # Resetting in case of a corrupted index
            embeddings = Embeddings()
    else:
        logger.info("No existing database found. Initializing a new one.")
        # Configure the new embeddings using the model from the main config
        embeddings = Embeddings(
            path=main_config.SENTENCE_TRANSFORMER_MODEL,
            content=True
        )

    return embeddings, indexed_files


def prepare_data_for_indexing(json_data: dict) -> list[dict]:
    """
    Prepares the data from a single JSON file for txtai indexing.

    Args:
        json_data (dict): The loaded content of a processed JSON file.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents
                    a chunk ready to be indexed.
    """
    prepared_data = []
    source_filename = json_data.get("source_filename", "Unknown")

    for i, chunk_text in enumerate(json_data.get("chunks", [])):
        chunk_id = f"{Path(source_filename).stem}_chunk_{i+1:03d}"

        chunk_data = {
            "id": chunk_id, # txtai uses 'id' field for uniqueness
            "text": chunk_text,
            "source_filename": source_filename,
            "document_summary": json_data.get("document_summary", ""),
            "key_entities": json_data.get("key_entities", [])
        }
        prepared_data.append(chunk_data)

    return prepared_data


def main():
    """
    Main function to build or update the txtai database.
    """
    logger.info("🚀 Starting database build process...")

    embeddings, indexed_files = load_or_initialize_embeddings()

    all_json_files = list(PROCESSED_DATA_DIR.glob("*.json"))

    # Determine which files are new and need to be indexed
    files_to_index = [f for f in all_json_files if f.name not in indexed_files]

    if not files_to_index:
        logger.info("✅ Database is already up-to-date. No new files to index.")
        return

    logger.info(f"Found {len(files_to_index)} new document(s) to index.")

    all_new_data = []
    for json_path in files_to_index:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            prepared_data = prepare_data_for_indexing(data)
            all_new_data.extend(prepared_data)
            logger.info(f"  -> Prepared {len(prepared_data)} chunks from '{json_path.name}'")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load or process '{json_path.name}'. Skipping. Error: {e}")

    if all_new_data:
        logger.info(f"Indexing {len(all_new_data)} new chunks...")
        # The index method takes an iterable of dictionaries
        embeddings.index(all_new_data)

        logger.info(f"Saving updated database to: {DATABASE_PATH}")
        embeddings.save(str(DATABASE_PATH))
        logger.info("✅ Database save complete.")
    else:
        logger.warning("No new data was successfully prepared for indexing.")

    logger.info("Database build process finished.")


if __name__ == "__main__":
    main()
