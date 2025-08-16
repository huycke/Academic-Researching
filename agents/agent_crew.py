# agents/agent_crew.py

import os
import sys
import logging
from pathlib import Path

# --- Add project root to sys.path ---
# This is crucial for ensuring the script can find top-level modules like `config`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Imports ---
from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI

from config import main_config
from agents.tools import database_tools

# --- Setup Logging ---
# Configure a logger for the agentic system
log_file = Path(project_root) / "logs/app.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO if main_config.VERBOSE_LOGGING else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_prompt(file_name: str) -> str:
    """
    Loads a prompt from a file in the config/prompts directory.
    """
    prompt_path = Path(project_root) / "config/prompts" / file_name
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_path}")
        return "" # Return empty string if prompt is missing

# --- Tools ---
# The tools are stateless, so they can be defined globally.
query_tool = database_tools.query_database
citation_tool = database_tools.get_chunk_by_id


# --- Main Execution Logic ---

def run_agentic_system(query: str, llm_client=None):
    """
    Runs the full agentic system for a given query.
    This function will handle routing and execute the appropriate crew.
    It yields the output in a streaming fashion.

    Args:
        query (str): The user's query.

    Yields:
        str: Chunks of the agent's output as they are generated.
    """
    logger.info(f"Received query: {query}")

    # --- LLM Setup ---
    # If no LLM client is provided, create the default one.
    # This allows for injecting a mock LLM during testing.
    if llm_client is None:
        logger.info("Initializing default LLM client.")
        llm_client = ChatOpenAI(
            base_url=main_config.LLM_API_ENDPOINT,
            api_key=main_config.LLM_API_KEY,
            model_name=main_config.LLM_MODEL_NAME
        )

    # --- Agent & Task Definitions (scoped to the run) ---
    researcher_agent = Agent(
        role="Researcher",
        goal=load_prompt("researcher.md"),
        backstory="You are a meticulous academic researcher...",
        llm=llm_client,
        tools=[query_tool],
        verbose=True,
    )
    analyst_agent = Agent(
        role="Analyst",
        goal=load_prompt("analyst.md"),
        backstory="You are a brilliant analyst...",
        llm=llm_client,
        verbose=True,
    )
    editor_agent = Agent(
        role="Editor",
        goal=load_prompt("editor.md"),
        backstory="You are a professional editor...",
        llm=llm_client,
        tools=[citation_tool],
        verbose=True,
    )

    research_task = Task(
        description=f"Use your tools to find relevant information in the knowledge base to answer the user's query: '{query}'.",
        expected_output="A compilation of the most relevant text chunks...",
        agent=researcher_agent,
    )
    analysis_task = Task(
        description=f"Analyze the information provided by the researcher and synthesize it into a comprehensive answer to the user's query: '{query}'.",
        expected_output="A detailed analysis of the researcher's findings...",
        agent=analyst_agent,
        context=[research_task],
    )
    editing_task = Task(
        description="Review the analysis provided. Format it into a final, polished response. Ensure every claim is supported by an inline citation in the format [chunk_id].",
        expected_output="A final, well-formatted, and fully cited response...",
        agent=editor_agent,
        context=[analysis_task],
    )

    # --- Crew Definition ---
    research_crew = Crew(
        agents=[researcher_agent, analyst_agent, editor_agent],
        tasks=[research_task, analysis_task, editing_task],
        process=Process.sequential,
        verbose=2,
    )

    # --- Execute the Crew ---
    logger.info("Executing the research crew.")
    inputs = {"query": query}
    try:
        result_stream = research_crew.kickoff(inputs=inputs)
        for token in result_stream:
            yield token
    except Exception as e:
        logger.error(f"An error occurred during crew execution: {e}", exc_info=True)
        yield f"An unexpected error occurred. Please check the logs for more details."

    logger.info("Crew execution finished.")
