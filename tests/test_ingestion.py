import pytest
from unittest.mock import MagicMock, patch
import json

# --- Module to be tested ---
# This import assumes the directory has been renamed from '1_ingestion' to 'ingestion'
from ingestion import ingest_pipeline
from tests.mocks.mock_llm import MockLLM

# --- Mock Data ---
MOCK_XML_CONTENT = """
<TEI>
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Mock Paper Title</title></titleStmt>
        </fileDesc>
    </teiHeader>
    <text>
        <body>
            <div type="abstract">
                <p>This is the mock abstract.</p>
            </div>
            <div>
                <head n="1">Introduction</head>
                <p>This is the first paragraph of the introduction.</p>
            </div>
        </body>
    </text>
</TEI>
"""

MOCK_LLM_RESPONSE = {
    "cleaned_text": "# Mock Paper Title\n\n## Abstract\n\nThis is the mock abstract.\n\n## Introduction\n\nThis is the first paragraph of the introduction.",
    "summary": "This is a mock summary of the paper.",
    "entities": ["mocking", "testing", "pytest"]
}

@pytest.fixture
def mock_fs(fs):
    """
    Sets up a fake file system using pyfakefs for testing.
    'fs' is a fixture provided by the pyfakefs library.
    """
    # Create necessary source directories
    fs.create_dir("/app/ingestion/source_documents/pdfs")
    fs.create_dir("/app/ingestion/source_documents/quarantined")
    fs.create_dir("/app/ingestion/processed_data")
    fs.create_dir("/app/ingestion/source_documents/xml_output") # The pipeline uses this temp dir
    fs.create_dir("/app/ingestion/source_documents/cleaned_md") # The pipeline uses this temp dir
    fs.create_dir("/app/logs")

    # Create a dummy PDF file to be "processed"
    fs.create_file("/app/ingestion/source_documents/pdfs/test_paper.pdf", contents="dummy pdf content")

    # Create mock config files that the pipeline will read
    # We need to provide dummy values for the paths used by the pipeline
    # The 'ingest_config' object in the pipeline is loaded from 'ingestion/config.py'
    fs.create_file("/app/ingestion/config.py", contents="""
from pathlib import Path
BASE_DIR = Path('/app')
PDF_SOURCE_DIR = BASE_DIR / "ingestion/source_documents/pdfs"
MD_CLEANED_DIR = BASE_DIR / "ingestion/source_documents/cleaned_md"
QUARANTINED_DIR = BASE_DIR / "ingestion/source_documents/quarantined"
PROCESSED_DATA_DIR = BASE_DIR / "ingestion/processed_data"
XML_OUTPUT_DIR = BASE_DIR / "ingestion/source_documents/xml_output"
LOG_FILE = BASE_DIR / "logs/ingestion.log"
GROBID_SERVER_URL = "http://mock-grobid:8070"
GROBID_TIMEOUT = 10
FORCE_REPROCESS_PDF = True # Forcing for tests
""")

    fs.create_file("/app/config/main_config.py", contents="""
LLM_API_ENDPOINT = "http://mock-llm-server/v1"
LLM_MODEL_NAME = "mock-model"
LLM_API_KEY = "not-required"
LLM_TIMEOUT = 10
LLM_MAX_TOKENS = 1024
CHUNK_METHOD = "sentences"
CHUNK_SIZE = 100
CHUNK_OVERLAP = 20
VERBOSE_LOGGING = True
""")

    fs.create_file("/app/ingestion/prompts.py", contents="""
VALIDATION_ENRICHMENT_PROMPT = "mock prompt: {markdown_text}"
""")

    yield fs


@patch('ingestion.ingest_pipeline.requests.post')
@patch('ingestion.ingest_pipeline.ChatOpenAI')
def test_ingestion_pipeline_success(mock_chat_openai, mock_post, mock_fs):
    """
    Tests the full ingestion pipeline on a successful run.
    Mocks a successful response from GROBID and uses a MockLLM.
    """
    # --- Mock API and Class Responses ---
    # Mock the GROBID API call
    mock_grobid_response = MagicMock()
    mock_grobid_response.status_code = 200
    mock_grobid_response.text = MOCK_XML_CONTENT
    mock_post.return_value = mock_grobid_response

    # Mock the LLM response by having ChatOpenAI return our MockLLM instance
    mock_llm_instance = MockLLM()
    # Our MockLLM needs to return a JSON string, just like the real one would
    mock_llm_instance.invoke = MagicMock(return_value=json.dumps(MOCK_LLM_RESPONSE))
    mock_chat_openai.return_value = mock_llm_instance

    # --- Run the pipeline ---
    # We need to reload the modules to use the fake file system
    import importlib
    importlib.reload(ingest_pipeline)
    ingest_pipeline.main()

    # --- Assertions ---
    # 1. Check that the final JSON file was created
    processed_files = list(mock_fs.glob("/app/ingestion/processed_data/*.json"))
    assert len(processed_files) == 1

    # 2. Check the content of the JSON file
    with open(processed_files[0], 'r') as f:
        data = json.load(f)

    assert data["source_filename"] == "test_paper.pdf"
    assert data["document_summary"] == "This is a mock summary of the paper."
    assert "testing" in data["key_entities"]
    assert len(data["chunks"]) > 0
    assert "first paragraph" in data["chunks"][0]

    # 3. Check that the original PDF was deleted
    assert not mock_fs.exists("/app/ingestion/source_documents/pdfs/test_paper.pdf")

    # 4. Check that the quarantined directory is empty
    quarantined_files = list(mock_fs.glob("/app/ingestion/source_documents/quarantined/*"))
    assert len(quarantined_files) == 0


