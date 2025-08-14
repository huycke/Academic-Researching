# Academic-Researching: A Private, Multi-Agent Research Assistant

    An advanced, local-first RAG pipeline and multi-agent system designed for the sophisticated analysis and synthesis of academic documents.

This project provides a complete, end-to-end solution for transforming a corpus of academic PDFs into an interactive, trustworthy research assistant. It goes beyond simple Q&A by employing a collaborative crew of AI agents to deliver synthesized, cited, and context-aware answers. The entire system is designed to run locally, ensuring complete data privacy, and is built with a modular architecture for extensibility, maintainability, and operational robustness.

✨ Key Features

    Robust Ingestion Pipeline: A resilient, multi-step process including LLM-based validation and correction of OCR/extraction errors, metadata enrichment (summaries, entities), and content-aware semantic chunking.

    Self-Contained Knowledge Base: Uses txtai as an efficient, self-contained document database, storing rich metadata alongside vector embeddings, with support for incremental indexing.

    Dynamic Multi-Agent System: Employs a CrewAI-powered system featuring a Router Agent that dynamically selects the appropriate workflow—either a quick, direct tool call for factual queries or a full collaborative crew for complex analysis.

    Collaborative Crew (Researcher -> Analyst -> Editor): For complex tasks, agents with specialized roles work together, engaging in inter-agent validation to ensure accuracy and depth.

    Verifiable, Cited Responses: The final output includes inline citations that link directly back to the specific source text chunks used to generate each claim, providing full transparency.

    Interactive & Modern UI: A Streamlit front-end supports full conversation history and streams agent responses in real-time, creating an engaging and responsive user experience.

    Privacy-First: Designed to run entirely on local hardware with local models (via LM Studio, Ollama, etc.), ensuring documents and queries never leave your machine.

    Production-Ready Design: Includes a comprehensive framework for testing, error handling, dependency management, and deployment, making the project stable and maintainable.

🏛️ System Architecture

The application follows a modular, unidirectional data flow, ensuring a clean separation of concerns between its various stages. The architecture is designed for resilience, with clear data handoffs and robust error handling at each step.

Data Flow:
PDFs -> [1. Ingestion Pipeline] -> Cleaned & Enriched JSON -> [2. Database Builder] -> txtai Index <- [3. Agent Tools] <-> [3. Agent Crew] <-> [4. Streamlit App] <- User

    Ingestion: Raw PDFs are processed into cleaned, validated, and enriched data ready for indexing. Failed files are quarantined.

    Database: The processed data is incrementally indexed into a self-contained txtai vector database.

    Agents & Tools: The CrewAI system uses robust tools to query the database. A Router Agent directs user queries to the appropriate workflow. All activities are logged.

    Application: The Streamlit app provides the user interface, manages state, and renders the streamed, cited output from the agent crew, while gracefully handling backend errors.

📁 Repository Structure

academic-agent-workflow/
├── .env                  # Environment variables (API keys, model endpoints)
├── .gitignore
├── README.md             # This file
├── requirements.txt      # Pinned project dependencies for reproducibility
├── Dockerfile            # For containerizing the application for easy deployment
├── config/
│   ├── prompts/
│   │   ├── router_agent.md
│   │   ├── researcher.md
│   │   ├── analyst.md
│   │   └── editor.md
│   └── main_config.py      # Main application settings (chunking, models, etc.)
├── 1_ingestion/
│   ├── ingest_pipeline.py  # Main script for the ingestion process
│   ├── source_documents/
│   │   ├── pdfs/           # Location for raw PDF files
│   │   ├── cleaned_md/     # Intermediate storage for GROBID's output
│   │   └── quarantined/    # Folder for PDFs that fail the ingestion process
│   └── processed_data/     # Final, chunked JSON objects ready for indexing
├── 2_database/
│   ├── build_database.py   # Script to build/update the txtai index
│   └── db/
│       └── txtai_index/    # The self-contained txtai database files
├── 3_agents/
│   ├── __init__.py
│   ├── agent_crew.py       # Defines the crew, tasks, router, and streaming logic
│   └── tools/
│       ├── __init__.py
│       └── database_tools.py # Tools for querying the txtai index
├── 4_app/
│   └── app.py                # The main Streamlit application script
├── logs/
│   ├── app.log               # Structured logs for observability and debugging
│   └── user_feedback.csv     # Log for explicit user feedback on responses
└── tests/
    ├── __init__.py
    ├── test_data/            # Mock data for testing
    ├── test_tools.py         # Unit tests for database tools
    ├── test_ingestion.py     # Tests for the ingestion pipeline
    └── evals/
        ├── eval_questions.jsonl # Set of questions for evaluating the agent crew
        └── run_evals.py         # Script to run evaluations and score results

