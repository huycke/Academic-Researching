# 1_ingestion/ingest_pipeline.py

import os
import sys
import requests
import time
import logging
import shutil
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from txtai.text import TextSplitter

# --- Add project root to sys.path ---
# This allows for absolute imports of modules from the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuration Imports ---
# Import settings from the newly created config files
from config import main_config
# The local config and prompts can be imported directly as they are in the same directory
import config as ingest_config
import prompts

# --- Setup Logging ---
# Configure a logger for this script
logging.basicConfig(
    level=logging.INFO if main_config.VERBOSE_LOGGING else logging.WARNING,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler(ingest_config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_grobid_server(url: str) -> bool:
    """
    Checks if the GROBID server is running and accessible.

    Args:
        url (str): The base URL of the GROBID server.

    Returns:
        bool: True if the server is up, False otherwise.
    """
    ping_url = f"{url}/api/isalive"
    try:
        response = requests.get(ping_url, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ GROBID server is active at {url}")
            return True
        else:
            logger.warning(f"⚠️ GROBID server at {url} responded with status {response.status_code}.")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Could not connect to GROBID server at {url}.")
        logger.error(f"   Error: {e}")
        logger.error("   Please ensure the GROBID Docker container is running and the URL is correct.")
        return False

def quarantine_file(pdf_path: Path, reason: str):
    """
    Moves a file to the quarantined directory and logs the reason.

    Args:
        pdf_path (Path): The path to the PDF file to be moved.
        reason (str): The reason for quarantining the file.
    """
    try:
        quarantined_path = ingest_config.QUARANTINED_DIR / pdf_path.name
        shutil.move(str(pdf_path), str(quarantined_path))
        logger.warning(f"Moved '{pdf_path.name}' to quarantine. Reason: {reason}")
    except Exception as e:
        logger.error(f"Failed to move '{pdf_path.name}' to quarantine. Error: {e}")

def process_pdf_with_grobid(pdf_path: Path, xml_path: Path) -> bool:
    """
    Sends a single PDF to the GROBID server for processing into TEI/XML.

    Args:
        pdf_path (Path): The path to the source PDF file.
        xml_path (Path): The path where the output XML should be saved.

    Returns:
        bool: True if processing was successful, False otherwise.
    """
    api_url = f"{ingest_config.GROBID_SERVER_URL}/api/processFulltextDocument"

    logger.info(f"Processing '{pdf_path.name}' with GROBID...")

    try:
        with open(pdf_path, 'rb') as pdf_file:
            # The file is sent as multipart-form data
            files = {'input': (pdf_path.name, pdf_file, 'application/pdf', {'Expires': '0'})}

            # Make the request to the GROBID API
            response = requests.post(
                api_url,
                files=files,
                timeout=ingest_config.GROBID_TIMEOUT
            )

        if response.status_code == 200:
            # Write the successful response content to the XML file
            with open(xml_path, 'w', encoding='utf-8') as xml_f:
                xml_f.write(response.text)
            logger.info(f"  -> Successfully created XML file: '{xml_path.name}'")
            return True
        else:
            # Handle API errors (e.g., bad request, server error)
            error_message = f"GROBID returned status {response.status_code}. Response: {response.text[:200]}..."
            logger.error(f"  -> Error processing '{pdf_path.name}': {error_message}")
            quarantine_file(pdf_path, error_message)
            return False

    except requests.exceptions.Timeout:
        timeout_message = f"Request timed out after {ingest_config.GROBID_TIMEOUT} seconds."
        logger.error(f"  -> Error processing '{pdf_path.name}': {timeout_message}")
        quarantine_file(pdf_path, timeout_message)
        return False
    except requests.exceptions.RequestException as e:
        network_error = f"A network error occurred: {e}"
        logger.error(f"  -> Error processing '{pdf_path.name}': {network_error}")
        quarantine_file(pdf_path, network_error)
        return False
    except Exception as e:
        unknown_error = f"An unexpected error occurred: {e}"
        logger.error(f"  -> Error processing '{pdf_path.name}': {unknown_error}")
        quarantine_file(pdf_path, unknown_error)
        return False


# --- XML to Markdown Conversion ---

def clean_text(text: str) -> str:
    """
    Cleans and normalizes text extracted from XML elements.
    - Replaces multiple spaces/newlines with a single space.
    - Strips leading/trailing whitespace.
    """
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def table_to_markdown(table_element) -> str:
    """
    Converts a BeautifulSoup table element into a Markdown table string.
    """
    markdown_table = []
    header_processed = False

    for row in table_element.find_all('row'):
        cells = [clean_text(cell.get_text()) for cell in row.find_all('cell')]
        markdown_table.append(f"| {' | '.join(cells)} |")

        if not header_processed:
            separator = '|' + '|'.join(['---'] * len(cells)) + '|'
            markdown_table.append(separator)
            header_processed = True

    return "\n".join(markdown_table) + "\n"

def convert_xml_to_md(xml_path: Path, md_path: Path, pdf_path: Path) -> bool:
    """
    Parses a GROBID TEI/XML file and converts it into a clean Markdown file.

    Args:
        xml_path (Path): The path to the input XML file.
        md_path (Path): The path for the output Markdown file.
        pdf_path (Path): The original PDF path, for quarantining on failure.

    Returns:
        bool: True if conversion was successful, False otherwise.
    """
    logger.info(f"Converting '{xml_path.name}' to Markdown...")
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml-xml')

        markdown_parts = []

        # Discard unwanted elements like in-text citations and footnotes
        for ref in soup.find_all('ref', {'type': 'bibr'}):
            ref.decompose()
        for note in soup.find_all('note', {'place': 'foot'}):
            note.decompose()

        # Extract Title
        title_element = soup.find('titleStmt').find('title')
        if title_element:
            title = clean_text(title_element.get_text())
            markdown_parts.append(f"# {title}\n")

        # Extract Abstract
        abstract = soup.find('abstract')
        if abstract:
            markdown_parts.append("## Abstract\n")
            for p in abstract.find_all('p'):
                markdown_parts.append(clean_text(p.get_text()) + "\n")

        # Extract Body Content
        body = soup.find('body')
        if body:
            for div in body.find_all('div', recursive=False):
                head = div.find('head')
                if head:
                    level = head.get('n', '1').count('.') + 2
                    heading_marker = '#' * level
                    heading_text = clean_text(head.get_text())
                    markdown_parts.append(f"\n{heading_marker} {heading_text}\n")

                for element in div.find_all(['p', 'formula', 'figure'], recursive=False):
                    if element.name == 'p':
                        markdown_parts.append(clean_text(element.get_text()) + "\n")
                    elif element.name == 'formula':
                        formula_text = clean_text(element.get_text())
                        markdown_parts.append(f"$$\n{formula_text}\n$$\n")
                    elif element.name == 'figure':
                        if element.find('table'):
                            markdown_parts.append(table_to_markdown(element.find('table')))
                        fig_desc = element.find('figDesc')
                        if fig_desc:
                            markdown_parts.append(f"[Image: {clean_text(fig_desc.get_text())}]\n")

        # Write to Markdown file
        final_markdown = "\n".join(markdown_parts)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown)

        logger.info(f"  -> Successfully created Markdown file: '{md_path.name}'")
        return True

    except Exception as e:
        error_message = f"Failed to convert XML to Markdown: {e}"
        logger.error(f"  -> Error processing '{xml_path.name}': {error_message}")
        quarantine_file(pdf_path, error_message)
        # Clean up the failed markdown file if it was created
        if md_path.exists():
            md_path.unlink()
        return False


# --- LLM Validation and Enrichment ---

def call_llm(prompt: str) -> dict | None:
    """
    Calls the local LLM API with a given prompt.

    Args:
        prompt (str): The complete prompt to send to the LLM.

    Returns:
        dict | None: The parsed JSON response from the LLM, or None on failure.
    """
    headers = {
        "Content-Type": "application/json",
    }
    if main_config.LLM_API_KEY and main_config.LLM_API_KEY != "not-required":
        headers["Authorization"] = f"Bearer {main_config.LLM_API_KEY}"

    data = {
        "model": main_config.LLM_MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, # Low temperature for deterministic output
        "max_tokens": main_config.LLM_MAX_TOKENS,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            main_config.LLM_API_ENDPOINT,
            headers=headers,
            data=json.dumps(data),
            timeout=main_config.LLM_TIMEOUT
        )
        response.raise_for_status()

        response_json = response.json()
        content = response_json['choices'][0]['message']['content']

        return json.loads(content)

    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Raw response content: {response.text}")
        return None

def validate_and_enrich_with_llm(md_path: Path, pdf_path: Path) -> dict | None:
    """
    Uses an LLM to validate, clean, and enrich the Markdown content.

    Args:
        md_path (Path): Path to the cleaned Markdown file.
        pdf_path (Path): The original PDF path, for quarantining on failure.

    Returns:
        dict | None: A dictionary with cleaned_text, summary, and entities, or None on failure.
    """
    logger.info(f"Validating and enriching '{md_path.name}' with LLM...")

    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        prompt = prompts.VALIDATION_ENRICHMENT_PROMPT.format(markdown_text=markdown_text)

        llm_response = call_llm(prompt)

        if not llm_response or not all(k in llm_response for k in ["cleaned_text", "summary", "entities"]):
            error_message = "LLM response was invalid or missing required keys."
            logger.error(f"  -> Error processing '{md_path.name}': {error_message}")
            quarantine_file(pdf_path, error_message)
            return None

        logger.info(f"  -> Successfully validated and enriched content for '{md_path.name}'.")
        return llm_response

    except Exception as e:
        error_message = f"An unexpected error occurred during LLM validation: {e}"
        logger.error(f"  -> Error processing '{md_path.name}': {error_message}")
        quarantine_file(pdf_path, error_message)
        return None


# --- Semantic Chunking and Final Output ---

def chunk_text_with_txtai(text: str) -> list[str]:
    """
    Splits the text into semantic chunks using txtai.

    Args:
        text (str): The input text to be chunked.

    Returns:
        list[str]: A list of text chunks.
    """
    logger.info("Chunking text with txtai...")
    try:
        text_splitter = TextSplitter(
            method=main_config.CHUNK_METHOD,
            size=main_config.CHUNK_SIZE,
            overlap=main_config.CHUNK_OVERLAP
        )
        chunks = text_splitter(text)
        logger.info(f"  -> Successfully split text into {len(chunks)} chunks.")
        return chunks
    except Exception as e:
        logger.error(f"Failed to chunk text: {e}")
        return []

def save_processed_data(output_path: Path, data: dict):
    """
    Saves the final processed data to a JSON file.

    Args:
        output_path (Path): The path for the output JSON file.
        data (dict): The dictionary containing the processed data.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"  -> Successfully saved processed data to '{output_path.name}'")
    except Exception as e:
        logger.error(f"Failed to save processed data to '{output_path.name}': {e}")


def main():
    """
    Main function to orchestrate the ingestion pipeline.
    Finds new PDFs, processes them with GROBID, converts to Markdown,
    and prepares for the next steps.
    """
    logger.info("🚀 Starting ingestion pipeline...")

    if not check_grobid_server(ingest_config.GROBID_SERVER_URL):
        logger.error("Halting pipeline: GROBID server is not available.")
        return

    pdf_files = list(ingest_config.PDF_SOURCE_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.info("No new PDF files found to process.")
        return

    logger.info(f"Found {len(pdf_files)} PDF(s) to process.")

    for pdf_path in pdf_files:
        base_name = pdf_path.stem
        xml_path = ingest_config.XML_OUTPUT_DIR / f"{base_name}.xml"
        md_path = ingest_config.MD_CLEANED_DIR / f"{base_name}.md"

        # --- Skip if already processed, unless forcing ---
        if md_path.exists() and not ingest_config.FORCE_REPROCESS_PDF:
            logger.info(f"Skipping '{pdf_path.name}', Markdown file already exists.")
            continue

        logger.info(f"--- Processing: {pdf_path.name} ---")

        # --- Step 1: Process PDF with GROBID to get XML ---
        if not process_pdf_with_grobid(pdf_path, xml_path):
            # The function already logs and quarantines, so just continue
            continue

        # --- Step 2: Convert XML to clean Markdown ---
        if not convert_xml_to_md(xml_path, md_path, pdf_path):
            # The function already logs and quarantines, so just continue
            # Clean up the intermediate XML file on failure
            if xml_path.exists():
                xml_path.unlink()
            continue

        # --- Step 3: LLM Validation and Enrichment ---
        enriched_data = validate_and_enrich_with_llm(md_path, pdf_path)
        if not enriched_data:
            # The function already logs, quarantines, and cleans up.
            if xml_path.exists(): xml_path.unlink()
            if md_path.exists(): md_path.unlink()
            continue

        # --- Step 4: Semantic Chunking ---
        chunks = chunk_text_with_txtai(enriched_data["cleaned_text"])
        if not chunks:
            quarantine_file(pdf_path, "Text chunking failed.")
            if xml_path.exists(): xml_path.unlink()
            if md_path.exists(): md_path.unlink()
            continue

        # --- Step 5: Save to JSON ---
        final_output = {
            "source_filename": pdf_path.name,
            "document_summary": enriched_data["summary"],
            "key_entities": enriched_data["entities"],
            "chunks": chunks,
            "processed_timestamp": time.time()
        }

        json_output_path = ingest_config.PROCESSED_DATA_DIR / f"{base_name}.json"
        save_processed_data(json_output_path, final_output)

        # --- Final Step: Move original PDF to a 'processed' subfolder ---
        # This prevents it from being processed again in the future.
        # (For this implementation, we will just delete the original PDF
        # as the README implies a one-way data flow)
        pdf_path.unlink()
        logger.info(f"  -> Moved '{pdf_path.name}' after successful processing.")

        # --- Cleanup intermediate files ---
        if xml_path.exists():
            xml_path.unlink()
        if md_path.exists():
            md_path.unlink()
        logger.info(f"  -> Cleaned up intermediate files for '{pdf_path.name}'")

        logger.info(f"--- Finished processing: {pdf_path.name} ---")
        time.sleep(1) # Small delay to be polite

    logger.info("✅ Ingestion pipeline run complete.")


if __name__ == "__main__":
    main()
