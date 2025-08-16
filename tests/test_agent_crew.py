import pytest
from unittest.mock import patch

# --- Modules to be tested and mocked ---
# This assumes directories have been renamed (e.g., '3_agents' -> 'agents')
from agents import agent_crew
from agents.tools import database_tools
from tests.mocks.mock_llm import MockLLM

# --- Test Fixture ---
# We reuse the session-scoped database setup from test_tools
# and the function-scoped patcher to point the tools to the test DB.
# This assumes pytest is run on the whole 'tests' directory, so the session fixture is available.
from .test_tools import setup_test_database, patch_db_path


# --- Test for the Agent Crew ---

def test_agent_crew_execution_with_mocks(patch_db_path):
    """
    Tests the main `run_agentic_system` function.

    This test ensures that the agent crew can be initialized and can run
    a task using a mocked LLM and a temporary test database. It verifies
    that the dependency injection for the LLM works as expected.
    """
    # --- Setup ---
    # The patch_db_path fixture already points the database_tools to the test DB.

    # Instantiate our MockLLM
    mock_llm = MockLLM()

    # Define a sample query
    query = "What is the key component of the system?"

    # --- Run the System ---
    # Call the main execution function, injecting the MockLLM
    response_stream = agent_crew.run_agentic_system(query, llm_client=mock_llm)

    # The response is a generator, so we consume it to get the full string
    full_response = "".join([token for token in response_stream])

    # --- Assertion ---
    # The most important thing to assert is that the output is the
    # hardcoded response from our MockLLM. This proves that the mock
    # was successfully injected and that the crew executed without crashing.
    assert full_response == "This is a mock LLM response to the prompt."
