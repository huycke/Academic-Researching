import pytest
from unittest.mock import patch
from txtai import Embeddings

# --- Module to be tested ---
# This import assumes the directory has been renamed from '3_agents' to 'agents'
from agents.tools import database_tools

# --- Mock Data ---
MOCK_DB_DATA = [
    {
        "id": "doc1_chunk_001",
        "text": "The quick brown fox jumps over the lazy dog.",
        "source_filename": "document1.pdf",
    },
    {
        "id": "doc1_chunk_002",
        "text": "A key component of the system is the central processing unit.",
        "source_filename": "document1.pdf",
    },
]

# --- Pytest Fixture for Test Database ---
@pytest.fixture(scope="session", autouse=True)
def setup_test_database(tmp_path_factory):
    """
    A session-scoped fixture that builds the test database once.
    `autouse=True` means it will run automatically for the session.
    """
    # We need to import the setup script and run its main function
    from tests import setup_test_db

    # Temporarily change the output directory to a pytest-managed temp dir
    # This prevents cluttering the project with a 'tests/temp_db' folder
    temp_db_path = tmp_path_factory.mktemp("temp_db")

    # Use monkeypatch to override the DB_OUTPUT_DIR in the setup script
    with patch.object(setup_test_db, 'DB_OUTPUT_DIR', temp_db_path):
        setup_test_db.build_test_database()

    # Yield the path to the temporary database for tests to use
    yield temp_db_path


@pytest.fixture(scope="function")
def patch_db_path(monkeypatch, setup_test_database):
    """
    A function-scoped fixture to patch the database path in the tools module.
    This ensures each test runs with a clean patch.
    """
    # The path to the 'config.yml' file within the temp_db directory
    db_config_path = setup_test_database / "config.yml"

    # Patch the DATABASE_PATH in the main_config module, which database_tools reads
    # This assumes that database_tools uses main_config.DATABASE_PATH to find the DB
    # A cleaner way would be to patch database_tools._load_database directly.
    # Let's patch the loaded object instead, which is more robust.

    # Load the temporary embeddings
    temp_embeddings = Embeddings()
    temp_embeddings.load(str(setup_test_database))

    # Patch the global embeddings object in the tools module
    monkeypatch.setattr(database_tools, "embeddings", temp_embeddings)


# --- Tests for query_database ---

def test_query_database_success(patch_db_path):
    """
    Tests the query_database function for a successful query using the temp DB.
    """
    query = "vector database"
    result = database_tools.query_database(query)

    assert "Found 1 relevant chunks" in result
    assert "sample_doc_chunk_001" in result
    assert "sample markdown document" in result

def test_query_database_no_results(patch_db_path):
    """
    Tests the query_database function when no relevant results are found.
    """
    monkeypatch.setattr(database_tools, "embeddings", mock_db_embeddings)

    query = "financial markets"
    result = database_tools.query_database(query)

    assert result == "No relevant information was found in the database for your query."

def test_query_database_unavailable(monkeypatch):
    """
    Tests the query_database function when the database is not loaded.
    """
    monkeypatch.setattr(database_tools, "embeddings", None)

    query = "anything"
    result = database_tools.query_database(query)

    assert result == "Database is not available. Please ensure it has been built correctly."

# --- Tests for get_chunk_by_id ---

def test_get_chunk_by_id_success(patch_db_path):
    """
    Tests the get_chunk_by_id function for a successful retrieval.
    """
    chunk_id = "sample_doc_chunk_001"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert f"Content for Chunk ID: {chunk_id}" in result
    assert "Source: sample_doc.md" in result
    assert "predictable data source" in result

def test_get_chunk_by_id_not_found(patch_db_path):
    """
    Tests the get_chunk_by_id function when the chunk ID does not exist.
    """
    chunk_id = "non_existent_id"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert result == f"The specified chunk ID '{chunk_id}' does not exist in the database."

def test_get_chunk_by_id_unavailable(monkeypatch):
    """
    Tests the get_chunk_by_id function when the database is not loaded.
    """
    monkeypatch.setattr(database_tools, "embeddings", None)

    chunk_id = "doc1_chunk_001"
    result = database_tools.get_chunk_by_id(chunk_id)

    assert result == "Database is not available. Please ensure it has been built correctly."
