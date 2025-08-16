# tests/setup_test_db.py

import os
from pathlib import Path
from txtai import Embeddings

# --- Configuration ---
TEST_DATA_DIR = Path(__file__).parent / "test_data"
SOURCE_MD_FILE = TEST_DATA_DIR / "sample_doc.md"
DB_OUTPUT_DIR = Path(__file__).parent / "temp_db"

def build_test_database():
    """
    Builds a small txtai index from the sample markdown file for testing purposes.
    """
    print("--- Building Test Database ---")

    if not SOURCE_MD_FILE.is_file():
        print(f"Error: Source markdown file not found at {SOURCE_MD_FILE}")
        return

    # Ensure the output directory exists
    DB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {DB_OUTPUT_DIR}")

    # Read the content of the markdown file
    with open(SOURCE_MD_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create a list of dictionaries to index.
    # We'll treat the whole document as a single chunk for this simple test DB.
    data_to_index = [
        {
            "id": "sample_doc_chunk_001",
            "text": content,
            "source_filename": "sample_doc.md"
        }
    ]

    # Create and save the embeddings index
    try:
        print("Initializing embeddings model...")
        # Using a default, lightweight model for testing
        embeddings = Embeddings(content=True, path="sentence-transformers/all-MiniLM-L6-v2")

        print(f"Indexing {len(data_to_index)} document(s)...")
        embeddings.index(data_to_index)

        db_save_path = DB_OUTPUT_DIR
        print(f"Saving index to {db_save_path}...")
        embeddings.save(str(db_save_path))

        print("✅ Test database built successfully.")
    except Exception as e:
        print(f"❌ An error occurred while building the test database: {e}")

if __name__ == "__main__":
    build_test_database()
