# config/main_config.py

# --- LLM Configuration ---
# This configuration assumes you are running a local LLM server (e.g., Ollama, LM Studio)
# The API endpoint for the LLM service
LLM_API_ENDPOINT = "http://localhost:1234/v1/chat/completions"
# The model name to be used for generation, validation, and enrichment
LLM_MODEL_NAME = "local-model" # Or "gpt-4", "claude-3-opus-20240229", etc.
# API key, if required by the service (set to None if not needed)
LLM_API_KEY = "not-required"
# Timeout in seconds for LLM API requests
LLM_TIMEOUT = 300
# The maximum number of tokens to generate in a single request
LLM_MAX_TOKENS = 2048


# --- Semantic Chunking Configuration ---
# These parameters are for the txtai TextSplitter
# The target number of tokens or characters for each chunk
CHUNK_SIZE = 512
# The number of tokens or characters of overlap between consecutive chunks
CHUNK_OVERLAP = 100
# The splitting method. 'sentences' is robust for academic text.
# Other options include 'words', 'characters'.
CHUNK_METHOD = "sentences"


# --- Database Configuration ---
# Path where the final txtai database will be stored
DATABASE_PATH = "2_database/db/txtai_index"


# --- Application Behavior ---
# Set to True to enable verbose logging for debugging purposes
VERBOSE_LOGGING = True