⚙️ Component Breakdown

config/

This directory externalizes all configuration from the application logic.

    prompts/: Storing each agent's detailed system prompt in a separate .md file is crucial for maintainability. This allows for easier versioning and tuning of agent behavior without touching Python code. The editor.md prompt, for example, will contain the strict rules for generating inline citations.

    main_config.py: A central place for application-level settings like chunking parameters, model names, or API retry settings.

1_ingestion/ 🧠

This module is a resilient data-processing pipeline responsible for ensuring data quality.

    ingest_pipeline.py: This is an idempotent script that finds new documents in source_documents/pdfs/ and processes them. It features robust try...except blocks to handle file-specific errors. Failed files are moved to the quarantined/ folder, and the error is logged, allowing the pipeline to continue processing the remaining documents. The pipeline executes three key steps:

        LLM Validation: Feeds the raw GROBID markdown to an LLM to correct OCR errors and normalize formatting.

        Metadata Enrichment: Uses an LLM to generate a document-level summary and extract key entities.

        Semantic Chunking: Uses txtai's native TextSplitter to intelligently chunk the cleaned documents.

    processed_data/: The final output is a series of JSON files, ready for the database builder.

2_database/ 🗃️

This module creates and maintains the project's single source of truth.

    build_database.py: This script is responsible for creating or updating the txtai index. It is designed for incremental updates, checking which documents are already indexed and only processing new ones. It indexes each chunk along with its rich metadata (source document, page, summary, entities, and a unique chunk_id for citations).

3_agents/ 🚀

This is the core intelligence of the application, designed for robustness and observability.

    tools/database_tools.py: This module contains functions for agents to query the txtai index. These tools are built defensively, handling cases where no results are found and returning clear, informative messages to the agent instead of None or an error.

    agent_crew.py: This file defines the entire agentic system. It initializes the Router Agent to analyze the user's query and select an execution path (a simple tool call or the full crew). The kickoff process is configured to stream its output (yield tokens) and is wrapped in error handling to manage LLM API failures, communicating status back to the front-end. All significant events (agent thoughts, tool calls, final decisions) are logged for debugging.

4_app/ 💬

This module delivers a user-friendly and resilient front-end experience.

    app.py: This Streamlit application script manages the UI and state.

        It uses st.session_state to maintain a persistent conversation history.

        It uses st.write_stream() to render the agent crew's response in real-time.

        It parses [chunk_id] markers into clickable buttons that display the source text in an st.expander.

        It includes simple "👍 / 👎" feedback buttons, which, when clicked, log the conversation context to logs/user_feedback.csv.

🛡️ Testing, Deployment, & Operations

This section outlines the plan for ensuring the application is robust, reproducible, and maintainable.

    Testing & Evaluation Strategy:

        Unit/Integration Tests: The tests/ directory contains tests for all deterministic components of the application, such as the ingestion helpers and database tools.

        LLM Evaluations: The tests/evals/ directory provides a framework for testing the quality of the non-deterministic agentic system. run_evals.py will execute a suite of predefined questions and use an LLM-as-a-judge to score the outputs for correctness and citation accuracy, preventing regressions when prompts or models are changed.

    Error Handling & Resilience: The application is designed to be resilient. The ingestion pipeline isolates file-specific errors, and all external API calls (to the LLM endpoint) are wrapped in a retry mechanism with exponential backoff to handle temporary network or model unavailability. Errors are communicated clearly to the user through the UI.

    Dependency & Deployment Plan:

        Dependencies: The project will use a Python venv to manage its environment. The requirements.txt file will be "frozen" with specific versions (pip freeze > requirements.txt) to ensure perfect reproducibility.

        Deployment: A Dockerfile is included to containerize the entire application. This simplifies deployment and ensures the application runs consistently across different environments with a single docker run command.

    Observability & User Feedback Loop:

        Logging: Structured logging to logs/app.log provides a detailed trace of each query, including the router's decision, each agent's process, and all tool interactions. This is essential for debugging.

        Feedback: The explicit user feedback mechanism provides invaluable data for identifying systemic weaknesses and guiding future improvements.
