# 3_agents/tools/database_tools.py

import logging
import os
import sys
from pathlib import Path
from txtai import Embeddings
from crewai import tool

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuration Imports ---
from config import main_config

# --- Setup Logging ---
# It's good practice for tool modules to have their own logger.
logger = logging.getLogger(__name__)

# --- Global Embeddings Object ---
# We load the database once when the module is imported for efficiency.
embeddings = None

def _load_database():
    """
    Internal function to load the txtai database into the global `embeddings` object.
    """
    global embeddings
    db_path = Path(main_config.DATABASE_PATH)

    if not db_path.exists():
        logger.error(f"Database not found at {db_path}. The database tools will not be available.")
        logger.error("Please run the `2_database/build_database.py` script first.")
        embeddings = None
        return

    try:
        logger.info(f"Loading database from: {db_path}")
        embeddings = Embeddings()
        embeddings.load(str(db_path))
        logger.info("✅ Database loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load the database from {db_path}. Error: {e}")
        embeddings = None

# --- Initial Load ---
# Load the database when this module is first imported.
_load_database()


# --- Database Tools ---

@tool("Query Database for Relevant Chunks")
def query_database(query: str, top_k: int = 5) -> str:
    """
    Performs a semantic search on the vector database to find the most
    relevant text chunks for a given query.

    Args:
        query (str): The user's query to search for.
        top_k (int): The number of top results to return.

    Returns:
        str: A formatted string containing the search results, or an
             informative message if no results are found or if the
             database is unavailable.
    """
    if embeddings is None:
        return "Database is not available. Please ensure it has been built correctly."

    try:
        results = embeddings.search(query, limit=top_k)

        if not results:
            return "No relevant information was found in the database for your query."

        # Format the results into a readable string for the agent
        output_str = f"Found {len(results)} relevant chunks for your query:\n\n"
        for i, res in enumerate(results):
            output_str += f"--- Result {i+1} (Score: {res['score']:.4f}) ---\n"
            output_str += f"Chunk ID: {res['id']}\n"
            output_str += f"Source: {res['source_filename']}\n"
            output_str += f"Text: \"{res['text']}\"\n\n"

        return output_str.strip()

    except Exception as e:
        logger.error(f"An error occurred during database query: {e}")
        return "An error occurred while searching the database. Please check the logs."


@tool("Retrieve Specific Chunk by ID")
def get_chunk_by_id(chunk_id: str) -> str:
    """
    Retrieves the content of a specific chunk from the database using its unique ID.

    Args:
        chunk_id (str): The unique ID of the chunk to retrieve (e.g., 'document_name_chunk_001').

    Returns:
        str: A formatted string containing the chunk's content and source,
             or an informative message if the ID is not found or the
             database is unavailable.
    """
    if embeddings is None:
        return "Database is not available. Please ensure it has been built correctly."

    try:
        # Use a SQL-like query to fetch the specific chunk by its ID
        query = f"SELECT text, source_filename FROM txtai WHERE id = '{chunk_id}'"
        result = embeddings.search(query)

        if not result:
            return f"The specified chunk ID '{chunk_id}' does not exist in the database."

        # Format the result into a readable string
        res = result[0]
        output_str = (
            f"Content for Chunk ID: {chunk_id}\n"
            f"Source: {res['source_filename']}\n"
            f"Text: \"{res['text']}\""
        )
        return output_str

    except Exception as e:
        logger.error(f"An error occurred while retrieving chunk by ID '{chunk_id}': {e}")
        return "An error occurred while retrieving the chunk. Please check the logs."
