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

# --- Instantiate LLM and Tools ---

# Configure the LLM to be used by the agents.
# This setup is for a local, OpenAI-compatible model endpoint (e.g., LM Studio)
llm = ChatOpenAI(
    base_url=main_config.LLM_API_ENDPOINT,
    api_key=main_config.LLM_API_KEY,
    model_name=main_config.LLM_MODEL_NAME
)

# Instantiate the tools the agents will use
query_tool = database_tools.query_database
citation_tool = database_tools.get_chunk_by_id


# --- Agent Definitions ---

router_agent = Agent(
    role="Router",
    goal=load_prompt("router_agent.md"),
    backstory="You are an intelligent router responsible for classifying user queries and directing them to the most appropriate processing pipeline.",
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

researcher_agent = Agent(
    role="Researcher",
    goal=load_prompt("researcher.md"),
    backstory="You are a meticulous academic researcher, skilled at digging through dense scientific documents to find relevant information.",
    llm=llm,
    tools=[query_tool],
    verbose=True,
)

analyst_agent = Agent(
    role="Analyst",
    goal=load_prompt("analyst.md"),
    backstory="You are a brilliant analyst, capable of synthesizing complex information into a clear and structured analysis.",
    llm=llm,
    verbose=True,
)

editor_agent = Agent(
    role="Editor",
    goal=load_prompt("editor.md"),
    backstory="You are a professional editor with an impeccable eye for detail, responsible for formatting, clarity, and ensuring every claim is properly cited.",
    llm=llm,
    tools=[citation_tool],
    verbose=True,
)

# --- Task Definitions ---

# Note: The `description` for each task is a crucial part of the prompt.
# It provides the specific instructions for the agent's execution loop.

router_task = Task(
    description="Analyze the following user query and decide if it is a simple, factual question that can be answered with a direct tool call, or a complex, analytical question that requires in-depth research by a crew. Your output must be a single word: either 'simple' or 'complex'. User Query: {query}",
    expected_output="A single word: either 'simple' or 'complex'.",
    agent=router_agent,
)

research_task = Task(
    description="Use your tools to find relevant information in the knowledge base to answer the user's query: '{query}'. Gather all the text chunks that could help answer the question.",
    expected_output="A compilation of the most relevant text chunks from the database, including their IDs and source information.",
    agent=researcher_agent,
)

analysis_task = Task(
    description="Analyze the information provided by the researcher and synthesize it into a comprehensive answer to the user's query: '{query}'. Your analysis should be well-structured and easy to understand.",
    expected_output="A detailed analysis of the researcher's findings, forming a coherent answer to the user's original query.",
    agent=analyst_agent,
    context=[research_task], # This task depends on the output of the research_task
)

editing_task = Task(
    description="Review the analysis provided. Format it into a final, polished response. Ensure every claim is supported by an inline citation in the format [chunk_id]. Use your tool to verify chunk contents if needed. The final output must be fully cited and ready for the user.",
    expected_output="A final, well-formatted, and fully cited response to the user's query.",
    agent=editor_agent,
    context=[analysis_task], # This task depends on the output of the analysis_task
)

# --- Crew Definition ---

research_crew = Crew(
    agents=[researcher_agent, analyst_agent, editor_agent],
    tasks=[research_task, analysis_task, editing_task],
    process=Process.sequential,
    verbose=2, # Use verbose level 2 for detailed logging of agent actions
)

# --- Main Execution Logic ---

def run_agentic_system(query: str):
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

    # For now, we will directly invoke the research crew.
    # The router logic can be integrated here in a future step.
    # e.g., router_decision = router_agent.execute_task(router_task, context={"query": query})

    logger.info("Executing the full research crew.")

    # Prepare the inputs for the crew's tasks
    inputs = {"query": query}

    try:
        # kickoff() returns an iterator when streaming is enabled
        result_stream = research_crew.kickoff(inputs=inputs)

        for token in result_stream:
            yield token

    except Exception as e:
        logger.error(f"An error occurred during crew execution: {e}", exc_info=True)
        yield f"An unexpected error occurred: {e}. Please check the logs for more details."

    logger.info("Crew execution finished.")
