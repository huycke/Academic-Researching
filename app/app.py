# app/app.py

import streamlit as st
import os
import sys
import re
import csv
from pathlib import Path

# --- Add project root to sys.path ---
# This is crucial for ensuring the script can find top-level modules like `config` and `agents`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Imports from our project ---
# It's good practice to keep these imports after the sys.path modification
try:
    from agents.agent_crew import run_agentic_system
    from agents.tools.database_tools import get_chunk_by_id
except ImportError as e:
    st.error(f"Failed to import agent modules. Please ensure the project structure is correct and all dependencies are installed. Error: {e}")
    st.stop()

# --- Page Configuration ---
st.set_page_config(
    page_title="Nexus Scholar",
    page_icon="📚",
    layout="wide"
)

# --- Page Title and Header ---
st.title("📚 Nexus Scholar: Your Private Research Assistant")
st.write("This application allows you to chat with a crew of AI agents to get synthesized, cited answers from your document library.")

# --- Initial UI setup ---
# We will add more logic for conversation history and agent interaction in the next steps.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Awaiting user input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        # Call the agentic system and stream the response
        response_stream = run_agentic_system(prompt)
        full_response = st.write_stream(response_stream)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    # Store the last response for feedback logging
    st.session_state.last_response = {
        "query": prompt,
        "response": full_response
    }

    # --- Citation Handling ---
    # After the response, find all citations and prepare them for display
    citation_ids = set(re.findall(r'\[(.*?)\]', full_response))
    if citation_ids:
        st.session_state.citations = {cid: False for cid in citation_ids}

# --- Display Citations ---
if "citations" in st.session_state and st.session_state.citations:
    st.markdown("---")
    st.subheader("Cited Sources")

    cols = st.columns(len(st.session_state.citations))
    for i, cid in enumerate(st.session_state.citations):
        if cols[i].button(cid, key=f"btn_{cid}"):
            # Toggle the visibility of the expander
            st.session_state.citations[cid] = not st.session_state.citations[cid]

    for cid, is_visible in st.session_state.citations.items():
        if is_visible:
            with st.expander(f"Source: {cid}", expanded=True):
                with st.spinner("Fetching source text..."):
                    source_text = get_chunk_by_id(cid)
                    st.markdown(source_text)

# --- Feedback Handling ---
def log_feedback(feedback: str):
    """Logs the user's feedback to a CSV file."""
    feedback_file = Path(project_root) / "logs/user_feedback.csv"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)

    # Get the last query and response from session state
    last_response = st.session_state.get("last_response", {})
    query = last_response.get("query", "N/A")
    response = last_response.get("response", "N/A")

    # Write to CSV
    try:
        file_exists = feedback_file.is_file()
        with open(feedback_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "query", "response", "feedback"]) # Header

            from datetime import datetime
            writer.writerow([datetime.now().isoformat(), query, response, feedback])

        st.toast("Thank you for your feedback!", icon="✅")
    except Exception as e:
        st.error(f"Failed to log feedback: {e}")

if "last_response" in st.session_state:
    st.markdown("---")
    feedback_cols = st.columns([1, 1, 8]) # Adjust column ratios as needed
    if feedback_cols[0].button("👍", key="thumbs_up"):
        log_feedback("positive")
    if feedback_cols[1].button("👎", key="thumbs_down"):
        log_feedback("negative")