@patch('ingestion.ingest_pipeline.requests.post')
def test_ingestion_pipeline_grobid_failure(mock_post, mock_fs):
    """
    Tests the pipeline's error handling when GROBID fails.
    """
    # --- Mock API Response ---
    mock_grobid_response = MagicMock()
    mock_grobid_response.status_code = 500
    mock_grobid_response.text = "Internal Server Error"
    mock_post.return_value = mock_grobid_response

    # --- Run the pipeline ---
    import importlib
    importlib.reload(ingest_pipeline)
    ingest_pipeline.main()

    # --- Assertions ---
    # 1. Check that the PDF was moved to quarantine
    quarantined_files = list(mock_fs.glob("/app/ingestion/source_documents/quarantined/*.pdf"))
    assert len(quarantined_files) == 1
    assert quarantined_files[0].name == "test_paper.pdf"

    # 2. Check that no processed file was created
    processed_files = list(mock_fs.glob("/app/ingestion/processed_data/*.json"))
    assert len(processed_files) == 0


def test_xml_to_markdown_conversion(mock_fs):
    """
    Tests the convert_xml_to_md function in isolation.
    """
    # --- Setup ---
    # Read the sample XML content from the real file system before pyfakefs takes over
    with open("tests/test_data/sample.xml", "r") as f:
        xml_content = f.read()

    # Create the necessary files and directories in the fake file system
    xml_path = Path("/app/test.xml")
    md_path = Path("/app/test.md")
    pdf_path = Path("/app/dummy.pdf") # A dummy path for the function signature
    mock_fs.create_file(xml_path, contents=xml_content)

    # --- Run the function ---
    import importlib
    importlib.reload(ingest_pipeline)
    success = ingest_pipeline.convert_xml_to_md(xml_path, md_path, pdf_path)

    # --- Assertions ---
    assert success is True
    assert md_path.exists()

    with open(md_path, 'r') as f:
        markdown_content = f.read()

    assert "# A Sample Paper for Testing" in markdown_content
    assert "## Abstract" in markdown_content
    assert "This is the abstract" in markdown_content
    assert "### 1. Introduction" in markdown_content # Checks heading level
    assert "| Column 1 | Column 2 |" in markdown_content # Checks table conversion
    assert "|---|---|" in markdown_content


@patch('ingestion.ingest_pipeline.requests.post')
@patch('ingestion.ingest_pipeline.ChatOpenAI')
def test_ingestion_pipeline_llm_failure(mock_chat_openai, mock_post, mock_fs):
    """
    Tests the pipeline's error handling when the LLM call fails.
    """
    # --- Mock API and Class Responses ---
    # Mock the GROBID API call to succeed
    mock_grobid_response = MagicMock()
    mock_grobid_response.status_code = 200
    mock_grobid_response.text = MOCK_XML_CONTENT
    mock_post.return_value = mock_grobid_response

    # Mock the LLM to raise an exception upon invocation
    mock_llm_instance = MockLLM()
    mock_llm_instance.invoke = MagicMock(side_effect=Exception("LLM provider error"))
    mock_chat_openai.return_value = mock_llm_instance

    # --- Run the pipeline ---
    import importlib
    importlib.reload(ingest_pipeline)
    ingest_pipeline.main()

    # --- Assertions ---
    # 1. Check that the PDF was moved to quarantine
    quarantined_files = list(mock_fs.glob("/app/ingestion/source_documents/quarantined/*.pdf"))
    assert len(quarantined_files) == 1
    assert quarantined_files[0].name == "test_paper.pdf"

    # 2. Check that no processed file was created
    processed_files = list(mock_fs.glob("/app/ingestion/processed_data/*.json"))
    assert len(processed_files) == 0
